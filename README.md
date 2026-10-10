# NEXUS — AI-Powered Business Operating System

Big App de portfólio para gestão operacional inteligente de PMEs.

## Status

**v0.18.0 — B9 Cloud baseline**

O Backend completou o roadmap técnico até B9 em nível de código/infraestrutura. A única pendência estrutural importante continua sendo validar PostgreSQL/Redis/AWS em runtime no ambiente real.

## Backend

- FastAPI + REST
- SQLAlchemy 2 + Alembic
- Tenant isolation, JWT, refresh tokens, RBAC e auditoria
- CRM, Sales, Inventory, Procurement, Finance, Logistics, Workflow
- Async jobs, retry/backoff/dead-letter, scheduler e notifications
- Integrações, Playwright worker, importadores CSV/XLSX e storage local/S3
- Intelligence API com tools controladas, gateway provider-agnostic, chat e action approval
- Segurança, observabilidade, métricas, concorrência e CI
- Docker/Compose production baseline
- Terraform para AWS Fargate/RDS/S3/IAM/CloudWatch

## Cloud architecture

```text
Internet
   ↓
Application Load Balancer
   ↓
ECS Fargate
├── API
├── Worker
└── Scheduler
   │
   ├── RDS PostgreSQL (private)
   ├── S3 (private)
   └── CloudWatch Logs
```

Fargate was selected to run containers without managing servers; RDS is used as the production PostgreSQL layer; S3 remains private and files are exposed through time-limited presigned URLs when needed. AWS documents these patterns for Fargate, RDS, S3 and CloudWatch. 

## Run locally without Docker

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example ..\.env
uvicorn app.main:app --reload
```

## Test

```powershell
cd backend
python -m pytest -q
```

## Cloud files

- `infra/terraform/` — AWS infrastructure source of truth
- `docs/B9-CLOUD.md` — architecture and deployment notes
- `scripts/cloud-check.ps1` — local prerequisite check
- `docker-compose.prod.yml` — local production-like API/worker/scheduler stack
