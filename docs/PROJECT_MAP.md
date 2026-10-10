# NEXUS — Project Map

## Backend domains

```text
Identity / RBAC / Audit
        ↓
CRM → Sales → Inventory ← Procurement
                 ↓              ↓
                 └──────────── Finance
                 ↓
              Logistics
                 ↓
              Workflow
                 ↓
        Intelligence / AI
```

## Official backend status

```text
B0 Foundation                 ✅
B1 Persistence                🟡 runtime PostgreSQL pending
B2 Identity/Security           ✅
B3 Core Domains                ✅
B4 Contracts/Platform          ✅
B5 Async Processing             ✅
B6 Automation/Integrations      ✅
B7 Intelligence API             ✅
B8 Quality/Security/Observability ✅
B9 Cloud                        ✅* 
```

`*` B9 is artifact-complete and locally validated as configuration/code; runtime AWS validation remains pending actual cloud access.

NEXUS remains a modular monolith. Cloud deployment runs the API, worker and scheduler as separate ECS Fargate services sharing the same backend image and domain modules.
