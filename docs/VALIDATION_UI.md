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

Resultados de regressão e clone limpo serão consolidados após a execução.
Não houve publicação de serviços. Roteiro reproduzível em [LOCAL_DEMO.md](LOCAL_DEMO.md).
