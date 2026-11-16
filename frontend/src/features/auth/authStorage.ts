/** Bearer sessions stay per-tab; only expiring, single-use PKCE proofs cross tabs. */
import type {Session} from '@supabase/supabase-js';

function recoveryIdentity(session:Session|null):string|null{
 if(!session)return null;
 try{
  const encoded=session.access_token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
  const id=JSON.parse(atob(encoded)).session_id;
  return typeof id==='string'&&id?JSON.stringify({subject:session.user.id,sessionId:id}):null;
 }catch{return null;}
}
export function createAuthStorage(tab:Storage,shared:Storage,search=window.location.search){
 const sweepProofs=()=>{
  const keys=Array.from({length:shared.length},(_,index)=>shared.key(index));
  for(const key of keys){
   if(!key?.startsWith('nexus-auth-pkce:'))continue;
   try{
    const entry=JSON.parse(shared.getItem(key)||'null');
    if(entry&&typeof entry.value==='string'&&typeof entry.expiresAt==='number'&&Number.isFinite(entry.expiresAt)&&entry.expiresAt>Date.now())continue;
   }catch{/* Malformed proofs cannot be exchanged. */}
   shared.removeItem(key);
  }
 };
 sweepProofs();
 const channelKey=`nexus-auth-${crypto.randomUUID()}`;
 const params=new URLSearchParams(search);
 const incoming=params.get('flow');
 const validFlow=(value:string|null)=>!!value&&/^[0-9a-f-]{36}$/i.test(value);
 let flow=validFlow(incoming)?incoming:tab.getItem('nexus-auth-flow');
 if(validFlow(incoming))tab.setItem('nexus-auth-flow',incoming!);
 const proofKey=(key:string)=>flow?`nexus-auth-pkce:${flow}${key.replace(/^nexus-auth-[0-9a-f-]{36}/i,'')}`:null;
 const canonical=(key:string)=>key.endsWith('-user')?'nexus-auth-user':'nexus-auth';
 const storage={
  getItem(key:string){
   if(!key.endsWith('-code-verifier'))return tab.getItem(canonical(key));
   const name=proofKey(key);if(!name)return null;
   try{const entry=JSON.parse(shared.getItem(name)||'null');if(entry&&typeof entry.value==='string'&&typeof entry.expiresAt==='number'&&Number.isFinite(entry.expiresAt)&&entry.expiresAt>Date.now())return entry.value;}catch{/* Invalid proofs are discarded. */}
   shared.removeItem(name);return null;
  },
  setItem(key:string,value:string){
   if(!key.endsWith('-code-verifier')){tab.setItem(canonical(key),value);return;}
   const name=proofKey(key);if(name)shared.setItem(name,JSON.stringify({value,expiresAt:Date.now()+3600000}));
  },
  removeItem(key:string){if(key.endsWith('-code-verifier')){const name=proofKey(key);if(name)shared.removeItem(name);}else tab.removeItem(canonical(key));},
 };
 return{channelKey,storage,
  callbackUrl(recovery=false){sweepProofs();flow=crypto.randomUUID();tab.setItem('nexus-auth-flow',flow);const url=new URL('/auth/callback',window.location.origin);url.searchParams.set('flow',flow);if(recovery)url.searchParams.set('intent','recovery');return url.toString();},
  isRecovery:(session:Session|null)=>{const identity=recoveryIdentity(session);return !!identity&&tab.getItem('nexus-auth-recovery')===identity;},
  setRecovery:(session:Session)=>{const identity=recoveryIdentity(session);if(identity)tab.setItem('nexus-auth-recovery',identity);else tab.removeItem('nexus-auth-recovery');},
  clearRecovery:()=>tab.removeItem('nexus-auth-recovery'),
 };
}
let runtime:ReturnType<typeof createAuthStorage>|undefined;
export function getAuthStorage(){return runtime??=createAuthStorage(window.sessionStorage,window.localStorage);}
