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
 const [recovery,setRecovery]=useState(()=>getAuthStorage().isRecovery());
 const [attempt,setAttempt]=useState(0);const linked=useRef<string|null>(null);const generation=useRef(0);
 const epoch=useRef(0);const signingOut=useRef(false);
 const [client]=useState(()=>new ApiClient(undefined,undefined,()=>{
  ++generation.current;linked.current=null;setUser(null);setExpired(true);
  const current=epoch.current;
  void auth.auth.refreshSession().then(({data,error})=>{if(current!==epoch.current||signingOut.current)return;if(error){setSession(null);}else{setSession(data.session);}}).catch(()=>{if(current===epoch.current&&!signingOut.current)setSession(null);});
 }));
 useEffect(()=>{
  let disposed=false;
  const {data}=auth.auth.onAuthStateChange((event,next)=>{
   if(disposed||signingOut.current&&event!=='SIGNED_OUT')return;
   if(event==='PASSWORD_RECOVERY'){getAuthStorage().setRecovery();setRecovery(true);}
   if(event==='SIGNED_OUT'){++epoch.current;++generation.current;getAuthStorage().clearRecovery();client.setToken(null);linked.current=null;setUser(null);setRecovery(false);}
   setSession(next);
  });
  const initialEpoch=epoch.current;
  void initializeSession(auth).then(next=>{if(!disposed&&initialEpoch===epoch.current&&!signingOut.current){setSession(next);if(!next){getAuthStorage().clearRecovery();setRecovery(false);}}}).catch(e=>{if(!disposed){getAuthStorage().clearRecovery();setRecovery(false);setError(authMessage(e));}}).finally(()=>{if(!disposed)setReady(true);});
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
   linked.current=subject;setUser(value);setExpired(false);
   if(window.location.pathname==='/auth/callback')history.replaceState(null,'','/');
   if(!window.location.hash.startsWith('#/'))window.location.hash='/overview';
  }).catch(e=>{if(current===generation.current){setUser(null);setError(e instanceof Error?e.message:'Não foi possível abrir seu workspace.');}});
  return()=>{if(generation.current===current)++generation.current;};
 },[session,recovery,attempt,client]);
 async function logout(){
  ++epoch.current;++generation.current;signingOut.current=true;
  const result=await auth.auth.signOut({scope:'local'}).catch(e=>({error:e}));
  if(result.error){signingOut.current=false;setError('Não foi possível encerrar a sessão. Tente novamente.');return;}
  signingOut.current=false;getAuthStorage().clearRecovery();++generation.current;client.setToken(null);linked.current=null;setUser(null);setSession(null);setError('');setExpired(false);setRecovery(false);window.location.hash='/overview';
 }
 return{client,session,user,error,expired,recovery,loading:!ready||!!(session&&!user&&!error&&!recovery),
  logout,retry:()=>setAttempt(value=>value+1),recovered:()=>{getAuthStorage().clearRecovery();setRecovery(false);}};
}
