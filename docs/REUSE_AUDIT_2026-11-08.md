# NEXUS — inventário e decisões de reaproveitamento

Data: 2026-11-08. Baseline analisado: main, commit 9e64214531f491ec0dabbd20e13f694afccd901c.

## Método e limites

Inspeção da árvore pública e leitura das rotas, schemas, modelos, serviços, testes e configuração relacionados ao fluxo ativo. Esta revisão é estática: não executou backend, PostgreSQL, Redis, navegador ou serviços cloud nesta sessão. “Existente” significa código encontrado; “validado” requer execução registrada posteriormente.

Não atribuir percentual de conclusão com base em contagem de arquivos. Os testes encontrados são evidências de cenários previstos, não resultados de execução atual.

## Matriz de decisão

| Componente existente | Evidência | Decisão | Trabalho necessário |
| --- | --- | --- | --- |
| FastAPI e monólito modular | backend/app/main.py, api/v1/router.py | Manter | Perfil explícito de rotas do MVP e health/readiness |
| JWT e usuário ativo | identity/dependencies.py, services/auth_service.py | Manter | Validar expiração, inatividade, segredo de produção e sessão da UI |
| Empresas e RBAC | rbac/constants.py, tests/test_rbac.py | Manter/adaptar | manager não tem sales:read/write/confirm no baseline; conceder conforme spec e testar limites |
| Catálogo | models/product.py, services/product_service.py | Manter | Tela tipada, validação, paginação e seed |
| Clientes básicos | models/customer.py, services/crm_service.py | Manter como suporte | Cliente opcional; CRM amplo fora do MVP |
| Pedidos e itens | models/order.py, schemas/sales.py | Manter | Identidade externa em tabela separada para importações |
| Serviço de vendas | services/sales_service.py | Manter/endurecer | Lock no pedido e atomicidade de efeitos e idempotência |
| Estoque e depósito | services/inventory_service.py | Manter/endurecer | Verificar locks/constraints no PostgreSQL e concorrência |
| Recebíveis | services/finance_service.py | Manter | Regressão confirmação/cancelamento; preservar bloqueio quando há pagamento |
| Auditoria | audit/service.py | Manter | Verificar mesma transação da operação e visualização paginada |
| Paginação/idempotência | platform/service.py, routes/sales.py | Reutilizar com revisão | Evitar janela entre commit do negócio e registro da resposta |
| Importação CSV/XLSX | services/import_service.py, b6_service.py | Aproveitar padrões | Importa CLIENTES, não pedidos; não reutilizar como se o novo fluxo já existisse |
| FileAsset/ImportRun | models/integrations.py | Preservar para legado | Obrigam arquivo armazenado; novas tabelas de revisão de pedidos não terão essa dependência |
| Jobs/Redis/worker | services/job_service.py, workers/runner.py | Preservar fora do caminho crítico | Claim/recovery precisa de revisão antes de múltiplos workers |
| React/Vite | frontend/src/App.jsx | Aproveitar UI e conexão com API | Migrar JS → TS e separar autenticação, páginas, componentes e cliente HTTP |
| CSS existente | frontend/src/styles.css | Manter direção visual | Revisar responsividade, contraste, teclado e foco |
| SQLAlchemy/Alembic | models, alembic/versions | Manter | Validar cadeia inteira no PostgreSQL; não editar migrações históricas aplicadas |
| Docker Compose | docker-compose.yml | Adaptar | Redis opcional; corrigir alinhamento de nome/usuário/URL do banco; validar clone novo |
| Backend CI | .github/workflows/backend.yml | Manter/ampliar | Serviço PostgreSQL e integração; frontend typecheck/build/tests/E2E |
| Terraform AWS | infra/terraform | Preservar como evolução | Não provisionar; Render/Neon é o alvo ativo do MVP |
| IA, automação, logística, compras, workflows avançados | módulos e testes correspondentes | Preservar/adiar | Fora do menu e do deploy inicial se exigirem dependências ausentes |

## Regras já implementadas que justificam reaproveitamento

- SalesOrder tem draft, confirmed e cancelled; criar pedido calcula total com Decimal e valida permissão para desconto/preço.
- update_order_status chama fulfill_sales_order e ensure_receivable_for_sales_order antes do commit.
- fulfillment valida o saldo de todos os produtos; _apply_movement executa atualização condicional do saldo.
- Cancelamento chama cancel_receivable_for_sales_order e reverse_sales_order_fulfillment.
- Financeiro bloqueia cancelamento se paid_amount for maior que zero.
- require_permission resolve identidade e permissão no backend.
- Rotas consultadas aplicam company_id do ator; testes incluem tenant isolation.
- Criação manual de pedido já usa Idempotency-Key na rota.

Esses pontos evitam reescrever o núcleo. A prova do conjunto ainda exige testes no PostgreSQL e testes de concorrência.

## Lacunas observadas

### Prioridade bloqueadora

1. Não há importação/revisão de PEDIDOS: só de clientes.
2. Frontend é JavaScript concentrado em App.jsx, cobrindo acesso e produtos.
3. Não há render.yaml no baseline nem configuração Neon comprovada.
4. STORAGE_BACKEND=local e SQLite padrão não podem ser usados para persistência do deploy gratuito.
5. CI atual não provisiona PostgreSQL; testes existentes não bastam para atestar locks reais.
6. Endpoints de jobs/imports legados ficam expostos mesmo sem worker/storage pronto; planejar perfil de capacidades.
7. Compose substitui DATABASE_URL com usuário/nome fixos embora o serviço de banco permita variáveis diferentes.

### Prioridade de consistência

- A transição de status lê pedido sem lock explícito. Provar comportamento de confirmações/cancelamentos concorrentes.
- Há commits em serviços de negócio e em auxiliares de idempotência. Revisar a unidade transacional antes de compor novas operações.
- O worker aceita um job já running no claim; não há garantia demonstrada de execução exclusiva nem recuperação por lease.
- O importador de clientes materializa as linhas antes do limite de validação. Não copiar esse padrão sem limites para o parser de pedidos.
- Sessão da UI atual persiste token no localStorage; rever antes de publicar demo.
- frontend/package.json usa latest e não há lockfile frontend no baseline.

### Organização e apresentação

- Preservar histórico de migrações e testes; imports repetidos ou pastas placeholder são ajustes secundários.
- A interface tem textos de etapas anteriores; atualizar junto da entrega de cada tela.
- Criar fixtures fictícias, roteiro E2E, screenshots, vídeo e relatório de validação.
- Não apresentar infraestrutura AWS ou IA como operação homologada apenas pela presença de código.

## Evidências de testes encontradas

- test_sales.py: totais, status, desconto/permissão e tenant.
- test_inventory.py: movimentos, transferência, confirmação/cancelamento, saldo insuficiente e tenant.
- test_finance.py: recebível de venda, pagamentos parciais, permissão e tenant.
- test_platform.py: replay de idempotência, payload conflitante e paginação.
- test_b6_integrations.py: dry-run/importação de CLIENTES, arquivos, isolamento e encaminhamento ao worker.

## Decisão de implementação

Evoluir o baseline sem reinicializar o projeto. Concluir uma jornada usando os serviços existentes, novas tabelas de revisão de pedidos e frontend tipado. Preservar os módulos extras como evolução; não removê-los nem executar AWS para cumprir este MVP.

Escopo normativo: [MVP de portfólio](MVP_PORTFOLIO.md).
