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
afterEach(()=>{vi.unstubAllGlobals();sessionStorage.clear();});
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
