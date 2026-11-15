import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,expect,it,vi} from 'vitest';
import {StrictMode} from 'react';
import type {SupabaseClient} from '@supabase/supabase-js';
import {EmailConfirmation} from '../src/features/auth/EmailConfirmation';
import {captureEmailConfirmationLink} from '../src/features/auth/emailConfirmationLink';
import {authMessage} from '../src/features/auth/SupabaseLoginPage';
afterEach(()=>history.replaceState(null,'','/'));
const hash='a'.repeat(64);
function auth(){return {auth:{verifyOtp:vi.fn(async()=>({data:{session:{access_token:'verified',user:{email:'confirmed@example.com'}}},error:null})),resend:vi.fn()}} as unknown as SupabaseClient;}

it('removes the proof from the address and rejects recovery-labelled confirmation routes',()=>{
 history.replaceState(null,'','/auth/confirm#token_hash='+hash+'&type=email');
 expect(captureEmailConfirmationLink()).toEqual({requested:true,tokenHash:hash});
 expect(location.href).not.toContain(hash);
 history.replaceState(null,'','/auth/confirm#token_hash='+hash+'&type=recovery');
 expect(captureEmailConfirmationLink().tokenHash).toBeNull();
 expect(location.href).not.toContain(hash);
});

it('locks the link action while a code is being verified and waits for that result',async()=>{
 const client=auth();let resolve!:(value:unknown)=>void;
 vi.mocked(client.auth.verifyOtp).mockImplementation(()=>new Promise(done=>{resolve=done as typeof resolve;}) as never);
 render(<EmailConfirmation auth={client} tokenHash={hash} onContinue={()=>{}}/>);
 const user=userEvent.setup();await user.type(screen.getByLabelText('E-mail'),'code@example.com');
 await user.type(screen.getByLabelText('Código de confirmação'),'123456');
 await user.click(screen.getByRole('button',{name:'Confirmar código'}));
 expect(screen.getByRole('button',{name:'Confirmar meu e-mail'})).toBeDisabled();
 await user.click(screen.getByRole('button',{name:'Confirmar meu e-mail'}));
 expect(client.auth.verifyOtp).toHaveBeenCalledTimes(1);
 resolve({data:{session:{access_token:'verified',user:{email:'code@example.com'}}},error:null});
 expect(await screen.findByText('code@example.com')).toBeVisible();
});

it('does not consume a confirmation link on page load, including StrictMode',async()=>{
 const client=auth();render(<StrictMode><EmailConfirmation auth={client} tokenHash={hash} onContinue={()=>{}}/></StrictMode>);
 expect(client.auth.verifyOtp).not.toHaveBeenCalled();
 await userEvent.click(screen.getByRole('button',{name:'Confirmar meu e-mail'}));
 expect(await screen.findByRole('heading',{name:'E-mail confirmado'})).toBeVisible();
 expect(client.auth.verifyOtp).toHaveBeenCalledWith({token_hash:hash,type:'email'});
});

it('shows code fallback when the link has expired without opening a workspace',async()=>{
 const client=auth();vi.mocked(client.auth.verifyOtp).mockResolvedValue({data:{user:null,session:null},error:{code:'otp_expired'}} as never);
 render(<EmailConfirmation auth={client} tokenHash={hash} onContinue={()=>{}}/>);
 await userEvent.click(screen.getByRole('button',{name:'Confirmar meu e-mail'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('expirou');
 expect(screen.getByLabelText('Código de confirmação')).toBeVisible();
 expect(screen.queryByRole('button',{name:'Abrir meu workspace'})).not.toBeInTheDocument();
});

it('explains how to recover an old implicit or missing-PKCE callback',()=>{
 expect(authMessage({code:'legacy_confirmation_link'})).toContain('senha');
 expect(authMessage({name:'AuthPKCECodeVerifierMissingError'})).toContain('código');
});
