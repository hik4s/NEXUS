# NEXUS Portfolio MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar a jornada de importação/revisão de pedidos, venda, estoque, recebível e cancelamento em uma demonstração web reproduzível.

**Architecture:** Evoluir o monólito modular FastAPI existente, mantendo domínio e testes. Revisão de CSV limitada e durável no PostgreSQL, frontend React/TypeScript e deploy Render + Neon sem worker obrigatório.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy 2, Alembic, PostgreSQL, React, TypeScript, Vite, pytest, Playwright, Docker Compose e GitHub Actions.

**Spec:** [MVP_PORTFOLIO.md](../../MVP_PORTFOLIO.md).
**Baseline:** 9e64214531f491ec0dabbd20e13f694afccd901c. Nenhuma tarefa de implementação foi executada nesta entrega documental.

## Global Constraints

- CSV UTF-8 com BOM opcional, separador vírgula e cabeçalho exato: external_order_id,sku,quantity.
- Limite: 1 MiB de conteúdo, 500 linhas de dados, 100 pedidos por arquivo e 200 itens por pedido.
- quantity é inteiro entre 1 e 1.000.000; external_order_id tem de 1 a 80 caracteres após trim; sku tem de 1 a 80.
- API é a autoridade de acesso; company_id vem do usuário autenticado.
- Revisão persiste no PostgreSQL; arquivo original não é retido.
- Sem worker, scheduler ou Redis obrigatório no deploy gratuito.
- Confirmar/cancelar duas vezes nunca duplica efeito.
- Não editar migrações históricas aplicadas nem remover módulos fora do recorte.
- Dados e credenciais da demonstração são fictícios/dedicados; nenhuma cobrança autorizada.
- Interface pt-BR; access token em memória; nenhum segredo em VITE_*.
- Até 20 batches/dia e 100 retidos por empresa do ator; contagem serializada por empresa para não depender da instância.
- Trabalhar em branch por etapa, revisar diff, executar os checks pertinentes e registrar evidências antes de integrar.

## Review Focus

1. Dois arquivos diferentes com mesmo external_order_id e confirmação simultânea não duplicam pedido nem movimentação — tarefas 2 e 4.
2. CSV válido por extensão mas inválido por encoding, cabeçalho ou estrutura é recusado sem estado parcial — tarefa 3.
3. Preço muda após revisão ou há falha de recebível após baixa — tarefas 2 e 4.
4. Retry após timeout/restart e tentativas com IDs de outro tenant não causam efeitos extras — tarefas 4 e 6.
5. Serviço hibernado, banco indisponível e ausência de worker/storage não deixam a UI em sucesso falso — tarefas 5 e 7.

## Mapa de arquivos

Preservar backend/app/{api,schemas,models,services,identity,rbac,audit,workers} e os testes existentes. Criar somente o necessário:

| Responsabilidade | Arquivos planejados |
| --- | --- |
| Validação CSV pura | backend/app/services/order_import_parser.py |
| Revisão/commit transacional | backend/app/services/order_import_service.py |
| Contratos HTTP | backend/app/schemas/order_imports.py |
| Estado durável | backend/app/models/order_imports.py e nova revisão Alembic |
| Rotas | backend/app/api/v1/routes/order_imports.py |
| Perfil gratuito | configuração existente + seleção de routers em api/v1/router.py |
| Sessão e HTTP da UI | frontend/src/features/auth/, frontend/src/lib/api.ts |
| Telas | frontend/src/features/{imports,sales,inventory,finance,audit}/ |
| Demo | scripts/seed_demo.py, demo/orders-valid.csv, demo/orders-with-errors.csv |
| E2E | frontend/e2e/portfolio-flow.spec.ts |
| Deploy | render.yaml, docs/DEPLOY_RENDER_NEON.md |

O nome da nova revisão Alembic será gerado pela ferramenta após conferir a head real; não supor um ID de revisão manual.

## Task 1: Baseline PostgreSQL reproduzível — M0

**Files:** modificar docker-compose.yml, .env.example, .github/workflows/backend.yml e scripts/db-check.ps1; criar backend/tests/test_postgres_baseline.py e docs/VALIDATION_MVP.md.

