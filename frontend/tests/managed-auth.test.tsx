import {act,renderHook,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import type {Session,SupabaseClient} from '@supabase/supabase-js';
import {useManagedAuth} from '../src/features/auth/useManagedAuth';
const session={access_token:'test-token',user:{id:'subject-a'}} as Session;
const user={id:'user-a',company_id:'company-a'};
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(done=>resolve=done);return{promise,resolve};}
function fake(){
 let listener:((event:string,next:Session|null)=>void)|undefined;
 const refresh=deferred<{data:{session:Session|null};error:null}>();
 const auth={auth:{getSession:vi.fn(async()=>({data:{session},error:null})),onAuthStateChange:vi.fn((fn:typeof listener)=>{listener=fn;return{data:{subscription:{unsubscribe(){}}}};}),refreshSession:vi.fn(()=>refresh.promise),signOut:vi.fn(async()=>{listener?.('SIGNED_OUT',null);return{error:null};})}} as unknown as SupabaseClient;
 return{auth,refresh,emit:(event:string,next:Session|null)=>listener?.(event,next)};
}
afterEach(()=>{vi.unstubAllGlobals();sessionStorage.clear();history.replaceState(null,'','/');});
it('discards a bootstrap response that arrives after logout',async()=>{
 const pending=deferred<Response>();vi.stubGlobal('fetch',vi.fn(()=>pending.promise));const {auth}=fake();
 const {result}=renderHook(()=>useManagedAuth(auth));await waitFor(()=>expect(fetch).toHaveBeenCalled());
 await act(()=>result.current.logout());await act(async()=>pending.resolve(Response.json(user)));
 expect(result.current.user).toBeNull();expect(result.current.session).toBeNull();
});
it('does not restore a session when refresh finishes after logout',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));const {auth,refresh}=fake();
 const {result}=renderHook(()=>useManagedAuth(auth));await waitFor(()=>expect(result.current.user).toEqual(user));
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({},{status:401})));
 await act(async()=>{await result.current.client.get('/products').catch(()=>{});});
 expect(auth.auth.refreshSession).toHaveBeenCalled();await act(()=>result.current.logout());
 await act(async()=>refresh.resolve({data:{session},error:null}));
 expect(result.current.session).toBeNull();expect(result.current.user).toBeNull();
});
it('returns to login when recovery has no valid session',async()=>{
 sessionStorage.setItem('nexus-auth-recovery','true');const {auth}=fake();
 vi.mocked(auth.auth.getSession).mockResolvedValue({data:{session:null},error:null});
 const {result}=renderHook(()=>useManagedAuth(auth));
 await waitFor(()=>expect(result.current.loading).toBe(false));
 expect(result.current.recovery).toBe(false);expect(sessionStorage.getItem('nexus-auth-recovery')).toBeNull();
});

it('hides the previous workspace immediately while a different account is bootstrapping',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));const {auth,emit}=fake();
 const {result}=renderHook(()=>useManagedAuth(auth));await waitFor(()=>expect(result.current.user).toEqual(user));
 const pending=deferred<Response>();vi.stubGlobal('fetch',vi.fn(()=>pending.promise));
 act(()=>emit('SIGNED_IN',{...session,access_token:'token-b',user:{...session.user,id:'subject-b'}}));
 expect(result.current.user).toBeNull();expect(result.current.loading).toBe(true);
 await act(async()=>pending.resolve(Response.json({id:'user-b',company_id:'company-b'})));
 expect(result.current.user?.id).toBe('user-b');
});

it('does not replace account B when a refresh for account A finishes late',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));const {auth,refresh,emit}=fake();
 const {result}=renderHook(()=>useManagedAuth(auth));await waitFor(()=>expect(result.current.user).toEqual(user));
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({},{status:401})));
 await act(async()=>{await result.current.client.get('/products').catch(()=>{});});
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({id:'user-b',company_id:'company-b'})));
 const other={...session,access_token:'token-b',user:{...session.user,id:'subject-b'}};
 act(()=>emit('SIGNED_IN',other));await waitFor(()=>expect(result.current.user?.id).toBe('user-b'));
 await act(async()=>refresh.resolve({data:{session},error:null}));
 expect(result.current.session?.user.id).toBe('subject-b');
});

it('ignores a refresh event that arrives while the callback session lookup is pending',async()=>{
 const pending=deferred<{data:{session:Session|null};error:null}>();const {auth,emit}=fake();
 vi.mocked(auth.auth.getSession).mockImplementation(()=>pending.promise as ReturnType<typeof auth.auth.getSession>);
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));
 const {result}=renderHook(()=>useManagedAuth(auth));
 act(()=>emit('SIGNED_IN',{...session,access_token:'token-b',user:{...session.user,id:'subject-b'}}));
 await act(async()=>pending.resolve({data:{session},error:null}));
 expect(result.current.session?.user.id).toBe('subject-b');
});

it('does not expose the persisted workspace while a callback exchange is pending',async()=>{
 history.replaceState(null,'','/auth/callback?code=pending-code');const {auth,emit}=fake();
 const exchange=deferred<{data:{session:null};error:Error}>();
 Object.assign(auth.auth,{exchangeCodeForSession:()=>exchange.promise});
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));
 const {result}=renderHook(()=>useManagedAuth(auth));
 await act(async()=>emit('INITIAL_SESSION',session));
 expect(result.current.user).toBeNull();expect(result.current.session).toBeNull();
 await act(async()=>exchange.resolve({data:{session:null},error:new Error('Invalid callback')}));
 expect(result.current.error).not.toBe('');
});

it('reports a failed callback even when the SDK emitted INITIAL_SESSION first',async()=>{
 history.replaceState(null,'','/auth/callback?code=expired-code');const {auth,emit}=fake();
 const exchange=deferred<{data:{session:null};error:Error}>();
 Object.assign(auth.auth,{exchangeCodeForSession:()=>exchange.promise});
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json(user)));
 const {result}=renderHook(()=>useManagedAuth(auth));
 act(()=>emit('INITIAL_SESSION',null));
 await act(async()=>exchange.resolve({data:{session:null},error:new Error('Invalid callback')}));
 expect(result.current.error).not.toBe('');expect(result.current.user).toBeNull();
});

it('stops refreshing automatically when the API rejects the refreshed identity too',async()=>{
 const {auth,emit}=fake();
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({},{status:401})));
 vi.mocked(auth.auth.refreshSession).mockImplementation(async()=>{
  const next={...session,access_token:'refreshed-'+crypto.randomUUID()};
  emit('TOKEN_REFRESHED',next);
  return {data:{session:next,user:next.user},error:null};
 });
 const {result}=renderHook(()=>useManagedAuth(auth));
 await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));
 await new Promise(resolve=>setTimeout(resolve,50));
 expect(result.current.loading).toBe(false);expect(result.current.error).not.toBe('');
 expect(vi.mocked(fetch).mock.calls.length).toBeLessThanOrEqual(2);
});
