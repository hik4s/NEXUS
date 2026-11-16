import {WorkspaceLoader as Workspace} from './WorkspaceLoader';
import {supabase,authConfigurationError} from './features/auth/supabaseClient';
import type {SupabaseClient} from '@supabase/supabase-js';
import {useManagedAuth} from './features/auth/useManagedAuth';
import {AuthFrame} from './features/auth/AuthFrame';
import {EmailConfirmation} from './features/auth/EmailConfirmation';
import {emailConfirmationLink} from './features/auth/emailConfirmationLink';
import { useState } from 'react';
import { ApiClient } from './lib/api';
import type { Login, User } from './lib/types';
import { Icon } from './components/ui';
import { LoginPage } from './features/auth/LoginPage';

export default function App() {
  const [confirmationHandled,setConfirmationHandled]=useState(false);
  if(authConfigurationError)return <AuthFrame note="Acesso ao NEXUS"><div role="alert" className="notice error">{authConfigurationError}</div></AuthFrame>;
  if(supabase&&emailConfirmationLink.requested&&!confirmationHandled)return <EmailConfirmation auth={supabase} tokenHash={emailConfirmationLink.tokenHash} onContinue={()=>setConfirmationHandled(true)}/>;
  return supabase?<ManagedApp auth={supabase}/>:<LegacyApp/>;
}
function ManagedApp({auth}:{auth:SupabaseClient}){
  const state=useManagedAuth(auth);
  if(state.loading)return <AuthFrame note="Seus dados ficam separados por workspace."><div role="status" className="auth-connecting"><Icon name="refresh"/>Conectando seu workspace…</div></AuthFrame>;
  if(state.session&&!state.user&&!state.recovery&&state.error)return <AuthFrame note="Nenhuma operação de negócio foi repetida."><div role="alert" className="notice error">{state.error}</div><div className="auth-options"><button className="button primary" onClick={state.retry}>Tentar abrir workspace</button><button type="button" onClick={()=>void state.logout()}>Sair desta conta</button></div></AuthFrame>;
  if(!state.user||state.recovery)return <><LoginPage auth={auth} recovery={state.recovery} onRecovered={state.recovered} onAuthenticated={state.acceptAuthenticatedSession} client={state.client} onLogin={()=>{}} expired={state.expired}/>{state.error&&<div className="session-notice notice error" role="alert">{state.error}</div>}</>;
  return <><Workspace key={state.user.id} client={state.client} user={state.user} logout={()=>void state.logout()}/>{state.error&&<div className="session-notice notice error" role="alert">{state.error}</div>}</>;
}
function LegacyApp() {
  const [user, setUser] = useState<User | null>(null); const [expired, setExpired] = useState(false);
  const [client] = useState(() => new ApiClient(undefined, undefined, () => { setUser(null); setExpired(true); window.location.hash = '/overview'; }));
  function login(login: Login) { client.setToken(login.access_token); setUser(login.user); setExpired(false); window.location.hash = '/overview'; }
  function logout() { client.setToken(null); setUser(null); setExpired(false); window.location.hash = '/overview'; }
  return user ? <Workspace key={user.id} client={client} user={user} logout={logout}/> : <LoginPage client={client} onLogin={login} expired={expired}/>;
}
