# NEXUS — autenticação publicada em 15/11/2026

O usuário aprovou a integração do PR e a publicação no workspace Render
**My Workspace**. [PR #3](https://github.com/hik4s/NEXUS/pull/3) integrado em
`ba91b3b59bfe7ffb1e96af9b0e4731aa82cd8812`; correções em `ba9c383` sobre `ce717d4`.

## Estado publicado

- [Interface](https://nexus-portfolio-ui.onrender.com): deploy
  `dep-dbssagtckfvc73c37vs0`, **live**, revisão `ba91b3b`.
- [API/readiness](https://nexus-up1i.onrender.com/readiness): deploy
  `dep-dbssae56e07s73ao9n7g`, **live**, mesma revisão.
- Workspace confirmado: `tea-dbkuk5vf3r2c73fvfdvg`.
- Serviços existentes preservados, API Free, Static Site e Neon; auto-deploy
  continua desligado. Nenhum recurso pago/extra foi criado.
- API em `AUTH_PROVIDER=supabase`; login/cadastro/refresh legados desabilitados.
- UI reconstruída com origem NEXUS Auth e chave publishable pública; nenhuma
  secret/service_role foi enviada ao frontend. Env existente foi preservado.

## Banco

O alvo direto Neon existente foi conferido na revisão `d82b966f6b46` antes da
alteração. Um backup custom foi criado e seu índice lido por `pg_restore --list`:
240.874 bytes, SHA-256
`41ec31ecc7c0823b9142c24caf0d499963418b47e76c394ee5eb41de360be2d9`.
O arquivo permanece privado no computador, fora do Git; esta leitura não é um
novo exercício de restauração completa.

`scripts/migrate_release.py` aplicou `0552c7d5fe36` com alvo explícito, TLS e
advisory lock. Drift check passou antes da ativação dos serviços. A migração
adiciona o vínculo de subject e preserva usuários/empresas legados. Não houve
associação automática de contas por e-mail.

## Validação em HTTPS real

Dois usuários **sintéticos**, confirmados administrativamente apenas para o teste,
foram criados no projeto NEXUS Auth. Não houve envio de e-mail a terceiros.

- Readiness respondeu 200; login legado retornou 403.
- Login por senha real no Supabase para as duas contas.
- Bootstrap real da API criou empresas distintas; repetição manteve o mesmo ID.
- A segunda conta não conseguiu consultar a empresa da primeira.
- Admin autenticado não pôde criar usuário local por senha.
- Edge headless abriu a UI pública, entrou com a conta sintética, mostrou o
  workspace próprio, manteve a sessão após reload e saiu corretamente.
- Reload depois do logout permaneceu na tela de entrada.
- Viewport autenticado de 390 × 844 sem transbordamento horizontal.
- Botões Google/GitHub presentes e endpoints reais de autorização responderam
  302 para as origens dos respectivos provedores.

Ao terminar, os dois usuários sintéticos foram removidos do Supabase; as empresas
vazias foram removidas do Neon com guardas pelo subject/e-mail/slug exatos criados
pelo teste. A limpeza terminou com sucesso; nenhum dado anterior foi removido.

## Validação anterior ao deploy

- CI remoto [backend](https://github.com/hik4s/NEXUS/actions/runs/43725642955)
  e [frontend](https://github.com/hik4s/NEXUS/actions/runs/43725642953): **success**
  no commit de revisão do PR.
- PostgreSQL local: 187 passed; SQLite: 153 passed, 34 skipped.
- Frontend: 34 passed; typecheck/build e dois E2E de negócio passaram.
- [Revisão e regressões](AUTH_REVIEW_2026-11-15.md) documentam sete correções e
  os avisos conhecidos. Não se reexecutou toda a suíte contra banco de produção.

## O que ainda não foi comprovado

- Conclusão de login Google/GitHub por uma pessoa real, incluindo retorno ao
  callback publicado. Redirecionar ao provedor não comprova conclusão OAuth.
- Entrega de e-mail/confirm/recovery com PKCE em nova aba no ambiente publicado;
  usuários do smoke foram confirmados pela administração, não por mensagem.
- Medição de cold start por hibernação natural, vídeos e release editorial M6.
- Limpeza proativa de provas PKCE abandonadas e otimização do chunk Supabase.

Portanto, **publicação e login por senha/isolamento estão comprovados**;
homologação integral dos provedores e M6 continuam abertos. O próximo passo é
concluir os logins reais e a confirmação/recuperação, registrar evidências sem
tokens e só então fechar o marco de autenticação no plano.

Os documentos de 13/11 e a revisão pré-deploy descrevem checkpoints anteriores;
esta publicação supera suas pendências de integração, migração e deploy.
