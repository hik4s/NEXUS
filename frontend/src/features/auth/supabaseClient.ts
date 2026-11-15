import {getAuthStorage} from './authStorage';
import {createClient} from '@supabase/supabase-js';
import type {Session,SupabaseClient} from '@supabase/supabase-js';
const url=import.meta.env.VITE_SUPABASE_URL;
const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
export const authProvider=import.meta.env.VITE_AUTH_PROVIDER||((url||key)?'supabase':'legacy');
export const authConfigurationError=authProvider==='supabase'&&(!url||!key)?'O acesso está sendo configurado. Tente novamente em instantes.':'';
export const supabase:SupabaseClient|null=authProvider==='supabase'&&url&&key?createClient(url,key,{
 auth:{flowType:'pkce',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false,storage:getAuthStorage().storage,storageKey:getAuthStorage().channelKey},
}):null;

const pending=new WeakMap<SupabaseClient,Promise<Session|null>>();
/** Share an in-flight PKCE exchange across StrictMode mounts; never cache old sessions. */
export function initializeSession(auth:SupabaseClient):Promise<Session|null>{
 const existing=pending.get(auth);if(existing)return existing;
 const address=new URL(window.location.href);
 const fragment=new URLSearchParams(address.hash.slice(1));
 const error=address.searchParams.has('error')||fragment.has('error')||fragment.has('access_token');
 const code=address.searchParams.get('code');
 const flowId=address.searchParams.get('sb_flow_id');
 if(code||error||address.pathname==='/auth/callback'){
  for(const name of ['code','error','error_code','error_description','intent','flow','sb_flow_id'])address.searchParams.delete(name);
  if(error)address.hash='';
  if(address.pathname==='/auth/callback')address.pathname='/';
  history.replaceState(null,'',address.pathname+address.search+address.hash);
 }
 const work=(async()=>{
  if(error)throw new Error('OAuth callback failed');
  const response=code?await auth.auth.exchangeCodeForSession(code,flowId?{flowId}:undefined):await auth.auth.getSession();
  if(response.error)throw response.error;
  return response.data.session;
 })();
 pending.set(auth,work);
 void work.finally(()=>{if(pending.get(auth)===work)pending.delete(auth);}).catch(()=>{});
 return work;
}
