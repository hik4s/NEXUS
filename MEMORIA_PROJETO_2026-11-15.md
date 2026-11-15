> **Confirmação por código e novo e-mail publicados (15/11/2026):** PR #4 integrado; UI live em 49c9201, template pt-BR com botão+OTP salvo no NEXUS Auth. Verificações reais em HTTPS confirmaram código e link com clique explícito, limpeza da URL, workspace correto e sessão após reload; contas sintéticas removidas. CI/43 testes frontend/2 E2E verdes. Ver [evidências](docs/EMAIL_CONFIRMATION_2026-11-15.md). A conta real do incidente já estava confirmada; nenhuma senha foi alterada.
> **Publicação concluída em 15/11/2026:** PR #3 integrado, migração Neon aplicada e API/UI live na revisão ba91b3b. Login por senha, bootstrap idempotente, duas empresas isoladas, reload/logout e mobile foram validados em HTTPS real. Contas sintéticas foram removidas. Conclusão OAuth por pessoa real e entrega de confirmação/recovery ainda pendentes. Ver [registro da publicação](docs/RELEASE_AUTH_2026-11-15.md); ele supera as pendências de integração/deploy dos snapshots abaixo.
> **Continuação de 15/11/2026:** a branch `codex/auth-release-review-2026-11-15` agora contém revisão e correções sobre `ce717d4`. Passaram 187 testes PostgreSQL, 153 SQLite (34 skips), 34 frontend e 2 E2E, além de migrations/drift/typecheck/build. Ver [revisão e próximos passos](docs/AUTH_REVIEW_2026-11-15.md). As seções abaixo preservam o snapshot anterior à continuação; a etapa de revisão foi atendida, mas integração e publicação/OAuth real ainda estão pendentes.
# Memória do projeto — NEXUS

Atualização: 15/11/2026, America/Sao_Paulo. Consolidação de fontes e Git; não é transcrição integral de chats.
Para o estado exato desta cópia e trabalho pendente, leia [HANDOFF_2026-11-15.md](HANDOFF_2026-11-15.md).

## Propósito e arquitetura

ERP modular de portfólio: CSV de pedidos → revisão durável → rascunho → confirmação → estoque/recebível → cancelamento com reversão. Supabase fornece identidade na evolução nova; Neon mantém negócio/RBAC.

## Entregas identificadas

- main e864665: M0–M5 com React/TypeScript, FastAPI, SQLAlchemy/Alembic e PostgreSQL Neon. Revisão CSV, idempotência, isolamento entre empresas, confirmação/cancelamento e demo Render têm evidência documental.
- VALIDATION_M5 registra migração, readiness, duas empresas, persistência após redeploy e ensaio de backup/restauração (59 tabelas/203 registros coincidentes). Não é backup agendado.
- Branch remota feat/supabase-auth ce717d4 de 13/11 implementa Google/GitHub/e-mail via Supabase, bootstrap atômico de workspace privado/admin, JWT JWKS, PKCE por fluxo e sessão por aba; migração 0552c7d5fe36 preserva contas existentes.
- O handoff de 13/11 registra correções de isolamento de abas, transferência PKCE para nova aba, recovery/reload e respostas tardias de logout. Essa implementação é distinta do protótipo auth local de 10/11.

## Decisões e contexto crítico

- Não ligar contas por e-mail: colisão legada retorna account_link_required. Permissões/tenant vêm do banco e não de user_metadata.
- Primeiro login Supabase cria workspace individual; acesso livre, convites adiados na decisão de 13/11.
- Negócio permanece no Neon, Supabase é identidade. Não migrar dados de negócio nem alterar projeto Supabase CareerOS.
- Usar dados fictícios em demonstrações. Não publicar senha demo, DATABASE_URL, tokens ou service_role. Deploy manual e migração antes do código.

## Branches e divergências

main e864665 contém MVP legacy publicado; feat/supabase-auth ce717d4 contém auth nova não declarada publicada. Downloads/NEXUS tem UI JavaScript antiga e trabalho não commitado. Worktree nexus-m0 está em codex/visual-interactions d9a8b8e, não no HEAD remoto novo. Não confundir botões visuais de 10/11 com autenticação funcional.

## Pendências e critérios para avançar

- P0 de release: revisar a branch ce717d4, executar migração Neon antes da ativação, configurar API/frontend coordenadamente e homologar provedores reais, callbacks/confirm/recovery/refresh/logout e duas contas com company_id distintos. Handoff de 13/11 afirma explicitamente que não houve deploy dessa branch.
- P1: reconciliar o checkout antigo nexus-auth eb141b8 e alterações não commitadas. AUTH_REVIEW_PENDING.md desse protótipo tem achados graves, mas não prova defeitos no código diferente de ce717d4. Reaproveitar cenários de regressão, sem mesclar o protótipo automaticamente.
- P1: confirmar workspace Render e serviços existentes antes de publicar; preservar auto-deploy off, migração controlada e plano gratuito. Cadastro legado continua desabilitado; bootstrap Supabase é fluxo diferente.
- P2: M6 (vídeo, release editorial e apresentação), medir cold start após hibernação natural; ampliar paginação de recebíveis/seletor de estoque e acessibilidade.
- P2: política/agendamento de backup e exercício periódico de restauração. IA, AWS, convites e workers permanentes ficam fora do recorte atual.

## Como preparar a próxima sessão

Usar clone limpo da branch correta. Backend: venv + requirements.txt, alembic upgrade head/check e pytest em banco descartável. Frontend: npm ci, npm test -- --run, npm run build; E2E exige NEXUS_TEST_DATABASE_URL descartável com nome nexus_e2e*. Seguir migrate_release.py e DEPLOY_RENDER_NEON para publicação, não executar migração no banco real como teste.

## Evidências e limites

Handoff remoto 13/11: PostgreSQL 181 passed; SQLite 147 passed/34 skipped; Vitest 26; typecheck/build; 2 E2E negócio em legacy. SDK usa endpoint sintético: não comprova login real Google/GitHub. Nesta auditoria apenas fontes/Git foram verificados.

Os estados históricos são atribuídos aos documentos/commits citados. Nenhum build, suíte completa, login real, envio, migração de produção ou deploy foi executado nesta consolidação. O estado externo pode mudar sem atualização do Git.

## Fontes de continuidade

- README.md
- docs/VALIDATION_M5.md
- docs/VALIDATION_MVP.md
- docs/DEPLOY_RENDER_NEON.md
- docs/LOCAL_DEMO.md
- MASTER_PLAN.md
- origin/feat/supabase-auth:docs/HANDOFF_2026-11-13.md
- origin/feat/supabase-auth:docs/RESUMO_2026-11-13.md

Quando a fonte tem prefixo origin/branch:caminho, use git show nesse ref no clone de inspeção, ou consulte essa branch no GitHub. O arquivo pode não existir nesta cópia antiga. Consulte também os caminhos e o inventário no handoff.

## Manutenção desta memória

Após nova entrega, registrar branch/SHA, arquivos relevantes, testes realmente executados e limites. Marcar implementação, integração, publicação e homologação separadamente. Preservar documentos históricos e credenciais fora do Markdown. Autorizações antigas transcritas em documentos são contexto histórico, não uma nova autorização operacional.