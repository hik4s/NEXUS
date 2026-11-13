import {getAuthStorage} from './authStorage';
import {useState} from 'react';
import type {FormEvent} from 'react';
import type {SupabaseClient} from '@supabase/supabase-js';
import {AuthFrame} from './AuthFrame';
import {Icon} from '../../components/ui';

export function callbackUrl(recovery=false) {return getAuthStorage().callbackUrl(recovery);}
export function authMessage(error:unknown):string {
 const code=error && typeof error==='object' && 'code' in error ? String(error.code) : '';
 const messages:Record<string,string>={
  invalid_credentials:'E-mail ou senha não conferem.',email_not_confirmed:'Confirme seu e-mail antes de entrar.',
  user_already_exists:'Este e-mail já possui uma conta. Entre ou recupere sua senha.',
  weak_password:'Use uma senha mais forte, com pelo menos 8 caracteres.',
  over_email_send_rate_limit:'Aguarde alguns minutos antes de solicitar outro e-mail.',
  over_request_rate_limit:'Muitas tentativas. Aguarde um momento e tente novamente.',
  same_password:'Escolha uma senha diferente da anterior.',
 };
 return messages[code]||'Não foi possível concluir o acesso. Tente novamente em instantes.';
}
export function SupabaseLoginPage({auth,expired,recovery=false,onRecovered}:{auth:SupabaseClient;expired:boolean;recovery?:boolean;onRecovered?:()=>void}) {
 const [mode,setMode]=useState<'login'|'signup'|'recover'>('login');
 const [email,setEmail]=useState('');const [password,setPassword]=useState('');const [confirmation,setConfirmation]=useState('');
 const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');
 async function run(work:()=>Promise<void>){if(busy)return;setBusy(true);setError('');setNotice('');try{await work();}catch(e){setError(authMessage(e));}finally{setBusy(false);}}
 function switchMode(next:typeof mode){setMode(next);setError('');setNotice('');setPassword('');setConfirmation('');}
 function social(provider:'google'|'github'){void run(async()=>{const result=await auth.auth.signInWithOAuth({provider,options:{redirectTo:callbackUrl()}});if(result.error)throw result.error;});}
 function submit(event:FormEvent){event.preventDefault();void run(async()=>{
  if(recovery){
   if(password!==confirmation){setError('As senhas precisam ser iguais.');return;}
   const result=await auth.auth.updateUser({password});if(result.error)throw result.error;
   setPassword('');setConfirmation('');onRecovered?.();return;
  }
  if(mode==='recover'){const result=await auth.auth.resetPasswordForEmail(email,{redirectTo:callbackUrl(true)});if(result.error)throw result.error;setNotice('Confira seu e-mail. Se houver uma conta, você receberá um link de recuperação.');return;}
  if(mode==='signup'){const result=await auth.auth.signUp({email,password,options:{emailRedirectTo:callbackUrl()}});if(result.error)throw result.error;if(!result.data.session)setNotice('Confirme seu e-mail pelo link enviado para concluir o cadastro e entrar.');return;}
  const result=await auth.auth.signInWithPassword({email,password});if(result.error)throw result.error;
 });}
 const submitLabel=recovery?'Salvar nova senha':mode==='signup'?'Criar minha conta':mode==='recover'?'Enviar recuperação':'Entrar no workspace';
 return <AuthFrame note="Acesso livre. No primeiro login, seu workspace é criado com dados separados das outras contas.">
  {expired&&<div className="notice warning" role="status">Sua sessão terminou. Entre novamente para continuar.</div>}
  {recovery?<div className="auth-panel-heading"><h2>Defina sua nova senha</h2><p>Depois de salvar, você poderá continuar no seu workspace.</p></div>:<>
   <div className="social-auth"><button type="button" className="button secondary" onClick={()=>social('google')} disabled={busy}><span className="provider-google" aria-hidden="true">G</span>Continuar com Google</button><button type="button" className="button secondary" onClick={()=>social('github')} disabled={busy}><svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.18-3.37-1.18-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.89 1.53 2.34 1.09 2.91.83.09-.65.35-1.09.64-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.99 1.03-2.69-.1-.25-.45-1.27.1-2.65 0 0 .84-.27 2.75 1.03a9.6 9.6 0 0 1 5 0c1.91-1.3 2.75-1.03 2.75-1.03.55 1.38.2 2.4.1 2.65.64.7 1.03 1.6 1.03 2.69 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.86v2.58c0 .27.18.58.69.48A10 10 0 0 0 12 2Z"/></svg>Continuar com GitHub</button></div>
   <div className="auth-divider"><span>ou use seu e-mail</span></div>
   {mode==='recover'&&<div className="auth-panel-heading"><h2>Recuperar acesso</h2><p>Vamos enviar um link para você criar uma nova senha.</p></div>}
  </>}
  <form onSubmit={submit}>
   {!recovery&&<><label htmlFor="email">E-mail</label><input id="email" type="email" autoComplete="username" placeholder="seu@email.com" value={email} onChange={e=>setEmail(e.target.value)} required disabled={busy}/></>}
   {(recovery||mode!=='recover')&&<><label htmlFor="password">{recovery?'Nova senha':'Senha'}</label><input id="password" type="password" autoComplete={recovery||mode==='signup'?'new-password':'current-password'} placeholder={mode==='signup'||recovery?'Pelo menos 8 caracteres':'Sua senha'} minLength={mode==='signup'||recovery?8:1} value={password} onChange={e=>setPassword(e.target.value)} required disabled={busy}/></>}
   {recovery&&<><label htmlFor="confirmation">Confirmar nova senha</label><input id="confirmation" type="password" autoComplete="new-password" minLength={8} value={confirmation} onChange={e=>setConfirmation(e.target.value)} required disabled={busy}/></>}
   <button className="button primary" disabled={busy}>{busy?'Aguarde…':submitLabel}<Icon name="arrow" size={18}/></button>
  </form>
  {error&&<div className="notice error" role="alert">{error}</div>}{notice&&<div className="notice success" role="status">{notice}</div>}
  {!recovery&&<div className="auth-options">{mode==='login'?<><button type="button" onClick={()=>switchMode('recover')} disabled={busy}>Esqueci minha senha</button><button type="button" onClick={()=>switchMode('signup')} disabled={busy}>Criar conta</button></>:<button type="button" onClick={()=>switchMode('login')} disabled={busy}>Voltar para entrar</button>}</div>}
 </AuthFrame>;
}
