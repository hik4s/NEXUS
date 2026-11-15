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
  verifyOtp:vi.fn(async()=>({data:{session:{access_token:'verified'}},error:null})),
  resend:vi.fn(async()=>({data:{user:null,session:null},error:null})),
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

it('offers a confirmation code after signup and never keeps the password in the form',async()=>{
 const {user}=setup();await user.click(screen.getByRole('button',{name:'Criar conta'}));
 await user.type(screen.getByLabelText('E-mail'),'new@example.com');await user.type(screen.getByLabelText('Senha'),'NewPassword123!');
 await user.click(screen.getByRole('button',{name:'Criar minha conta'}));
 expect(await screen.findByLabelText('Código de confirmação')).toHaveAttribute('autocomplete','one-time-code');
 expect(screen.queryByLabelText('Senha')).not.toBeInTheDocument();
 expect(screen.getByLabelText('E-mail')).toHaveValue('new@example.com');
});

it('verifies an email code and shows provider failures without claiming success',async()=>{
 const {methods,user}=setup();
 methods.verifyOtp.mockResolvedValueOnce({data:{session:null},error:{code:'otp_expired'}} as never);
 await user.click(screen.getByRole('button',{name:'Confirmar com código'}));
 await user.type(screen.getByLabelText('E-mail'),'new@example.com');
 await user.type(screen.getByLabelText('Código de confirmação'),'123456');
 await user.click(screen.getByRole('button',{name:'Confirmar código'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('expirou');
 expect(screen.queryByText('E-mail confirmado')).not.toBeInTheDocument();
 expect(methods.verifyOtp).toHaveBeenCalledWith({email:'new@example.com',token:'123456',type:'email'});
});

it('resends signup confirmation with a cooldown and preserves the selected email',async()=>{
 const {methods,user}=setup();await user.click(screen.getByRole('button',{name:'Confirmar com código'}));
 await user.type(screen.getByLabelText('E-mail'),'new@example.com');
 await user.click(screen.getByRole('button',{name:'Reenviar confirmação'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Confira');
 expect(methods.resend).toHaveBeenCalledWith({type:'signup',email:'new@example.com',options:{emailRedirectTo:expect.stringMatching(/\/auth\/callback\?flow=[0-9a-f-]+$/)}});
 expect(screen.getByRole('button',{name:/Reenviar em/})).toBeDisabled();
 expect(screen.getByLabelText('E-mail')).toHaveValue('new@example.com');
});
