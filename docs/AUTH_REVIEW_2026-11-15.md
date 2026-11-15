# NEXUS — revisão de autenticação e preparação de release

Continuação em 15/11/2026 da implementação `feat/supabase-auth` (`ce717d4`).
Branch de revisão: `codex/auth-release-review-2026-11-15`.
Base de integração: `main` / `e864665`.

## Comportamento corrigido

1. Claims `session_id` com número, lista ou objeto eram passadas a `UUID` e
   podiam causar erro 500. IDs agora precisam ser strings antes do parsing;
   tokens inválidos recebem 401.
2. A presença de `intent=recovery` na URL ativava a troca de senha sem prova de
   recuperação. O contexto agora nasce somente de `PASSWORD_RECOVERY` do SDK e
   fica vinculado ao usuário e ao `session_id`. Uma sessão diferente não herda
   o contexto. O identificador lido no cliente controla apenas a interface;
   a autoridade de autenticação continua no servidor/provedor.
3. Ao trocar de conta, o workspace anterior continuava visível enquanto o novo
   bootstrap aguardava resposta. Ele agora é removido imediatamente. Respostas
   de refresh e consulta inicial anteriores à troca não restauram a conta velha.
4. `INITIAL_SESSION` podia abrir a conta persistida antes de concluir um callback
   PKCE e ocultar um erro posterior. O callback agora precisa terminar antes de
   usar esse estado inicial; uma notificação inicial não elimina o erro.
5. Uma rejeição 401 persistente após refresh podia provocar um ciclo ilimitado
   de bootstrap/refresh. Há uma recuperação automática por tentativa, seguida de
   erro visível e retomada explícita. Nenhuma operação de negócio é repetida.
6. Um primeiro login concorrente podia encontrar o subject ausente e, logo após
   outro commit, encontrar o e-mail existente e retornar 409 ao próprio titular.
   O insert agora usa as restrições únicas e, após rollback, consulta o subject
   exato. Colisões de contas distintas continuam sem associação automática.
7. Um admin Supabase ainda podia criar usuário por senha local e reservar um
   e-mail de terceiro, bloqueando o bootstrap do titular. Essa criação fica
   desabilitada no modo Supabase. O modo legado permanece compatível. Convites
   continuam fora do escopo; não foram implementados como substituição.

## Evidências desta execução

As regressões foram observadas falhando antes das respectivas correções:

- `session_id` não textual causou `AttributeError` em três casos.
- Estado de recuperação por URL/sessão incorreta, workspace anterior, refresh
  tardio e consulta inicial antiga falharam nos testes de frontend.
- Callback inválido com `INITIAL_SESSION` abriu a sessão antiga ou perdeu erro.
- API recusando tokens renovados produziu milhares de consultas no teste.
- Ordem forçada entre consultas de subject/e-mail retornou 409; criação local
  no modo Supabase retornou 201 quando deveria ser recusada.

Validação final executada em bancos locais descartáveis, sem banco de produção:

| Verificação | Resultado |
| --- | --- |
| Backend completo PostgreSQL 17 | **187 passed**, 2 warnings |
| Backend completo SQLite | **153 passed, 34 skipped**, 1 warning |
| Alembic do zero + drift check PostgreSQL/SQLite | **passou** |
| Frontend Vitest | **34 passed**, 7 arquivos |
| TypeScript + Vite, configuração Supabase sintética | **passou** |
| Playwright, jornada negócio real em PostgreSQL e mobile | **2 passed**, 35,6 s |
| `git diff --check` | **passou** |

Os 34 skips SQLite cobrem recursos cuja prova requer PostgreSQL; a suíte
PostgreSQL foi executada sem skips. Os E2E de negócio usam modo legacy conforme
a configuração existente: comprovam regressão do ERP, não OAuth Google/GitHub.
Build Supabase usou origem/chave públicas sintéticas de teste, não valores de
produção. Warnings: Starlette/httpx, Alembic `path_separator` e bundle Supabase
acima de 500 kB. Não foram ocultados nem tratados como falhas funcionais.

## Revisão e limites

Uma revisão independente da branch e do SDK instalado identificou quatro dos
problemas acima. Todos foram reproduzidos e corrigidos na mesma rodada; o diff
final recebeu inspeção local e as suítes completas passaram depois das mudanças.
Isso não equivale a pentest ou homologação do provedor real.

Endurecimento posterior: remover proativamente provas PKCE abandonadas/vencidas
do prefixo próprio em localStorage (hoje a expiração é aplicada na leitura);
ampliar casos de algoritmo JWT proibido e usuário rebaixado no RBAC com metadata
antiga; otimizar o chunk Supabase. Abas duplicadas pelo navegador podem herdar
sessionStorage inicial; isolamento de canais entre abas independentes não deve
ser anunciado como proteção contra essa cópia feita pelo próprio navegador.

JWT já emitido pode continuar válido até expirar mesmo após logout no provedor.
Esta versão verifica assinatura/claims e o usuário local; não adiciona consulta
de revogação de `auth.sessions` a cada operação.

## Publicação ainda pendente

Não houve merge em main, migração Neon, configuração de secrets/env ou deploy.
O workspace listado pelo conector Render é **My Workspace**
(`tea-dbkuk5vf3r2c73fvfdvg`); sua seleção para publicação ainda requer confirmação.

Depois da aprovação de integração/publicação:

1. Integrar a branch revisada e conferir CI remoto.
2. Aplicar `0552c7d5fe36` no Neon pelo procedimento controlado de
   [DEPLOY_RENDER_NEON.md](DEPLOY_RENDER_NEON.md), antes de ativar o código.
3. Configurar API (`AUTH_PROVIDER=supabase`, `SUPABASE_URL`) e reconstruir o
   frontend com os valores públicos `VITE_*` corretos; preservar envs existentes.
4. Confirmar redirects/templates no projeto NEXUS Auth, sem alterar CareerOS.
5. Publicar API/frontend e homologar Google, GitHub, e-mail/confirm/recovery,
   refresh/logout e isolamento entre duas contas. Não enviar e-mails a terceiros
   nem registrar tokens em evidências.
6. Atualizar M6 somente com essas evidências, então produzir release/vídeo.

Manter serviços gratuitos existentes e auto-deploy desligado. Não criar novos
recursos ou promover a configuração sintética do build à produção.

## Referências consultadas

- [Plano de autenticação](superpowers/plans/2026-11-13-supabase-auth.md)
- [Handoff da implementação de 13/11](HANDOFF_2026-11-13.md)
- [Supabase: sessões](https://supabase.com/docs/guides/auth/sessions)
- [Supabase: getUser](https://supabase.com/docs/reference/javascript/auth-getuser)
- [Changelog Supabase](https://supabase.com/changelog.md), consultado em 15/11.
- Código de `@supabase/auth-js` instalado pelo lockfile (2.119.0): exchange PKCE,
  `PASSWORD_RECOVERY`, `INITIAL_SESSION` e logout local.
