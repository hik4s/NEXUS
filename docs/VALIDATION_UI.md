# M3/M4 — interface e demonstração

Plano: `docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md`, Task 6.
Base: `30c0b7e`; branch `codex/m3-m4-portfolio-ui`; data: 2026-11-09.

## Entrega

Frontend migrado para React/TypeScript com cliente HTTP tipado, token em memória,
rotas de hash e páginas separadas de acesso, resumo, importações/revisão, pedidos,
catálogo/clientes, estoque, recebíveis e auditoria. Nenhum KPI simulado na interface:
contagens, preços, saldos e registros vêm da API da empresa autenticada.

Preservados canvas escuro, bordas azul-acinzentadas, ações claras e estados
semânticos do Master Plan. Marca e Inter/OFL reaproveitados dos ativos locais
existentes; alterações de código daquele checkout original não foram copiadas.

Há estados loading/empty/error/success, labels, foco visível, diálogo nativo de
confirmação e navegação por teclado. A API continua a autoridade de permissões,
preço, estoque e recebível. A UI não inclui pagamentos manuais nem ações legadas
desativadas no perfil portfolio.

## Evidências iniciais

- Primeiro Vitest falhou por módulos ausentes antes da implementação.
- Testes adicionais reproduziram 401 antigo derrubando sessão nova, erro de login
  confundido com expiração e geração não bloqueada após 409 catalog_changed.
- O primeiro E2E desktop passou com PostgreSQL real. O mobile detectou overflow de
  tabela e foco rolando o conteúdo sob a navegação fixa. Contenção local da tabela
  e foco com preventScroll corrigiram os dois pontos; E2E desktop/mobile passaram.
- Seed: teste inicial falhou por script inexistente; depois 2 testes passaram,
  cobrindo guardas e idempotência sem repor estoque alterado.
- Auditoria não tinha paginação; teste reproduziu falta de cabeçalhos/seleção de
  página. Endpoint ganhou page/page_size opcionais e ordenação estável por data/ID,
  preservando limit e o formato de lista para consumidores anteriores.
- Revisão independente encontrou liberação precoce de formulários na recuperação
  de ação incerta. Teste reproduziu reenvio permitido antes do GET terminar; hook
  de consulta agora devolve conclusão/sucesso e só então libera as ações. Falha no
  GET conserva o bloqueio e nenhuma criação é repetida automaticamente.

## Decisões

- Versões de frontend fixas, lockfile versionado e npm ci; Node 24.15+ na linha 24.
- Audit pagination foi adaptada no backend porque era necessária à tela prevista.
- Compose usa nomes por projeto e portas configuráveis para o clone de QA não
  interferir nos bancos existentes. Dockerfiles usam lockfile/npm ci e contextos
  excluem dados, segredos, venv e node_modules locais.
- Credenciais do seed vêm de ambiente dedicado; cadastro público permanece fechado.
  Guardas recusam ambiente de produção e exigem confirmação explícita. O seed
  preserva dados existentes e deve ser executado sem outra instância simultânea.
- O leitor de estoque ainda segue o contrato atual: seletor dos primeiros 100
  produtos e últimos 30 movimentos. Isso está descrito no roteiro local, sem
  simular uma paginação que a API de movimentos não possui.

## Verificação final

Fonte implementada: commit `1944575`. Resultados em 2026-11-09:

- Node 24.21.0: npm ci, typecheck, **15 testes Vitest** e build passaram.
  Build principal: JS 281,67 kB (gzip 83,73 kB), CSS 28,42 kB (gzip 7,27 kB),
  além dos ativos locais de fonte/marca. Nenhum recurso remoto é necessário à UI.
- Playwright/Chromium: **2 E2E passaram**, em 32,4 s. A suíte cobre desktop 1440px,
  mobile 390px, teclado, duas empresas, CSV com erro, saldo antes/depois,
  recebível único, reversão e sessão descartada ao recarregar.
- Backend/PostgreSQL: **140 passed**, 2 avisos de depreciação, em 113,63 s.
- Backend/SQLite: **107 passed, 33 skipped**, 1 aviso, em 44,25 s.
- Migrações do zero e Alembic check passaram nos dois bancos, sem divergências.
- Revisão independente: achado de recuperação incerta corrigido com teste que
  falhou antes; a suíte verde inclui GET pendente, GET malsucedido e recuperação
  bem-sucedida, sem repetir POST.
- `git diff --check` e `docker compose config --quiet` passaram.

### Clone limpo e Linux

Clone local independente do commit `1944575`, sem venv/node_modules/dados copiados,
em `.superpowers/qa/clean-clone`. Compose executado com projeto exclusivo
`nexus-m4-check`, frontend/API/PostgreSQL e Redis ausente. Portas 5182/8813/55434,
restritas a loopback no ambiente de QA; PostgreSQL existente na porta 5432 intacto.
Volumes e containers eram exclusivos e descartáveis deste teste.

- `docker compose up --build -d` construiu as duas imagens e inicializou o banco.
- Readiness e página frontend responderam 200; seed executou a partir do clone.
- No container Linux frontend: typecheck, **15 testes**, build passaram via npm ci.
- Chromium contra a UI do Compose completou importar → revisar → rascunho →
  confirmar → cancelar; consulta real da API comprovou saldo restaurado,
  recebível cancelado e 404 para usuário de outra empresa.
- Contextos Docker excluem dados locais e segredos. Imagens/dados foram criados
  somente no Docker local; não houve provisionamento externo.

Capturas verificadas: [visão geral](ui-overview.png), [revisão](ui-import-review.png),
[venda confirmada](ui-order-confirmed.png), [mobile](ui-overview-mobile.png) e
[acesso mobile](ui-login-mobile.png). As capturas são de dados fictícios da API,
não mockups. Em execuções normais, E2E salva capturas em test-results; a variável
NEXUS_CAPTURE_DIR permite selecionar uma pasta de QA explicitamente.

Workflow frontend configurado com PostgreSQL, instalação reproduzível, typecheck,
Vitest, build, navegador e E2E. A execução no GitHub permanece pendente de push/
integração: resultado local não é apresentado como execução remota de CI.

Não houve publicação de serviços. Roteiro reproduzível em [LOCAL_DEMO.md](LOCAL_DEMO.md).
