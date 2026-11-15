export function authMessage(error:unknown):string {
 const code=error&&typeof error==='object'&&'code' in error?String(error.code):'';
 const name=error&&typeof error==='object'&&'name' in error?String(error.name):'';
 const messages:Record<string,string>={
  invalid_credentials:'E-mail ou senha não conferem.',
  email_not_confirmed:'Confirme seu e-mail pelo link ou use o código recebido antes de entrar.',
  user_already_exists:'Este e-mail já possui uma conta. Entre ou recupere sua senha.',
  weak_password:'Use uma senha mais forte, com pelo menos 8 caracteres.',
  over_email_send_rate_limit:'Aguarde alguns minutos antes de solicitar outro e-mail.',
  over_request_rate_limit:'Muitas tentativas. Aguarde um momento e tente novamente.',
  same_password:'Escolha uma senha diferente da anterior.',
  otp_expired:'Este código ou link expirou ou já foi utilizado. Solicite uma nova confirmação.',
  legacy_confirmation_link:'Seu e-mail pode já estar confirmado. Entre com sua senha ou solicite uma nova confirmação por código.',
  flow_state_not_found:'Não encontramos o início desta confirmação. Entre com sua senha ou solicite um novo código.',
  flow_state_expired:'Esta confirmação expirou. Solicite um novo código ou entre com sua senha se o e-mail já foi confirmado.',
  bad_code_verifier:'Não foi possível retomar este link neste navegador. Use o código ou entre com sua senha se o e-mail já foi confirmado.',
  confirmation_session_missing:'A confirmação não retornou uma sessão válida. Solicite um novo código ou entre com sua senha.',
 };
 if(name==='AuthPKCECodeVerifierMissingError')return messages.bad_code_verifier;
 return messages[code]||'Não foi possível concluir o acesso. Tente novamente em instantes.';
}
