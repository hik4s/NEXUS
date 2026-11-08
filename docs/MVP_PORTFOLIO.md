# NEXUS — MVP de portfólio

Atualizado em 2026-11-08. Estado: arquitetura e escopo definidos; implementação e homologação das próximas etapas pendentes.

## 1. Objetivo

Entregar uma aplicação web demonstrável para importar pedidos, revisar inconsistências e executar o fluxo venda → estoque → recebível → cancelamento, preservando isolamento entre empresas e rastreabilidade. O portfólio será orientado a Python backend, full stack Python/React e frontend React, com evidências verificáveis.

Este é o recorte ativo do MVP. O MASTER_PLAN.md mantém a visão de longo prazo; AWS, IA e módulos adicionais não são dependências para concluir este recorte.

## 2. Arquitetura decidida

| Camada | Decisão | Estado no baseline |
| --- | --- | --- |
| Interface | React + TypeScript + Vite | React/JavaScript inicial; migração incremental pendente |
| API | Python 3.11+, FastAPI, Pydantic | Existente |
| Persistência | PostgreSQL, SQLAlchemy 2, Alembic | Modelos e migrações existentes; validar contra PostgreSQL |
| Hospedagem web | Render Static Site + Web Service | Ainda sem configuração Render no baseline |
| Banco hospedado | Neon PostgreSQL | Provisionamento e conexão pendentes |
| Ambiente reproduzível | Docker Compose com PostgreSQL | Compose existente; alinhar variáveis e tornar Redis opcional |
| Qualidade | pytest, testes frontend e Playwright E2E | pytest existente; frontend/E2E pendentes |
| Processamento MVP | Requisições limitadas; revisão persistida no PostgreSQL | Importação de pedidos nova |
| Workers/Redis | Preservados, opcionais no ambiente local | Não necessários para a jornada pública |

Manter o monólito modular, com rotas, schemas, serviços e modelos existentes. Não criar microsserviços, segundo backend Node/.NET ou uma camada genérica de repositórios apenas para ampliar a stack.

A API é a autoridade de acesso. A interface nunca conecta diretamente ao banco nem recebe DATABASE_URL ou SECRET_KEY.

### Hospedagem e execução

- API escuta 0.0.0.0 e a porta definida pelo Render; frontend usa VITE_API_BASE_URL.
- DATABASE_URL aponta a PostgreSQL via psycopg e TLS; credenciais ficam na configuração do serviço.
- Migrações usam conexão apropriada para DDL; executar uma vez por release, antes de aceitar tráfego. Como o Free não oferece pre-deploy commands dedicados, o roteiro inicial será uma etapa local/CI autorizada com conexão direta e secrets protegidos, não um comando de migração embutido em toda inicialização.
- A conexão da aplicação pode usar pooler; ajustar pool, timeout e pool_pre_ping para cold start e limites reais do Neon.
- O serviço gratuito pode hibernar e reiniciar. A interface deve informar indisponibilidade/inicialização e oferecer nova tentativa. Não repetir automaticamente mutações.
- Nenhum dado necessário ao fluxo pode depender de SQLite ou arquivo local persistente no Render.
- A importação MVP não conserva o CSV original: processa bytes limitados e persiste metadados, hash e linhas normalizadas no PostgreSQL.
- CSVs de exportação são gerados sob demanda. Armazenamento externo de anexos fica para depois.
- Sem worker, scheduler ou Redis obrigatório no deploy gratuito. Endpoints legados que dependem deles ou de storage local precisam ficar indisponíveis nesse perfil, com resposta explícita; não aceitar jobs que nunca serão executados.
- A gratuidade depende das cotas e regras dos provedores, sem garantia de disponibilidade contínua. Não provisionar serviços pagos.
- Referências verificadas em 2026-11-08: https://render.com/docs/free e https://neon.com/pricing.

## 3. Usuários e permissões

Reaproveitar admin, manager e employee. Não redefinir permissões de todos os módulos legados.

| Operação do MVP | admin | manager | employee |
| --- | --- | --- | --- |
| Ler catálogo/estoque | Sim | Sim | Sim |
| Ler pedidos/recebíveis | Sim | Sim | Não |
| Importar, revisar e gerar rascunhos | Sim | Sim | Não |
| Confirmar/cancelar venda | Sim | Sim | Não |
| Ajustar estoque inicial | Sim | Sim | Não |
| Ver auditoria | Sim | Sim | Não |
| Gerenciar papéis elevados | Sim | Não | Não |

Alteração necessária: conceder sales:read, sales:write e sales:confirm a manager; preservar controle de desconto separado. A importação exige integrations:import; geração de rascunhos exige também sales:write. Todas as rotas autenticadas usam o company_id do usuário, nunca um tenant fornecido pelo frontend. IDs de outra empresa retornam 404 e falta de permissão retorna 403.

## 4. Jornada e telas

