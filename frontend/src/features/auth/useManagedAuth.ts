import {getAuthStorage} from './authStorage';
import {useEffect,useRef,useState} from 'react';
import type {Session,SupabaseClient} from '@supabase/supabase-js';
import {ApiClient} from '../../lib/api';
import type {User} from '../../lib/types';
import {initializeSession} from './supabaseClient';
import {authMessage} from './SupabaseLoginPage';

export function useManagedAuth(auth:SupabaseClient){
 const [session,setSession]=useState<Session|null>(null);const [user,setUser]=useState<User|null>(null);
 const [ready,setReady]=useState(false);const [error,setError]=useState('');const [expired,setExpired]=useState(false);
 const [recovery,setRecovery]=useState(false);
 const [attempt,setAttempt]=useState(0);const linked=useRef<string|null>(null);const generation=useRef(0);
 const epoch=useRef(0);const signingOut=useRef(false);
 const currentSession=useRef<Session|null>(null);
 const initialAddress=new URL(window.location.href);const initialFragment=new URLSearchParams(initialAddress.hash.slice(1));
 const callbackPending=useRef(initialAddress.pathname==='/auth/callback'||initialAddress.searchParams.has('code')||initialAddress.searchParams.has('error')||initialFragment.has('access_token')||initialFragment.has('error'));
 const callbackFailed=useRef(false);
 const refreshAttempted=useRef(false);const authBlocked=useRef(false);
 const [client]=useState(()=>new ApiClient(undefined,undefined,()=>{
  ++generation.current;linked.current=null;setUser(null);setExpired(true);
  if(refreshAttempted.current){authBlocked.current=true;setError('A sessão não foi aceita pela API. Entre novamente ou tente abrir o workspace manualmente.');return;}
  refreshAttempted.current=true;
  const current=epoch.current;
  void auth.auth.refreshSession().then(({data,error})=>{if(current!==epoch.current||signingOut.current)return;if(error){setSession(null);}else{setSession(data.session);}}).catch(()=>{if(current===epoch.current&&!signingOut.current)setSession(null);});
 }));
 useEffect(()=>{
  let disposed=false;
  const {data}=auth.auth.onAuthStateChange((event,next)=>{
   if(disposed||signingOut.current&&event!=='SIGNED_OUT'||authBlocked.current&&event==='TOKEN_REFRESHED')return;
   if(callbackPending.current){if(event==='PASSWORD_RECOVERY'&&next)getAuthStorage().setRecovery(next);return;}
   if(callbackFailed.current&&event!=='SIGNED_OUT')return;
   // INITIAL_SESSION describes persisted state, not a successful callback.
   if(event==='INITIAL_SESSION'&&callbackPending.current)return;
   if(event!=='INITIAL_SESSION')++epoch.current;
   if(event==='SIGNED_IN'||event==='PASSWORD_RECOVERY'||event==='SIGNED_OUT'){refreshAttempted.current=false;authBlocked.current=false;}
   if(currentSession.current?.user.id!==next?.user.id||event==='SIGNED_OUT'){
    ++generation.current;client.setToken(null);linked.current=null;setUser(null);setError('');
   }
   currentSession.current=next;
   if(event==='PASSWORD_RECOVERY'&&next)getAuthStorage().setRecovery(next);
   const recovering=getAuthStorage().isRecovery(next);
   if(!recovering)getAuthStorage().clearRecovery();
   setRecovery(recovering);
   setSession(next);
  });
  const initialEpoch=epoch.current;
  void initializeSession(auth).then(next=>{if(!disposed&&initialEpoch===epoch.current&&!signingOut.current){currentSession.current=next;setSession(next);const recovering=getAuthStorage().isRecovery(next);setRecovery(recovering);if(!recovering)getAuthStorage().clearRecovery();}}).catch(e=>{if(!disposed&&initialEpoch===epoch.current&&!signingOut.current){callbackFailed.current=callbackPending.current;currentSession.current=null;client.setToken(null);setSession(null);setUser(null);getAuthStorage().clearRecovery();setRecovery(false);setError(authMessage(e));}}).finally(()=>{if(!disposed){callbackPending.current=false;setReady(true);}});
  return()=>{disposed=true;data.subscription.unsubscribe();};
 },[auth,client]);
 useEffect(()=>{
  const current=++generation.current;
  if(!session||recovery){client.setToken(null);setUser(null);linked.current=null;return;}
  client.setToken(session.access_token);setError('');
  const subject=session.user.id;
  const work=linked.current===subject?client.get<User>('/auth/me'):client.post<User>('/auth/bootstrap');
  void work.then(value=>{
   if(current!==generation.current)return;
   linked.current=subject;refreshAttempted.current=false;setUser(value);setExpired(false);
   if(window.location.pathname==='/auth/callback')history.replaceState(null,'','/');
   if(!window.location.hash.startsWith('#/'))window.location.hash='/overview';
  }).catch(e=>{if(current===generation.current){setUser(null);setError(e instanceof Error?e.message:'Não foi possível abrir seu workspace.');}});
  return()=>{if(generation.current===current)++generation.current;};
 },[session,recovery,attempt,client]);
 async function logout(){
  ++epoch.current;++generation.current;signingOut.current=true;
  const result=await auth.auth.signOut({scope:'local'}).catch(e=>({error:e}));
  if(result.error){signingOut.current=false;setError('Não foi possível encerrar a sessão. Tente novamente.');return;}
  signingOut.current=false;getAuthStorage().clearRecovery();++generation.current;client.setToken(null);currentSession.current=null;linked.current=null;setUser(null);setSession(null);setError('');setExpired(false);setRecovery(false);window.location.hash='/overview';
 }
 function acceptAuthenticatedSession(next:Session){
  // Only an explicit password/code result may leave a failed callback screen.
  if(!callbackFailed.current)return;
  callbackFailed.current=false;++epoch.current;++generation.current;currentSession.current=next;
  linked.current=null;client.setToken(null);setUser(null);setError('');setSession(next);
  const recovering=getAuthStorage().isRecovery(next);setRecovery(recovering);if(!recovering)getAuthStorage().clearRecovery();
 }
 return{client,session,user,error,expired,recovery,loading:!ready||!!(session&&!user&&!error&&!recovery),
  logout,acceptAuthenticatedSession,retry:()=>{refreshAttempted.current=false;authBlocked.current=false;setAttempt(value=>value+1);},recovered:()=>{getAuthStorage().clearRecovery();setRecovery(false);}};
}
