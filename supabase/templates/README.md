# E-mail de confirmação NEXUS

Template: `confirmation.html`. Assunto: **Confirme seu e-mail e abra seu workspace · NEXUS**.

Publicar somente em NEXUS Auth (`mszdilxysgnmkyekknat`), Authentication → Emails →
Confirm sign up. Preservar SMTP Brevo e configuração de OAuth/segurança. Não mudar
o template de recuperação ou magic link nesta entrega.

`{{ .Token }}` fornece o código do Supabase. O botão usa `{{ .TokenHash }}` no
fragmento de `/auth/confirm`; o app exige confirmação explícita antes de validar
a prova e remove o fragmento. Nem código nem hash devem aparecer em logs/analytics.
Desabilitar rastreamento/reescrita de links no provedor se estiver habilitado.

Publicar a UI compatível antes do template. Links antigos permanecem consumíveis
pelo Supabase, mas podem exigir entrar com senha depois de confirmar o endereço.
O código é validado com `verifyOtp({email,token,type:'email'})`; reenvio usa
`resend({type:'signup',email})`, com callbackUrl PKCE para preservar mensagens
emitidas durante a troca de template. A UI é de confirmação de conta; o tipo
genérico `email` também aceita outras provas de e-mail reconhecidas pelo provedor.

Referências: [templates](https://supabase.com/docs/guides/auth/auth-email-templates)
e [verifyOtp](https://supabase.com/docs/reference/javascript/auth-verifyotp).
