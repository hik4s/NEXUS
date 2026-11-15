# Confirmação por link e código — NEXUS

## Problema e comportamento

O provedor confirmou um endereço após o clique no e-mail padrão, mas o app não
concluiu a sessão e mostrou um erro genérico. O template dependia do retorno da
URL do provedor e a interface não oferecia alternativa por código.

A nova confirmação tem duas opções no mesmo e-mail:

- Botão abre `/auth/confirm#token_hash=…&type=email`; o app limpa o fragmento e só
  consome a prova após clique explícito. Não exige o navegador de origem do cadastro
  e não consome a prova em pré-carregamento de links.
- Código de uso único digitado com o e-mail. Após cadastro, o formulário aparece
  automaticamente; também há “Confirmar com código” no login. A senha é removida
  do formulário ao entrar nessa etapa. Reenvio de cadastro tem cooldown de 60 s
  e usa o mesmo callback PKCE existente para compatibilidade durante a troca.

Uma trava compartilhada impede concorrência entre link, código, reenvio e saída.
O sucesso mostra o e-mail retornado pelo provedor antes de abrir seu workspace.
Erros/expiração não produzem sucesso. Um callback antigo com sessão já presente
fica isolado dos eventos de restauração do SDK até um novo resultado explícito
de login por senha ou código, sem aceitar bearer token do fragmento.

O tipo Supabase `email` também aceita outras provas de e-mail suportadas pelo
provedor; não é uma garantia criptográfica de origem exclusivamente no cadastro.
O fluxo dedicado de recuperação/OAuth permanece separado na interface.

## Arquivos

- `frontend/src/features/auth/EmailConfirmation.tsx`: tela de link e sucesso.
- `EmailCodeForm.tsx`, `useAuthOperation.ts`: código, reenvio e trava compartilhada.
- `emailConfirmationLink.ts`: captura única e limpeza da URL antes de StrictMode.
- `authMessages.ts`: erros em português, inclusive links antigos/prova ausente.
- `useManagedAuth.ts`, `SupabaseLoginPage.tsx`, `LoginPage.tsx`, `App.tsx`: integração.
- `supabase/templates/confirmation.html`: modelo versionado, pt-BR, botão e OTP.

## Verificação antes da publicação

- **43 testes frontend** em 8 arquivos; TypeScript e build passaram.
- **2 E2E** de negócio em PostgreSQL passaram, incluindo mobile, 34,4 s.
- Regressões observadas RED antes das correções: ausência de código/reenvio;
  operações concorrentes; sessão restaurada após callback inválido; callback de
  reenvio incompatível com o template anterior.
- Provas reais de cadastro foram geradas administrativamente no NEXUS Auth sem
  enviar mensagens: verificação por código e por hash retornou as identidades
  esperadas. Contas sintéticas removidas ao terminar.
- Modelo renderizado em desktop 640 px e mobile 390 px; OTP/botão legíveis,
  sem transbordamento. Prévia usa valores fictícios.
- Revisão independente identificou as condições de corrida e compatibilidade;
  correções receberam regressões e inspeção final do diff.

Backend e migrações não foram alterados nesta entrega. O build Supabase continua
com aviso de chunk >500 kB. Mensagens SMTP reais, reputação do remetente e pasta
de spam dependem do provedor; a nova aparência não promete classificação na inbox.

## Publicação

Publicar frontend compatível antes de substituir o template “Confirm sign up” do
NEXUS Auth. Preservar SMTP Brevo, demais templates, OAuth, plano gratuito e dados
existentes. Confirmar publicação e testes HTTPS no complemento de release.
