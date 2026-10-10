# NEXUS — FASE B5: Processamento Assíncrono

## B-030 — Redis

- Adapter `RedisJobQueue` usando `redis-py`.
- Fallback local para desenvolvimento/testes sem Redis.
- O banco continua sendo a fonte de verdade dos jobs.

## B-031 — Worker / Jobs

- `BackgroundJob` persistente.
- Handlers registrados por `kind`.
- Retry com backoff exponencial curto.
- Dead-letter após `max_attempts`.
- Worker por polling do banco quando Redis não está disponível.
- Worker contínuo em `python -m app.workers.worker_loop`.

## B-032 — Scheduler

- `JobSchedule` persistente.
- Intervalo em segundos.
- `next_run_at`.
- Idempotência por ocorrência.
- Scheduler contínuo em `python -m app.workers.scheduler_loop`.

## B-033 — Notifications

- Notificações persistentes por usuário.
- Severidade e tipo.
- Estado lido/não lido.
- Handler assíncrono `notification.create`.

## Limite atual

Redis real **não foi validado neste ambiente** porque o ambiente de desenvolvimento não possui o serviço Docker/Redis disponível. A integração está implementada e declarada em `requirements.txt` e `docker-compose.yml`.