1. Entrar ou criar empresa de demonstração.
2. Preparar catálogo, cliente opcional, depósito e saldo inicial.
3. Enviar CSV, visualizar resumo e erros por pedido/linha.
4. Excluir da seleção pedidos inválidos; corrigir o arquivo e reenviar se necessário. Edição inline não entra na primeira versão.
5. Selecionar pedidos válidos e gerar rascunhos, sem alterar estoque ou financeiro.
6. Abrir um rascunho e confirmar com depósito e prazo.
7. Conferir movimentos de estoque, recebível e auditoria.
8. Cancelar venda não recebida e verificar reversão.
9. Exportar resultado da revisão ou pedidos visíveis à empresa.

Telas: acesso; resumo operacional; catálogo/preparação; importações/lista/detalhe; pedidos/lista/detalhe; estoque; recebíveis somente leitura; auditoria.

Cada tela tem estados loading, empty, error e success, acesso por teclado e rótulos de formulário. Cópia da interface em pt-BR. Erros da API têm códigos estáveis e a UI traduz a mensagem para linguagem clara.

## 5. Contrato da importação de pedidos

### Arquivo

- CSV UTF-8 com BOM opcional, separador vírgula e cabeçalho exato: external_order_id,sku,quantity.
- Limite: 1 MiB de conteúdo, 500 linhas de dados, 100 pedidos por arquivo e 200 itens por pedido.
- Valores monetários vêm do catálogo do tenant e não são aceitos no arquivo no primeiro MVP.
- quantity é inteiro entre 1 e 1.000.000; external_order_id tem de 1 a 80 caracteres após trim; sku tem de 1 a 80.
- Não incluir cliente, desconto ou dados pessoais no CSV inicial; customer_id permanece opcional.
- external_order_id e SKU são case-sensitive depois de trim, sem transformação silenciosa. Pedido repetido no mesmo arquivo agrupa linhas; SKU repetido dentro do mesmo pedido invalida esse pedido.
- Cabeçalhos ausentes, duplicados, extras, UTF-8 inválido, colunas excedentes, arquivo vazio e limite de linhas/pedidos invalidam o arquivo inteiro: nenhuma gravação.
- Um SKU desconhecido ou quantidade inválida invalida todo o pedido correspondente, mas outros pedidos do arquivo podem seguir.
- Linhas não associáveis a external_order_id são reportadas separadamente e não geram pedidos.
- Nenhum dado é truncado silenciosamente.

Exemplo:

~~~csv
external_order_id,sku,quantity
DEMO-001,PROD-A,2
DEMO-001,PROD-B,1
DEMO-002,PROD-INEXISTENTE,1
~~~

O primeiro pedido pode seguir para rascunho; o segundo recebe sku_not_found. Estoque insuficiente é aviso na revisão e bloqueio na confirmação, quando o saldo é revalidado com transação.

### Estado durável

Novas tabelas dedicadas OrderImportBatch, OrderImportEntry e OrderImportSource, separadas de ImportRun/FileAsset legados que exigem arquivo armazenado.

- Batch: UUID, company_id, actor_id, filename sanitizado, sha256, status, created_at.
- Entry: UUID, batch_id, company_id, external_order_id, source_lines, normalized_items, errors, status e sales_order_id opcional. Valores monetários normalizados usam strings decimais.
- Source: company_id + external_order_id únicos e sales_order_id único. Liga identidade externa ao pedido e evita duplicação entre arquivos, tentativas e reinícios.
- Estados de batch: reviewed, committed, partially_committed. Estados de entry: valid, invalid, committed, duplicate. reviewed não significa que o estoque foi reservado.
- Inserir conteúdo e resultados em uma transação só depois de validações estruturais. Nada depende da memória entre requisições.
- Repetir o mesmo arquivo por hash no mesmo tenant devolve o batch existente; conteúdo igual em empresas diferentes não compartilha registros.
- Preço e disponibilidade são conferidos novamente ao gerar rascunhos. Se o preço do catálogo mudou desde a revisão, devolver 409 catalog_changed e exigir revalidação explícita; não alterar o valor aceito silenciosamente. A revalidação atualiza apenas entries não committed, preserva erros e decisões anteriores no registro de auditoria e não cria pedidos.
- Seleção contém até 100 entry_ids do mesmo batch e tenant. Seleção com item inválido, duplicado já existente em outro batch ou de outro tenant falha sem escrita parcial.
- Reenvio da mesma seleção já committed devolve os mesmos IDs de pedidos; mistura de entries novas válidas e já committed reaproveita as existentes e grava somente as novas.
- Bloquear batch durante commit e usar constraints únicas para concorrência. Falha em qualquer criação reverte todas as novas criações da requisição.

### API proposta

Prefixo /api/v1. Novas rotas, ainda não existentes:

| Método/rota | Resultado |
| --- | --- |
| POST /order-imports | multipart file; 201 novo batch, 200 repetição idêntica |
| GET /order-imports | Lista paginada do tenant |
| GET /order-imports/{batch_id} | Resumo, entries, erros com código e linha |
| POST /order-imports/{batch_id}/revalidate | 200 com revisão atualizada das entries não committed |
| POST /order-imports/{batch_id}/commit | JSON {entry_ids: UUID[]}; 200 com {batch_id, orders: [{entry_id, order_id, reused}]} |
| GET /order-imports/{batch_id}/errors.csv | Exportação autenticada com escape de fórmulas |

