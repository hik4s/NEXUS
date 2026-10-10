# NEXUS — B5 Async Processing

## Implementado

- Redis dispatch adapter.
- Durable `BackgroundJob` persistence.
- Worker runner com retry/backoff/dead-letter.
- Scheduler baseado em `JobSchedule`.
- Notifications internas.
- Fallback de worker por polling do banco quando Redis não estiver disponível.
- API para inspeção/execução de jobs e notificações.

## Princípio

Redis não é a fonte de verdade. O banco registra o estado do job; Redis apenas acelera a entrega ao worker.

## Jobs demonstráveis

- `noop`
- `notification.create`

Novos handlers de domínio serão adicionados conforme os módulos precisarem de processamento assíncrono.
