import {useEffect,useState} from 'react';
import type {FormEvent} from 'react';
import type {Session,SupabaseClient} from '@supabase/supabase-js';
import {authMessage} from './authMessages';
import {getAuthStorage} from './authStorage';
import {useAuthOperation} from './useAuthOperation';
import type {AuthOperation} from './useAuthOperation';

export function EmailCodeForm({auth,initialEmail='',justSent=false,onVerified,onBack,backLabel='Voltar para entrar',operation:shared}:{auth:SupabaseClient;initialEmail?:string;justSent?:boolean;onVerified:(session:Session)=>void;onBack?:()=>void;backLabel?:string;operation?:AuthOperation}){
 const [email,setEmail]=useState(initialEmail);const [token,setToken]=useState('');
 const local=useAuthOperation();const {busy,setBusy,lock}=shared??local;
 const [error,setError]=useState('');const [notice,setNotice]=useState(justSent?'Confirme seu e-mail pelo botão da mensagem ou digite o código abaixo.':'');
 const [until,setUntil]=useState(justSent?Date.now()+60_000:0);const [now,setNow]=useState(Date.now());
 useEffect(()=>{if(!until)return;const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[until]);
 const remaining=Math.max(0,Math.ceil((until-now)/1000));
 async function run(work:()=>Promise<void>){if(lock.current)return;lock.current=true;setBusy(true);setError('');setNotice('');try{await work();}catch(e){setError(authMessage(e));}finally{lock.current=false;setBusy(false);}}
 function submit(event:FormEvent){event.preventDefault();void run(async()=>{
  const value=token.replace(/\s/g,'');
  if(!/^\d{6,10}$/.test(value)){setError('Digite o código numérico recebido no e-mail.');return;}
  const result=await auth.auth.verifyOtp({email:email.trim().toLowerCase(),token:value,type:'email'});
  if(result.error)throw result.error;
  if(!result.data.session)throw {code:'confirmation_session_missing'};
  setToken('');onVerified(result.data.session);
 });}
 function resend(){if(remaining)return;void run(async()=>{
  const value=email.trim().toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)){setError('Informe seu e-mail para reenviar a confirmação.');return;}
  const result=await auth.auth.resend({type:'signup',email:value,options:{emailRedirectTo:getAuthStorage().callbackUrl()}});
  if(result.error)throw result.error;
  const sent=Date.now();setNow(sent);setUntil(sent+60_000);setToken('');
  setNotice('Confira sua caixa de entrada e o spam. Se houver uma confirmação pendente, você receberá um novo e-mail.');
 });}
 return <div className="email-code-panel">
  <div className="auth-panel-heading"><h2>Confirme seu e-mail</h2><p>Seu workspace está quase pronto. Use o link da mensagem ou digite o código recebido — basta uma das opções.</p></div>
  <form onSubmit={submit}>
   <label htmlFor="confirmation-email">E-mail</label><input id="confirmation-email" type="email" autoComplete="email" value={email} onChange={e=>{setEmail(e.target.value);setToken('');setError('');}} disabled={busy} required/>
   <label htmlFor="confirmation-code">Código de confirmação</label><input id="confirmation-code" className="confirmation-code" type="text" inputMode="numeric" autoComplete="one-time-code" placeholder="Digite o código do e-mail" value={token} maxLength={20} onChange={e=>setToken(e.target.value)} disabled={busy} required aria-describedby="confirmation-help"/>
   <p id="confirmation-help" className="confirmation-help">O código é de uso único. Use o mais recente e não compartilhe com ninguém.</p>
   <button className="button primary" disabled={busy}>{busy?'Aguarde…':'Confirmar código'}</button>
  </form>
  {error&&<div className="notice error" role="alert">{error}</div>}
  {notice&&<div className="notice success" role="status">{notice}</div>}
  <div className="auth-options"><button type="button" disabled={busy||remaining>0} onClick={resend}>{remaining?`Reenviar em ${remaining}s`:'Reenviar confirmação'}</button>{onBack&&<button type="button" disabled={busy} onClick={onBack}>{backLabel}</button>}</div>
 </div>;
}
