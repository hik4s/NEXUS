import {AuthFrame} from './AuthFrame';
import { useState } from 'react';
import type { FormEvent } from 'react';
import type {SupabaseClient} from '@supabase/supabase-js';
import {SupabaseLoginPage} from './SupabaseLoginPage';
import { ApiClient } from '../../lib/api';
import type { Login } from '../../lib/types';
import { useAction } from '../../lib/hooks';
import { ErrorNotice, Icon } from '../../components/ui';

type LoginProps={client:ApiClient;onLogin:(login:Login)=>void;expired:boolean;auth?:SupabaseClient;recovery?:boolean;onRecovered?:()=>void};
export function LoginPage(props:LoginProps){return props.auth?<SupabaseLoginPage auth={props.auth} expired={props.expired} recovery={props.recovery} onRecovered={props.onRecovered}/>:<LegacyLoginPage {...props}/>;}
function LegacyLoginPage({client,onLogin,expired}:LoginProps) {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const action = useAction();
  function submit(event: FormEvent) { event.preventDefault(); void action.run(async () => { const login = await client.post<Login>('/auth/login', { email, password }); onLogin(login); }); }
  return <AuthFrame note="Use uma conta de demonstração provisionada. Seus dados ficam separados por empresa.">    {expired && <div className="notice warning" role="status">Sua sessão terminou. Entre novamente para continuar.</div>}
    <form onSubmit={submit}><label htmlFor="email">E-mail</label><input id="email" type="email" autoComplete="username" placeholder="seu@email.com" value={email} onChange={event => setEmail(event.target.value)} required/><label htmlFor="password">Senha</label><input id="password" type="password" autoComplete="current-password" placeholder="Sua senha" value={password} onChange={event => setPassword(event.target.value)} required/><button className="button primary" disabled={action.busy}>{action.busy ? 'Entrando…' : 'Entrar no workspace'}<Icon name="arrow" size={18}/></button></form><ErrorNotice error={action.error}/></AuthFrame>;
}
