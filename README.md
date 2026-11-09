# NEXUS

**Backend modular para integrar operações de pequenas e médias empresas.**

O NEXUS explora a integração entre clientes, vendas, estoque, compras e finanças, com permissões por empresa, auditoria e processamento assíncrono. A proposta é transformar operações isoladas em fluxos de negócio rastreáveis.

**Estado atual:** baseline de código `v0.18.0 — B9 Cloud`. O backend contém os domínios e a infraestrutura descritos abaixo; a interface React ainda cobre principalmente autenticação e catálogo. O produto completo e a operação cloud não estão homologados.

[![Backend](https://github.com/hik4s/NEXUS/actions/workflows/backend.yml/badge.svg)](https://github.com/hik4s/NEXUS/actions/workflows/backend.yml)

## MVP ativo de portfólio

A jornada do MVP é **importar pedidos CSV → revisar → gerar rascunhos → confirmar venda → atualizar estoque → gerar recebível → cancelar com reversão**. O backend dessa jornada foi validado localmente até M2; integração e CI no GitHub seguem pendentes.

A arquitetura alvo usa **React/TypeScript + FastAPI + PostgreSQL**, com frontend/API no Render e banco no Neon. A interface atual ainda é React/JavaScript; perfil público restrito, interface da jornada e deploy estão pendentes. No perfil gratuito, o recorte não exige worker permanente, Redis ou arquivos locais persistentes.

- [Escopo, arquitetura e critérios de aceite](docs/MVP_PORTFOLIO.md)
- [O que será mantido, adaptado e adiado](docs/REUSE_AUDIT_2026-11-08.md)
- [Plano de implementação M0–M6](docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md)
- [Decisão Render + Neon](docs/adr/0002-portfolio-render-neon.md)

## Stack e organização

| Camada | Tecnologias |
| --- | --- |
| API | Python, FastAPI e Pydantic |
| Persistência | SQLAlchemy 2, Alembic; SQLite local e configuração PostgreSQL |
| Identidade | JWT, refresh tokens, RBAC e contexto de empresa |
| Processamento | Workers, scheduler e integração Redis |
| Interface | React e Vite, em estágio inicial |
| Integrações | HTTPX, Playwright, CSV/XLSX e storage local/S3 |
| Infraestrutura | Docker Compose e Terraform para AWS |
| Qualidade | pytest e GitHub Actions |

O projeto segue um monólito modular. A API reúne rotas e serviços por domínio; a interface e os workers consomem essa base.

## Escopo implementado no backend

- Autenticação, empresas, usuários, papéis, permissões e auditoria.
- CRM: clientes, leads e interações.
- Catálogo, pedidos de venda, itens, descontos e transições de estado.
- Estoque, compras, financeiro, logística e workflows.
- Jobs persistidos, tentativas, backoff, dead-letter e agendamento.
- Importação de arquivos, integrações e armazenamento.
- Camada de inteligência com provedores configuráveis, ferramentas e propostas de ação com aprovação.
- Configuração de contêineres e infraestrutura AWS como código.

Essas capacidades têm implementações e testes no repositório. Sua existência não equivale a jornadas completas disponíveis na interface ou a serviços externos homologados.

## Um fluxo de negócio para avaliar

A confirmação de uma venda envolve estoque e recebível. O cancelamento de uma venda confirmada percorre as operações inversas. Os descontos e alterações de preço também passam por permissões.

| Evidência | Onde revisar |
| --- | --- |
| Regras da venda e integração entre domínios | [sales_service.py](backend/app/services/sales_service.py) |
| Cenários de vendas | [test_sales.py](backend/tests/test_sales.py) |
| Acesso por papéis e isolamento entre empresas | [test_rbac.py](backend/tests/test_rbac.py) |
| Persistência e migrações | [Alembic](backend/alembic/versions), [test_persistence.py](backend/tests/test_persistence.py) |
| Processamento assíncrono | [workers](backend/app/workers), [test_async.py](backend/tests/test_async.py) |
| Interface atualmente disponível | [App.jsx](frontend/src/App.jsx) |

Os cálculos de venda usam `Decimal`; consultas de recursos aplicam o contexto da empresa. Os testes incluem recusas por permissão e tentativa de acesso a recursos de outro tenant.

## Executar localmente

Requer Python 3.11 e Node.js/npm para a interface. Os comandos abaixo usam PowerShell e o backend local com SQLite, sem provisionar AWS.

### Backend

Na raiz:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:REDIS_ENABLED = "false"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

A configuração pode ser fornecida por variáveis de ambiente ou por `backend/.env`, carregado quando o processo parte dessa pasta. Consulte [.env.example](.env.example) antes de habilitar integrações. Use valores próprios para segredos; os padrões de desenvolvimento não são credenciais de produção.

A API fica em `http://127.0.0.1:8000`, com documentação de desenvolvimento em `/docs`. Redis está desabilitado nesse roteiro mínimo; jobs e scheduler exigem sua configuração e execução próprias.

### Frontend

Em outro terminal, a partir da raiz:

```powershell
cd frontend
npm install
npm run dev
```

Use o endereço informado pelo Vite. A API padrão é `http://localhost:8000/api/v1`; altere `VITE_API_BASE_URL` quando necessário. A demonstração visual atual permite autenticação, consulta da empresa e gerenciamento básico de produtos.

## Verificar

Na pasta `backend`, com o ambiente de desenvolvimento:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m alembic check
```

Na pasta `frontend`:

```powershell
npm run build
```

O [workflow backend](.github/workflows/backend.yml) instala dependências, compila os módulos Python, verifica Alembic e executa pytest. Testes locais não substituem validação das migrações, concorrência e recuperação no PostgreSQL/Redis reais.

## O que ainda precisa de validação

| Área | Situação |
| --- | --- |
| Backend de negócio | Código e testes presentes; validar jornadas integradas no banco-alvo |
| Frontend | Autenticação e catálogo iniciais; demais módulos ainda precisam de telas e integração |
| PostgreSQL e Redis | Configuração presente; homologação operacional pendente no checkpoint |
| IA | Provedor mock padrão e integração configurável; uso real e qualidade precisam de avaliação |
| AWS | Terraform presente; não há confirmação de implantação real no checkpoint |
| Desktop e offline | Evoluções de produto; não demonstrados pelo frontend atual |

## Próximas entregas prioritárias

1. M0 validado localmente: [baseline PostgreSQL](docs/VALIDATION_MVP.md).
2. M1 validado localmente: [atomicidade, concorrência e idempotência](docs/VALIDATION_M1.md).
3. M2 validado localmente: [revisão/importação de pedidos](docs/VALIDATION_M2.md), separada do importador de clientes existente. Próximo passo: perfil público restrito (Task 5).
4. M3–M4: migrar UI para TypeScript e entregar a jornada com testes E2E e CI.
5. M5: configurar Render + Neon e validar persistência, cold start e acesso entre empresas.
6. M6: publicar release, vídeo, screenshots e relatório de testes.

Workers, IA e AWS são evoluções posteriores. O código existente é preservado; a existência de serviços ou configurações não comprova homologação operacional.

## Documentação

- [Master plan e critérios de aceite](MASTER_PLAN.md)
- [Trilhas frontend, backend e IA](NEXUS-roadmap)
- [Arquitetura](docs/architecture/overview.md)
- [Estado do backend](docs/BACKEND_PROGRESS.md)
- [Infraestrutura cloud](docs/B9-CLOUD.md)
- [Terraform](infra/terraform/README.md)

O foco deste portfólio é demonstrar regras de negócio, persistência, autorização e integração entre domínios. Métricas de economia, escala e uso por empresas só devem ser publicadas depois de medidas.