**Interfaces:** usar DATABASE_URL com postgresql+psycopg, engine/SessionLocal existentes e alembic upgrade head. Entregar comando de teste com banco descartável e fixtures sem dados pessoais.

- [x] Criar teste test_postgres_migrations_bootstrap que consulta alembic_version e confirma tabelas companies, sales_orders, stock_balances e accounts_receivable após upgrade de banco vazio.
- [x] Executar em PostgreSQL novo; registrar falha ou ausência da configuração, sem substituí-la por SQLite.
- [x] Corrigir variáveis de usuário/nome do Compose, permitir perfil sem Redis e incluir PostgreSQL no CI.
- [x] Executar alembic upgrade head, alembic check e python -m pytest -q com DATABASE_URL de teste. Registrar comando, versões, commit e resultado em VALIDATION_MVP.md.
- [x] Conferir que reiniciar a API não recria/apaga o banco; revisar diff e commitar.

Não usar banco de produção nem downgrade de banco com dados reais como teste.

## Task 2: Venda, estoque e recebível atômicos — M1

**Files:** modificar services/sales_service.py, inventory_service.py, finance_service.py, platform/service.py, routes/sales.py e models pertinentes somente se constraints necessárias; testar em test_inventory.py, test_finance.py, test_platform.py e novo test_sales_concurrency.py.

**Interfaces:** manter rotas e schemas SalesOrderCreate/SalesOrderStatusUpdate. Adicionar à assinatura de create_order o argumento keyword-only commit: bool = True; commit=False deixa flush e rollback ao chamador. Não alterar callers existentes sem compatibilidade.

- [x] Criar testes de duas sessões PostgreSQL confirmando o mesmo pedido; afirmar 1 fulfillment, 1 recebível, estoque debitado uma vez e uma transição bem-sucedida.
- [x] Criar test_receivable_failure_rolls_back_stock e test_paid_order_cannot_cancel; afirmar saldo/status/recebível inalterados após falha e após cancelamento proibido.
- [x] Criar teste de cancelamentos concorrentes e de replay Idempotency-Key após resposta perdida.
- [x] Rodar os testes-alvo para confirmar quais garantias já passam e quais falham.
- [x] Bloquear pedido antes da transição e manter efeitos/auditoria na mesma transação; adicionar unicidade por pedido no banco quando ausente e separar auxiliares que fazem commit.
- [x] Corrigir atomicidade de criação/idempotência para não haver pedido salvo sem resposta recuperável.
- [x] Rodar testes-alvo e regressões sales/inventory/finance/platform no PostgreSQL; revisar e commitar.

## Task 3: Parser CSV determinístico — início M2

**Files:** criar services/order_import_parser.py, schemas/order_imports.py, tests/test_order_import_parser.py e arquivos demo/orders-*.csv.

**Interfaces:** parse_order_csv(content: bytes) -> ParsedOrderFile. Schema ParsedOrderFile contém orders: list[ParsedOrder], unassigned_errors: list[ImportIssue]. ParsedOrder contém external_order_id: str, items: list[ParsedOrderItem], source_lines: list[int], errors: list[ImportIssue]. ParsedOrderItem contém sku: str e quantity: int. ImportIssue contém row: int, field: str | None, code: str e message: str. Falhas estruturais lançam OrderImportFormatError(code: str, message: str), sem banco.

- [x] Escrever testes BOM, agrupamento, SKU repetido no pedido, UTF-8 inválido, cabeçalhos duplicados/ausentes/extras e linha com colunas a mais.
- [x] Testar limites exatos: 1 MiB aceito/1 byte extra recusado; 500/501 linhas; 100/101 pedidos; quantidade 0, decimal, negativa e acima do máximo.
- [x] Testar linha sem external_order_id como erro não associado; uma linha inválida invalida o pedido inteiro.
- [x] Rodar python -m pytest -q tests/test_order_import_parser.py, confirmar falha inicial e implementar parser sem materializar entrada ilimitada.
- [x] Rodar novamente até passar; conferir que fixtures são fictícias e commitar.

## Task 4: Revisão persistida e geração de rascunhos — M2

**Files:** criar models/order_imports.py, services/order_import_service.py, api/v1/routes/order_imports.py, nova migration e tests/test_order_import_api.py; modificar models/__init__.py, api/v1/router.py e schemas/order_imports.py.

