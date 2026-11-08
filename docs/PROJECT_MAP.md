# Mapa do NEXUS

Atualizado em 2026-11-08.

## Documentação ativa

- [MVP de portfólio](MVP_PORTFOLIO.md): arquitetura, fluxo, contratos, limites e aceite.
- [Inventário de reaproveitamento](REUSE_AUDIT_2026-11-08.md): leitura do baseline e decisões.
- [ADR de hospedagem](adr/0002-portfolio-render-neon.md): Render + Neon.
- [Plano de implementação](superpowers/plans/2026-11-08-nexus-portfolio-mvp.md): tarefas e verificações.
- [Master plan](../MASTER_PLAN.md): checkpoint ativo e histórico da visão ampla.

## Código existente

| Área | Diretório |
| --- | --- |
| Rotas REST | backend/app/api/v1/routes |
| Regras de negócio | backend/app/services |
| Contratos de entrada/saída | backend/app/schemas |
| Modelos SQLAlchemy | backend/app/models |
| Identidade e papéis | backend/app/identity e backend/app/rbac |
| Auditoria | backend/app/audit |
| Migrações | backend/alembic/versions |
| Testes backend | backend/tests |
| UI React/JavaScript inicial | frontend/src |
| Workers e IA preservados | backend/app/workers e backend/app/intelligence |
| Infra AWS futura | infra/terraform |

O backend não possui uma camada de repositórios de dados implementada apenas por existir a pasta repositories. Os serviços usam Session/SQLAlchemy diretamente. Seguir esse padrão onde suficiente.

## Novidades planejadas

Parser e revisão de pedidos, tabelas próprias de importação, UI React/TypeScript por funcionalidade, CI PostgreSQL/frontend/E2E, seed fictício e render.yaml. Esses elementos são planejamento, não arquivos existentes no baseline.
