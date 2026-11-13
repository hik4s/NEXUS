import {expect,it,afterEach,vi} from 'vitest';
import {createAuthStorage} from '../src/features/auth/authStorage';
class MemoryStorage implements Storage {
 data=new Map<string,string>();get length(){return this.data.size;} clear(){this.data.clear();}getItem(k:string){return this.data.get(k)??null;}key(i:number){return [...this.data.keys()][i]??null;}removeItem(k:string){this.data.delete(k);}setItem(k:string,v:string){this.data.set(k,v);}
}
afterEach(()=>vi.useRealTimers());
it('isolates SDK broadcast keys but restores each tabs own persisted session',()=>{
 const local=new MemoryStorage(),tabA=new MemoryStorage(),tabB=new MemoryStorage();
 const a=createAuthStorage(tabA,local),b=createAuthStorage(tabB,local);
 expect(a.channelKey).not.toBe(b.channelKey);
 a.storage.setItem(a.channelKey,'token-A');b.storage.setItem(b.channelKey,'token-B');
 expect(a.storage.getItem(a.channelKey)).toBe('token-A');
 expect(createAuthStorage(tabA,local).storage.getItem(a.channelKey)).toBe('token-A');
 expect(local.length).toBe(0);
});
it('shares only an expiring per-flow PKCE verifier with a fresh callback tab',()=>{
 const local=new MemoryStorage();const a=createAuthStorage(new MemoryStorage(),local);
 const url=new URL(a.callbackUrl(true));
 a.storage.setItem(a.channelKey+'-code-verifier','"verifier-only"');
 const tabB=new MemoryStorage();const b=createAuthStorage(tabB,local,url.search);
 expect(b.storage.getItem(b.channelKey+'-code-verifier')).toBe('"verifier-only"');
 expect(b.isRecovery()).toBe(true);
 expect(createAuthStorage(tabB,local).isRecovery()).toBe(true);
 b.clearRecovery();expect(createAuthStorage(tabB,local).isRecovery()).toBe(false);
 b.storage.removeItem(b.channelKey+'-code-verifier');expect(local.length).toBe(0);
});
it('expires unused PKCE proof without persisting a bearer session',()=>{
 vi.useFakeTimers();vi.setSystemTime(new Date('2026-11-13T10:00:00Z'));
 const local=new MemoryStorage();const a=createAuthStorage(new MemoryStorage(),local);a.callbackUrl();a.storage.setItem(a.channelKey+'-code-verifier','proof');
 vi.setSystemTime(new Date('2026-11-13T12:00:00Z'));
 expect(a.storage.getItem(a.channelKey+'-code-verifier')).toBeNull();expect(local.length).toBe(0);
});

it('passes a real SDK PKCE proof to an exchange in a fresh callback tab',async()=>{
 const {createClient}=await import('@supabase/supabase-js');
 const shared=new MemoryStorage();const a=createAuthStorage(new MemoryStorage(),shared);
 const options=(runtime:ReturnType<typeof createAuthStorage>)=>({flowType:'pkce' as const,persistSession:true,autoRefreshToken:false,detectSessionInUrl:false,storage:runtime.storage,storageKey:runtime.channelKey});
 const original=createClient('https://test.supabase.co','public-test-key',{auth:options(a)});
 const started=await original.auth.signInWithOAuth({provider:'github',options:{redirectTo:a.callbackUrl(true),skipBrowserRedirect:true}});
 expect(started.error).toBeNull();
 const redirect=new URL(new URL(started.data.url!).searchParams.get('redirect_to')!);
 const b=createAuthStorage(new MemoryStorage(),shared,redirect.search);
 const fetcher=vi.fn<typeof fetch>(async()=>Response.json({error:'invalid_grant',error_description:'Synthetic code rejected'},{status:400}));
 const callback=createClient('https://test.supabase.co','public-test-key',{auth:options(b),global:{fetch:fetcher}});
 const result=await callback.auth.exchangeCodeForSession('synthetic-code',{flowId:redirect.searchParams.get('sb_flow_id')!});
 expect(fetcher).toHaveBeenCalled();
 const body=JSON.parse(String(fetcher.mock.calls[0][1]?.body));
 expect(body.auth_code).toBe('synthetic-code');expect(body.code_verifier.length).toBeGreaterThan(40);
 expect(result.error?.name).not.toBe('AuthPKCECodeVerifierMissingError');
 original.auth.stopAutoRefresh();callback.auth.stopAutoRefresh();
});