**Interfaces:** create_review(db: Session, actor: User, filename: str, content: bytes) -> tuple[OrderImportBatch, bool]; get_review(db: Session, actor: User, batch_id: UUID) -> OrderImportBatch; revalidate_review(db: Session, actor: User, batch_id: UUID) -> OrderImportBatch; commit_review(db: Session, actor: User, batch_id: UUID, entry_ids: list[UUID]) -> CommitReviewResult. Resultado tem batch_id e orders com entry_id, order_id, reused. Usar create_order(..., commit=False) da tarefa 2. Rotas e estados são os da spec.

- [x] Criar testes de revisão sem efeito em estoque, SKU desconhecido, arquivo repetido e separação entre empresas.
- [x] Criar testes para 20/21 batches diários, 100/101 retidos, seleção inválida, CSV com pedido repetido e dois batches concorrentes com a mesma referência.
- [x] Testar timeout/repetição após commit: mesmos order_ids; payload diferente sob mesma identidade externa: 409; nenhum pedido parcial na falha.
- [x] Testar preço alterado → 409 catalog_changed → revalidate → geração com novo valor explícito; snapshot anterior permanece rastreável em auditoria.
- [x] Implementar tabelas/constraints e serviço transacional, incluindo lock no batch e contagem/limites sob lock da empresa.
- [x] Exportar erros CSV com neutralização de fórmulas e teste de autorização.
- [x] Rodar python -m pytest -q tests/test_order_import_parser.py tests/test_order_import_api.py no PostgreSQL e a cadeia Alembic do zero; revisar e commitar.

Limites e constraints protegem concorrência; hash ou checagem prévia isolados não bastam.

## Task 5: Perfil público sem dependências ocultas — pré-requisito M3/M5

**Files:** modificar core/config.py, api/v1/router.py, main.py e rbac/constants.py; criar tests/test_portfolio_profile.py; ajustar tests/test_rbac.py.

**Interfaces:** APP_PROFILE = full | portfolio, padrão full para compatibilidade; PUBLIC_REGISTRATION_ENABLED = bool. No perfil portfolio permitir auth com registro condicionado, companies/users necessários, products, customers básicos, sales, inventory, finance somente leituras, audit e order-imports. Desativar mutações financeiras e rotas legadas de integrações, jobs, IA, automação, logística e compras nesse perfil.

- [ ] Criar testes: perfil portfolio inicializa com REDIS_ENABLED=false, não aceita job sem executor, não oferece upload persistente local e não expõe rotas fora do recorte.
- [ ] Testar manager com novas permissões sales e sem acesso a papéis admin/finance:pay; employee recebe 403 nas mutações do fluxo.
- [ ] Testar token expirado/inativo e 404 para UUID de outra empresa; autorização permanece no servidor.
- [ ] Implementar seleção de routers/capacidades e configurar CORS para expor os cabeçalhos de paginação usados pela UI.
- [ ] Manter segredo de produção obrigatório, readiness com timeout e resposta de erro sem segredos.
- [ ] Rodar python -m pytest -q tests/test_portfolio_profile.py tests/test_rbac.py tests/test_auth.py; revisar e commitar.

## Task 6: Interface TypeScript e demonstração integrada — M3/M4

**Files:** criar tsconfig e configuração de testes, frontend/src/lib/api.ts, features/{auth,imports,sales,inventory,finance,audit}, frontend/e2e/portfolio-flow.spec.ts, scripts/seed_demo.py e frontend/package-lock.json; migrar App.jsx/main.jsx; modificar package.json, CSS e adicionar CI frontend.

**Interfaces:** API_BASE_URL de VITE_API_BASE_URL; ApiError {status, code, message}; token de sessão em memória. Tipos gerados do OpenAPI de desenvolvimento ou tipados contra schemas, sem duplicar regras financeiras no cliente. Scripts npm: typecheck, test, build, test:e2e. Seed executa explicitamente no banco de demonstração, com flag de ambiente e comportamento idempotente.

