# NEXUS — Backend Roadmap

**Versão:** 1.0  
**Trilha:** Backend  
**Objetivo final:** construir o núcleo transacional e operacional do NEXUS com FastAPI, PostgreSQL, SQLAlchemy, autenticação, regras de negócio, processamento assíncrono, automações, observabilidade e contratos estáveis para o frontend e a IA.

---

## 1. Princípios da trilha

1. O backend é a autoridade das regras de negócio e da segurança.
2. Os módulos serão separados por domínio, não por um único arquivo gigante.
3. Toda funcionalidade importante terá validação, persistência, testes e tratamento de erro.
4. PostgreSQL será o banco principal da arquitetura final; SQLite serve apenas como ambiente temporário/local enquanto a infraestrutura não estiver disponível.
5. Integrações externas não devem bloquear a API quando puderem ser assíncronas.
6. O backend fornecerá ferramentas/serviços seguros para a camada de IA; o modelo nunca terá acesso direto ao banco.

## 2. Arquitetura-alvo

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── domains/
│   ├── intelligence/
│   ├── automation/
│   ├── workers/
│   ├── integrations/
│   └── main.py
├── alembic/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
├── Dockerfile
└── requirements.txt
```

`domains/` deve concentrar regras específicas de cada contexto. `services/` abriga serviços compartilhados quando uma regra realmente atravessa domínios.

---

# 3. Microtarefas

## FASE B0 — Fundação técnica

### B-001 — Configuração e ambiente
- Settings via `.env`.
- Dev/test/prod.
- Configuração de logs.

### B-002 — App factory/lifecycle
- Startup/shutdown.
- Registro de routers.
- Health check.

### B-003 — Tratamento de exceções
- Erros de domínio.
- 400/401/403/404/409/422/500.
- Formato consistente de erro.

### B-004 — Logging estruturado
- Request ID.
- Usuário.
- Empresa.
- Tempo de resposta.
- Erro e stack trace somente em logs apropriados.

### B-005 — Test harness
- Pytest.
- Fixtures.
- Banco de teste.
- Cliente HTTP.

**Marco B0:** API organizada, previsível e testável.

---

## FASE B1 — Persistência

### B-006 — PostgreSQL
- Subir PostgreSQL quando o ambiente Docker estiver disponível.
- Configurar conexão.

### B-007 — SQLAlchemy 2
- Engine.
- Session.
- Declarative models.

### B-008 — Alembic
- Migração inicial.
- Estratégia de revisão.
- Rollback.

### B-009 — Convenções de banco
- IDs.
- Timestamps.
- Unique constraints.
- Foreign keys.
- Índices.
- Soft delete somente onde fizer sentido.

### B-010 — Transações
- Commit.
- Rollback.
- Unidade transacional clara por operação.

**Marco B1:** persistência robusta e migrável.

---

## FASE B2 — Identity e segurança

### B-011 — Company
- CRUD interno.
- Isolamento por tenant.

### B-012 — User
- Criação.
- Atualização.
- Desativação.

### B-013 — Password security
- Hash seguro.
- Política mínima.
- Nunca armazenar senha em texto puro.

### B-014 — JWT
- Access token.
- Refresh token.
- Expiração.
- Rotação quando necessário.

### B-015 — RBAC
- Roles.
- Permissions.
- Verificação central.

### B-016 — Auditoria
- Quem.
- O quê.
- Quando.
- Empresa.
- Recurso afetado.

### B-017 — Rate limiting inicial
- Login.
- Endpoints sensíveis.
- Base pronta para Redis.

**Marco B2:** identidade, autorização e auditoria em produção possível.

---

## FASE B3 — Domínios core

Implementar em ciclos independentes.

### B-018 — CRM
- Customer.
- Lead.
- Interaction.
- Segment.

### B-019 — Catalog/Sales
- Category.
- Product.
- Price.
- Order.
- OrderItem.
- Discount.
- Commission.

### B-020 — Inventory
- Warehouse.
- Stock.
- StockMovement.
- Transfer.
- Minimum stock.

### B-021 — Procurement
- Supplier.
- PurchaseOrder.
- PurchaseItem.
- SupplierPriceHistory.

### B-022 — Finance
- Account.
- Payable.
- Receivable.
- Transaction.
- Cash projection.

### B-023 — Logistics
- Delivery.
- Driver.
- Vehicle.
- Route.
- Tracking event.

### B-024 — Workflow
- Task.
- Approval.
- SLA.
- Escalation.
- Comment.
- Attachment metadata.

**Regra:** um domínio só passa para “estável” quando possui schema, model, serviço, endpoint, autorização e testes.

---

## FASE B4 — Contratos e plataforma

### B-025 — Paginação
- Offset ou cursor conforme o caso.
- Metadados.

### B-026 — Filtros e ordenação
- Whitelist de campos.
- Validação.

### B-027 — Idempotência
- Operações críticas.
- Chaves de idempotência.
- Proteção contra duplicidade.

### B-028 — Webhooks
- Registro.
- Assinatura/verificação.
- Retries.
- Dead-letter quando necessário.

### B-029 — API keys
- Criação.
- Revogação.
- Escopos.
- Hash de segredo quando aplicável.

---

## FASE B5 — Processamento assíncrono

### B-030 — Redis
- Cache onde houver benefício.
- Locks quando necessário.
- Rate limiting.

### B-031 — Worker
- Fila.
- Jobs.
- Retry.
- Backoff.
- Estado do job.

### B-032 — Agendador
- Jobs recorrentes.
- Idempotência.
- Histórico.

### B-033 — Notificações
- Email.
- Notificação interna.
- Templates.

**Marco B5:** trabalhos demorados deixam de bloquear requests.

---

## FASE B6 — Automação e integrações

### B-034 — Sistema de integrações
- Credenciais.
- Conectores.
- Logs.
- Health status.

### B-035 — Playwright worker
- Executar fora do processo HTTP.
- Capturar screenshots/logs quando falhar.
- Armazenar resultado.

### B-036 — Importadores
- CSV.
- XLSX quando necessário.
- Validação.
- Dry-run.
- Relatório de erros.

### B-037 — S3/file storage
- Upload.
- Download autorizado.
- URLs temporárias.
- Metadados.

---

## FASE B7 — Intelligence API

### B-038 — Data/metrics services
Criar serviços estáveis para a IA consultar:
- vendas;
- margem;
- estoque;
- caixa;
- inadimplência;
- fornecedores;
- logística.

### B-039 — Tool layer
Cada ferramenta de IA terá:
- nome;
- schema de entrada;
- autorização;
- limite de dados;
- execução auditada.

### B-040 — AI gateway
- Provider abstraction.
- Timeout.
- Retry.
- Fallback.
- Controle de custo.

### B-041 — Chat API
- Conversas.
- Mensagens.
- Tool calls.
- Resultado.
- Auditoria.

### B-042 — Action approval API
- Proposta.
- Aprovação.
- Execução.
- Resultado.
- Rollback quando possível.

---

## FASE B8 — Qualidade e segurança avançadas

### B-043 — Testes de integração por domínio

### B-044 — Testes de concorrência para operações críticas

### B-045 — Segurança de arquivos, payloads e uploads

### B-046 — CORS e headers de segurança

### B-047 — Gestão de segredos

### B-048 — Observabilidade
- Métricas.
- Logs.
- Traces.
- Health/readiness.

### B-049 — Performance
- Índices.
- N+1.
- Query profiling.
- Cache seletivo.

### B-050 — CI/CD
- Lint.
- Testes.
- Build.
- Migrations.
- Deploy controlado.

---

## FASE B9 — Cloud final

### B-051 — Dockerização

### B-052 — AWS compute

### B-053 — AWS RDS/PostgreSQL

### B-054 — AWS S3

### B-055 — IAM

### B-056 — CloudWatch

### B-057 — Backup e recuperação

### B-058 — Infraestrutura como código
- Terraform quando a complexidade justificar.

---

# 4. Contratos que o Backend precisa fornecer

O backend deve oferecer à camada de frontend:
- OpenAPI atualizada;
- códigos HTTP consistentes;
- paginação;
- autenticação;
- permissões;
- erros estruturados.

Para a IA:
- dados agregados e autorizados;
- ferramentas tipadas;
- contexto mínimo necessário;
- auditoria de consultas e ações;
- limites de custo e acesso.

# 5. Critério de conclusão do Backend

O backend estará “pronto para a versão final” quando os domínios principais estiverem isolados, testados e auditáveis; processos assíncronos estiverem desacoplados do request; IA e automações acessarem somente interfaces controladas; e o sistema puder ser implantado de forma reproduzível.
