# Architecture overview

NEXUS is designed as a modular monolith first, with clear domain boundaries and an upgrade path to asynchronous workers and independent services where justified.

## Core flow

```text
React → REST API → domain services → repositories → PostgreSQL
                     │
                     ├→ Redis / workers
                     ├→ external integrations
                     └→ intelligence layer
```

The initial architecture intentionally avoids microservices. We will split components only when scale, deployment independence, or failure isolation creates a concrete reason.