- [ ] Criar teste E2E com duas empresas: importar arquivo com um pedido válido e um inválido, revisar, gerar rascunho, confirmar e cancelar; afirmar estoque e recebível.
- [ ] Adicionar testes de UI para 401, 403, 409 catalog_changed, serviço indisponível e seleção inválida.
- [ ] Implementar páginas pt-BR, navegação por teclado e estados loading/empty/error/success; separar cadastro inicial de estoque/catálogo do fluxo de importação.
- [ ] Impedir double-submit e não repetir mutações automaticamente em timeout; consulta GET recupera estado salvo.
- [ ] Migrar JS incrementalmente, fixar versões compatíveis após build e versionar lockfile; não manter latest.
- [ ] Executar npm ci, npm run typecheck, npm test -- --run, npm run build e npm run test:e2e contra API real com PostgreSQL e dados fictícios.
- [ ] Documentar execução local; conferir clone novo com Docker Compose, capturar evidências e commitar.

## Task 7: Publicação Render + Neon — M5

**Files:** criar render.yaml, docs/DEPLOY_RENDER_NEON.md e scripts/migrate_release.py; ajustar config de DB/health e adicionar tests/test_release_config.py.

**Interfaces:** render.yaml define apenas Static Site e Web Service gratuito. API usa PORT; DATABASE_URL TLS e segredo somente no backend; conexão direta para migrações configurada no ambiente do comando, não no bundle. Perfil portfolio, Redis desligado e registro público desabilitado até existir controle de abuso.

- [ ] Testar configuração de produção: segredo padrão recusado, SQLite recusado no perfil publicado e ausência de banco/health sem falsa prontidão.
- [ ] Definir build/start/redirect SPA/origens explícitas, timeouts e pool compatíveis com Neon. Não criar Postgres temporário do Render.
- [ ] Implementar migração controlada de release: conferir alvo/ambiente, aplicar Alembic e registrar revisão sem imprimir segredo; validar contra banco descartável.
- [ ] Validar Blueprint com ferramenta oficial disponível e confirmar diff sem secrets; registrar quando a validação externa não estiver disponível.
- [ ] Criar recursos somente dentro das cotas gratuitas e conectar contas necessárias. Se faltar acesso, registrar o passo exato pendente; não inventar URL de deploy.
- [ ] Executar smoke test público: login, revisão, commit, confirmação, cancelamento, persistência após restart e estado de inicialização/cold start.
- [ ] Testar exportação e restauração do banco fictício, registrar limitações e commitar a documentação validada.

Não marcar M5 concluída só porque render.yaml foi escrito.

## Task 8: Release de portfólio — M6

**Files:** atualizar README.md, MASTER_PLAN.md, docs/VALIDATION_MVP.md, docs/DEPLOY_RENDER_NEON.md e adicionar docs/media com capturas reais e vídeo/link.

**Interfaces:** usa o fluxo E2E da tarefa 6 e deploy da tarefa 7; todos os resultados são vinculados ao commit testado.

- [ ] Executar regressão backend/PostgreSQL, frontend typecheck/test/build e E2E da release.
- [ ] Gravar vídeo de até dois minutos e screenshots com dados fictícios; mostrar uma falha além do caminho feliz.
- [ ] Publicar arquitetura, setup, conta demo limitada, CSV de exemplo, decisões e limites com links verificáveis.
- [ ] Registrar tempos observados e condições do teste; não alegar economia/escala de empresa sem medição.
- [ ] Revisar conteúdo e diff, criar tag/release e atualizar checklist apenas com evidências.

## Auto-revisão do plano

- Spec coberta por tarefas 1–8; limites e permissões têm testes previstos.
- Fluxos legados preservados; alterações de perfil evitam jobs e anexos não operacionais na demo.
- Revalidação resolve mudança de catálogo sem exigir alteração artificial do CSV/hash.
- Commit de lote depende da variante flush-only de create_order; não compor commits intermediários.
- O pipeline PostgreSQL e o E2E são requisitos de release, não alegações sobre o estado atual.
- IA, workers contínuos, mobile/offline e AWS ficam fora do recorte, conforme spec.

## Continuidade

A primeira execução de implementação é Task 1/M0. Antes de editar código, conferir HEAD e alterações pendentes, ler a spec e este plano, abrir branch da etapa e registrar os resultados reais. Etapas de documentação estão concluídas somente após publicação e verificação dos arquivos; as tarefas de código acima permanecem abertas.
