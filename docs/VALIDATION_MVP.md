# M0 — validação do baseline

Plano: `docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md`, Task 1.
Data: 2026-11-09. Base: `5c0cdaa`. Branch: `codex/m0-postgres`.

## Ambiente e resultados

- Checkout limpo separado do trabalho local, criado pelo Codex.
- Python 3.12.10, PostgreSQL 17.11 (imagem postgres:17-alpine), psycopg 3.3.6,
  SQLAlchemy 2.1.4, Alembic 1.20.0 e pytest 8.4.2.
- PostgreSQL descartável exclusivo, container `nexus-m0-postgres`, porta local 55432.
  O PostgreSQL já existente na porta 5432 não foi utilizado.
- Antes das migrações, `test_postgres_migrations_bootstrap` falhou corretamente:
  banco vazio sem tabelas nem alembic_version.
- `alembic upgrade head`: cadeia completa aplicada até `b689a44a2ac3`.
- `alembic check`: nenhuma operação nova detectada.
- `python -m pytest -q` com PostgreSQL: **68 passed**, 2 avisos de depreciação
  (Starlette/httpx e path_separator do Alembic).
- Teste de persistência: registro preservado após fechar e abrir o lifespan da API
  com TestClient. Não cobre reinício real de processo/container ou backup/restore.
- `scripts/db-check.ps1`: upgrade, check e current executados com sucesso.
- SQLite vazio: upgrade e check passaram; suíte com **66 passed, 2 skipped**
  (os dois testes exclusivos de PostgreSQL), 1 aviso Starlette/httpx.
- `docker compose config --quiet`: passou sem arquivo .env obrigatório.
- Compose padrão: postgres/backend/frontend; perfil async adiciona redis.
- Configuração com POSTGRES_USER e POSTGRES_DB personalizados: URL da API coerente.

## Reprodução

Use um PostgreSQL descartável vazio. Na raiz, em PowerShell:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/DATABASE'
$env:REDIS_ENABLED = 'false'
./scripts/db-check.ps1
cd backend
./.venv/Scripts/python.exe -m pytest -q
```

O script aceita `-PythonExecutable` para selecionar outro ambiente Python.
Requer Docker Compose 2.24+ para `.env` opcional. Para usar Redis, definir
REDIS_ENABLED=true e iniciar com `docker compose --profile async up`.

## Decisões e limites

- M0 valida o código publicado no main; as alterações locais de frontend/backend
  permanecem no checkout original para reconciliação posterior.
- O PR #1 não foi integrado; a correção da ordem de migração no CI foi aplicada
  aqui por ser necessária a M0. As alterações de jobs desse PR continuam pendentes.
- CI foi configurado para SQLite e PostgreSQL; execução no GitHub depende de push.
- Instalação do zero das dependências e stack completa frontend/API pelo Compose
  não foram executadas. O ambiente Python local existente foi reutilizado.
- M1 continua pendente: concorrência, atomicidade e idempotência de negócio.
- Revisão estática independente de M0: nenhum bloqueador encontrado; comentário
  de ativação do Redis corrigido e limite do teste de lifespan registrado acima.
