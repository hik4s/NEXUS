import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {expect,it,vi} from 'vitest';
import type {SupabaseClient} from '@supabase/supabase-js';
import {LoginPage} from '../src/features/auth/LoginPage';
import {ApiClient} from '../src/lib/api';
function setup() {
 const methods={
  signInWithOAuth:vi.fn(async()=>({error:null})),
  signInWithPassword:vi.fn(async()=>({error:{code:'invalid_credentials'}})),
  signUp:vi.fn(async()=>({data:{session:null},error:null})),
  resetPasswordForEmail:vi.fn(async()=>({error:null})),
  updateUser:vi.fn(async()=>({error:null})),
 };
 const auth={auth:methods} as unknown as SupabaseClient;
 render(<LoginPage client={new ApiClient()} onLogin={()=>{}} expired={false} {...{auth}}/>);
 return {methods,user:userEvent.setup()};
}
it('offers Google GitHub and email using a same-origin callback',async()=>{
 const {methods,user}=setup();
 await user.click(screen.getByRole('button',{name:'Continuar com Google'}));
 expect(methods.signInWithOAuth).toHaveBeenCalledWith({provider:'google',options:{redirectTo:expect.stringMatching(new RegExp('^'+window.location.origin+'/auth/callback\\?flow=[0-9a-f-]+$'))}});
 await user.click(screen.getByRole('button',{name:'Continuar com GitHub'}));
 expect(methods.signInWithOAuth).toHaveBeenLastCalledWith({provider:'github',options:{redirectTo:expect.stringMatching(new RegExp('^'+window.location.origin+'/auth/callback\\?flow=[0-9a-f-]+$'))}});
 expect(screen.getByLabelText('E-mail')).toBeVisible();
});
it('shows a clear email/password error',async()=>{
 const {user}=setup();await user.type(screen.getByLabelText('E-mail'),'demo@example.com');await user.type(screen.getByLabelText('Senha'),'WrongPassword123');
 await user.click(screen.getByRole('button',{name:'Entrar no workspace'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha não conferem');
});
it('allows signup and explains the required email confirmation',async()=>{
 const {methods,user}=setup();await user.click(screen.getByRole('button',{name:'Criar conta'}));
 await user.type(screen.getByLabelText('E-mail'),'new@example.com');await user.type(screen.getByLabelText('Senha'),'NewPassword123!');
 await user.click(screen.getByRole('button',{name:'Criar minha conta'}));
 expect(methods.signUp).toHaveBeenCalled();expect(await screen.findByRole('status')).toHaveTextContent('Confirme seu e-mail');
});
it('offers email password recovery without a company or invite form',async()=>{
 const {methods,user}=setup();await user.click(screen.getByRole('button',{name:'Esqueci minha senha'}));
 await user.type(screen.getByLabelText('E-mail'),'demo@example.com');await user.click(screen.getByRole('button',{name:'Enviar recuperação'}));
 expect(methods.resetPasswordForEmail).toHaveBeenCalledWith('demo@example.com',{redirectTo:expect.stringContaining('/auth/callback?flow=')});
 expect(await screen.findByRole('status')).toHaveTextContent('Confira seu e-mail');
 expect(screen.queryByLabelText('Empresa')).not.toBeInTheDocument();
});
