/** Bearer sessions stay per-tab; only expiring, single-use PKCE proofs cross tabs. */
export function createAuthStorage(tab:Storage,shared:Storage,search=window.location.search){
 const channelKey=`nexus-auth-${crypto.randomUUID()}`;
 const params=new URLSearchParams(search);
 const incoming=params.get('flow');
 const validFlow=(value:string|null)=>!!value&&/^[0-9a-f-]{36}$/i.test(value);
 let flow=validFlow(incoming)?incoming:tab.getItem('nexus-auth-flow');
 if(validFlow(incoming))tab.setItem('nexus-auth-flow',incoming!);
 if(params.get('intent')==='recovery')tab.setItem('nexus-auth-recovery','true');
 const proofKey=(key:string)=>flow?`nexus-auth-pkce:${flow}${key.replace(/^nexus-auth-[0-9a-f-]{36}/i,'')}`:null;
 const canonical=(key:string)=>key.endsWith('-user')?'nexus-auth-user':'nexus-auth';
 const storage={
  getItem(key:string){
   if(!key.endsWith('-code-verifier'))return tab.getItem(canonical(key));
   const name=proofKey(key);if(!name)return null;
   try{const entry=JSON.parse(shared.getItem(name)||'null');if(entry&&entry.expiresAt>Date.now()&&typeof entry.value==='string')return entry.value;}catch{/* Invalid proofs are discarded. */}
   shared.removeItem(name);return null;
  },
  setItem(key:string,value:string){
   if(!key.endsWith('-code-verifier')){tab.setItem(canonical(key),value);return;}
   const name=proofKey(key);if(name)shared.setItem(name,JSON.stringify({value,expiresAt:Date.now()+3600000}));
  },
  removeItem(key:string){if(key.endsWith('-code-verifier')){const name=proofKey(key);if(name)shared.removeItem(name);}else tab.removeItem(canonical(key));},
 };
 return{channelKey,storage,
  callbackUrl(recovery=false){flow=crypto.randomUUID();tab.setItem('nexus-auth-flow',flow);const url=new URL('/auth/callback',window.location.origin);url.searchParams.set('flow',flow);if(recovery)url.searchParams.set('intent','recovery');return url.toString();},
  isRecovery:()=>tab.getItem('nexus-auth-recovery')==='true',
  setRecovery:()=>tab.setItem('nexus-auth-recovery','true'),
  clearRecovery:()=>tab.removeItem('nexus-auth-recovery'),
 };
}
let runtime:ReturnType<typeof createAuthStorage>|undefined;
export function getAuthStorage(){return runtime??=createAuthStorage(window.sessionStorage,window.localStorage);}
