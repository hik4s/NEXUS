# NEXUS — B4 Contracts & Platform

## Concluído

### B-025 — Paginação
- Paginação com `page` e `page_size` em endpoints centrais.
- Metadados via headers:
  - `X-Page`
  - `X-Page-Size`
  - `X-Total-Count`
  - `X-Total-Pages`

### B-026 — Filtros e ordenação
- Whitelist de campos.
- Validação de direção `asc|desc`.
- Endpoints centrais já preparados para filtros existentes + ordenação segura.

### B-027 — Idempotência
- Header `Idempotency-Key`.
- Hash da requisição.
- Replay da resposta original.
- Reuso com payload diferente bloqueado.
- Estado `processing` evita duplicidade concorrente.
- Aplicado inicialmente à criação de Sales Orders; outras operações críticas podem adotar o mesmo serviço.

### B-028 — Webhooks
- Cadastro de endpoints.
- Eventos inscritos.
- Segredo criptografado em repouso.
- Assinatura HMAC SHA-256.
- Registro de deliveries.
- Retry contabilizado.
- Dead-letter após atingir máximo de tentativas.
- Envio HTTP fica desacoplado para B5/worker.

### B-029 — API Keys
- Geração de segredo.
- Hash do segredo em banco.
- Scopes.
- Revogação.
- Validação por `X-API-Key`.
- Segredo bruto mostrado somente na criação.

## Marco

**B4 — Contratos e Plataforma: concluído.**

A camada de plataforma agora fornece contratos reutilizáveis para frontend, integrações e futura Intelligence API sem colocar lógica de integração dentro dos domínios de negócio.
