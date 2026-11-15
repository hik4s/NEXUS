# Confirmação NEXUS por link e código

Pedido aprovado: melhorar o e-mail de confirmação, corrigir o retorno que confirmou
o endereço mas não abriu o app e oferecer código além do link. Continuar mantendo
Supabase como autoridade e a sessão por aba. Sem desabilitar confirmação.

## Comportamento

- E-mail em pt-BR, fundo claro, cabeçalho azul NEXUS, botão de confirmação e código
  OTP destacado; explicar uso único, spam e que não é necessário usar ambos.
- Botão abre `/auth/confirm#token_hash=...&type=email`. Fragmento não é enviado ao
  servidor estático. O app remove a prova da URL e pede confirmação explícita
  antes de `verifyOtp`; pré-carregamento de e-mail não consome o token.
- Após cadastro sem sessão, mostrar entrada de código e reenvio de confirmação,
  sem guardar senha/código. A opção também fica acessível na tela de login.
- Código usa e-mail + `verifyOtp(type=email)`, sessão só se provedor retornar sucesso.
  Reenvio usa `resend(type=signup)`, cooldown e erros honestos de limite/expiração.
- Verificação `type=email` aceita provas de e-mail do provedor; não afirmar
  exclusividade criptográfica de signup. O fluxo dedicado de recovery é preservado.
- Link usado/inválido oferece código/reenvio/voltar ao login. Sessão pré-existente
  não aparece antes de a pessoa decidir confirmar ou sair desse fluxo.
- OAuth/recuperação PKCE existentes permanecem separados. Erros antigos por token
  implícito ou prova PKCE ausente orientam entrar com senha/solicitar código novo.

## Limites e validação

Configurar somente o template de confirmação do projeto NEXUS Auth; preservar
SMTP Brevo, OAuth, políticas e CareerOS. Template fica no Git e no Supabase.
Testar link/código reais em usuários sintéticos sem enviar e-mails a terceiros,
erros, reenvio, StrictMode, mobile, troca de conta e regressões de sessão.
Prévia de e-mail deve ser renderizada e inspecionada em desktop/mobile.
