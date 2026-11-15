import {useState} from 'react';
import type {Session,SupabaseClient} from '@supabase/supabase-js';
import {AuthFrame} from './AuthFrame';
import {EmailCodeForm} from './EmailCodeForm';
import {authMessage} from './authMessages';
import {useAuthOperation} from './useAuthOperation';

export function EmailConfirmation({auth,tokenHash,onContinue}:{auth:SupabaseClient;tokenHash:string|null;onContinue:()=>void}){
 const [verified,setVerified]=useState<Session|null>(null);const operation=useAuthOperation();const {busy,setBusy,lock}=operation;const [error,setError]=useState('');
 async function confirm(){if(!tokenHash||lock.current)return;lock.current=true;setBusy(true);setError('');try{
  const result=await auth.auth.verifyOtp({token_hash:tokenHash,type:'email'});
  if(result.error)throw result.error;
  if(!result.data.session)throw {code:'confirmation_session_missing'};
  setVerified(result.data.session);
 }catch(e){setError(authMessage(e));}finally{lock.current=false;setBusy(false);}}
 return <AuthFrame note="Confirmação segura. Seu workspace e seus dados ficam separados das outras contas.">
  {verified?<div className="email-confirmation-success"><span className="confirmation-check" aria-hidden="true">✓</span><h2>E-mail confirmado</h2>{verified.user.email&&<strong>{verified.user.email}</strong>}<p>Tudo pronto. Agora você pode abrir o workspace desta conta e começar a conectar cada etapa da sua operação.</p><button className="button primary" onClick={onContinue}>Abrir meu workspace</button></div>:<>
   {tokenHash&&<div className="email-confirmation-intro"><span className="eyebrow">SÓ FALTA UM PASSO</span><h2>Vamos confirmar seu acesso?</h2><p>Confirme que foi você quem criou a conta no NEXUS. O link só será utilizado ao tocar no botão abaixo.</p><button className="button primary" disabled={busy} onClick={()=>void confirm()}>Confirmar meu e-mail</button></div>}
   {error&&<div className="notice error" role="alert">{error}</div>}
   <EmailCodeForm auth={auth} operation={operation} onVerified={setVerified} onBack={onContinue} backLabel="Sair da confirmação"/>
  </>}
 </AuthFrame>;
}
