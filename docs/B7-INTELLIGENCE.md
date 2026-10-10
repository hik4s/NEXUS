# NEXUS — B7 Intelligence API

## B-038 — Data/Metrics Services

Serviços agregados para vendas, estoque, caixa, inadimplência e preços de fornecedores. Eles recebem `company_id` do usuário autenticado e nunca recebem uma conexão arbitrária do modelo.

## B-039 — Tool Layer

Ferramentas registradas por nome, descrição e schema de entrada. Execução é feita pelo backend, com tenant isolation. Ferramentas de ação criam apenas propostas pendentes; não executam ações diretamente.

## B-040 — AI Gateway

Provider abstraction com:
- timeout;
- retries;
- fallback para modo `mock`;
- limite de tool calls;
- limite de output tokens;
- metadados de provider/model/usage/latência.

Provider padrão: `mock`. Provider externo: `openai-compatible`.

## B-041 — Chat API

Endpoints:
- `POST /api/v1/intelligence/conversations`
- `GET /api/v1/intelligence/conversations`
- `GET /api/v1/intelligence/conversations/{id}`
- `POST /api/v1/intelligence/conversations/{id}/messages`

As mensagens e tool calls são persistidos.

## B-042 — Action Approval API

Endpoints:
- `GET /api/v1/intelligence/action-proposals`
- `POST /api/v1/intelligence/action-proposals/{id}/approve`
- `POST /api/v1/intelligence/action-proposals/{id}/reject`
- `POST /api/v1/intelligence/action-proposals/{id}/execute`

A primeira ação suportada é `workflow.create_task`, executada somente após aprovação e com permissão de escrita em Workflow.

## Segurança

- `intelligence:read`
- `intelligence:chat`
- `intelligence:approve`

O modelo não acessa PostgreSQL diretamente. Toda informação passa por métricas e tools controladas.