Erros: 413 tamanho excedido; 422 formato/limites/seleção inválida; 409 conflito de identidade externa ou catálogo alterado; 401/403/404 conforme acesso. Descrição de erro não expõe dados de outra empresa. Lista paginada usa os helpers e cabeçalhos existentes; expor os cabeçalhos necessários no CORS.

## 6. Contratos de vendas preservados

Reutilizar POST /sales/orders, GET /sales/orders, GET /sales/orders/{id} e PATCH /sales/orders/{id}/status.

- Estados permanecem draft, confirmed e cancelled. Não criar estado de revisão no SalesOrder: revisão pertence ao batch.
- Criar rascunho não altera estoque/recebível.
- Confirmação exige depósito do tenant, saldo suficiente para todos os itens e total positivo.
- Bloquear o pedido antes de avaliar a transição; saldo atualizado atomicamente, fulfillment e recebível únicos por pedido.
- Uma única transação inclui status, todos os movimentos, recebível e auditoria. Helpers chamados não fazem commits intermediários.
- Confirmar/cancelar duas vezes nunca duplica efeito. Contrato de status existente pode devolver 409 na segunda chamada; UI recarrega o estado antes de nova ação.
- Falha ao criar recebível deve reverter a baixa de estoque.
- Cancelar pedido confirmado sem recebimentos devolve estoque uma vez e cancela recebível.
- Pedido com pagamento parcial/total não pode ser cancelado: 409 sem qualquer reversão.
- Data de vencimento usa data atual UTC + payment_terms_days, igual no teste e na API; horário de exibição pt-BR não muda o instante armazenado.
- Pagamentos manuais e estornos financeiros complexos não são parte da jornada pública inicial; preservar código e regressões existentes.

## 7. Segurança, demonstração e operação

- Manter JWT/RBAC; testar token expirado, usuário inativo e acesso cruzado. Frontend mantém access token em memória no primeiro MVP; não persistir token no localStorage. Recarregar pode exigir novo login até existir estratégia de refresh revisada.
- Perfil público de demonstração deve limitar endpoints aos domínios do MVP; desabilitar IA, automações, imports legados de arquivos e operações cloud que não tenham infraestrutura.
- Dados exclusivamente fictícios. Seed idempotente para duas empresas, dois usuários de papéis distintos por empresa, três produtos, um depósito por empresa e saldos conhecidos.
- Não publicar senhas do ambiente pessoal. Credenciais demo são dedicadas, com privilégios limitados e dados descartáveis. Conta de teste de isolamento não precisa ser divulgada.
- Limites por conta: até 20 batches/dia e 100 batches retidos por empresa, checados em banco; ao atingir, responder 429 ou 409 com instrução. Limpeza manual autenticada via comando do administrador, nunca endpoint público de reset global.
- Limitar tentativas de login antes de publicar cadastro aberto. Se ainda não houver controle de abuso, deploy inicial usa contas demo pré-criadas e registro público desabilitado.
- Arquivos exportados neutralizam células iniciadas por =, +, -, @, tab ou retorno de carro; mensagens não incluem segredos.
- Documentar exportação/backup e restauração de um banco fictício. Não depender de backups gratuitos presumidos.
- Health público sem informações sensíveis; readiness consulta DB com timeout e falha explícita.
- Métricas são medidas e acompanhadas de procedimento, sem prometer ganhos empresariais não observados.

## 8. Entregas e aceite

| Etapa | Entrega verificável | Aceite |
| --- | --- | --- |
| M0 | Baseline PostgreSQL | Migração do zero, suíte executada com DB-alvo, evidências registradas |
| M1 | Fluxo transacional endurecido | Concorrência, rollback, estoque e recebível únicos comprovados |
| M2 | Importação/revisão | Contratos de arquivo, tenant, duplicidade e seleção aprovados |
| M3 | Frontend TypeScript | Jornada completa com estados, teclado e sessão coerentes |
| M4 | CI e demo local | Instalação reproduzível; E2E com duas empresas e arquivo com erro |
| M5 | Render + Neon | Migrações, configuração, cold start, persistência e smoke test comprovados |
| M6 | Release de portfólio | README, vídeo, screenshots, CSVs fictícios, ADRs e relatório de validação |

Não marcar etapas concluídas apenas por documentação ou presença de arquivos.

## 9. Fora deste MVP

IA/LLMs, treinamento de modelos, automação de portal externo, XLSX na importação de pedidos, CRM além do cliente básico, compras/logística avançadas, recebimento financeiro, webhooks, workers contínuos na hospedagem gratuita, AWS, aplicativo desktop/mobile e sincronização offline.

Código desses módulos é preservado, com testes de regressão e funcionalidades fora do menu do MVP. A visão de longo prazo permanece válida; o corte reduz dependências para uma entrega demonstrável.
