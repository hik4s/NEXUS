# NEXUS — B8 Quality & Security

## Implemented
- Integration and regression suite remains green.
- Transaction/lock hardening for stock balances with deterministic lock ordering.
- Maximum request-body enforcement.
- XLSX payload validation and decompression guard.
- Configurable CORS and trusted hosts.
- Security response headers.
- Request IDs and structured JSON request logs.
- In-memory metrics endpoint compatible with Prometheus text format.
- Liveness/readiness checks for database and optional Redis.
- Production secret validation; development defaults remain allowed only for local use.
- CI workflow for backend checks.
- Performance baseline via request-duration metrics and indexed domain models.

## Explicit runtime limitations
- PostgreSQL, Redis, S3 and external LLM runtime tests remain environment-dependent until those services are available.
- Distributed tracing is represented by request/correlation IDs and structured logs; an OpenTelemetry exporter can be added in the cloud phase without changing domain code.
