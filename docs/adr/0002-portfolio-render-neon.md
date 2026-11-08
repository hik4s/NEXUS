# ADR 0002 — MVP web com Render e Neon

Data: 2026-11-08. Status: decisão de arquitetura para implementação; deploy pendente.

## Contexto

O NEXUS tem um backend modular amplo e uma interface React inicial. O objetivo imediato é um portfólio demonstrável para vagas júnior com custo zero dentro das cotas gratuitas. O fluxo central será importar/revisar pedidos e comprovar integração entre vendas, estoque e recebíveis.

## Alternativas consideradas

| Alternativa | Consequência |
| --- | --- |
| AWS Fargate/RDS/S3 prevista na visão original | Aproveita Terraform existente, mas introduz operação e custos fora do objetivo imediato |
| Render com Postgres gratuito do próprio Render | Facilita colocação inicial, mas o banco gratuito tem prazo de expiração |
| Render para interface/API e Neon PostgreSQL | Mantém stack e banco persistente externo, sem depender do banco temporário do Render |

Escolha: Render Static Site + Render Web Service + Neon PostgreSQL, com instalação local via Docker Compose. Não há infraestrutura criada por este documento.

## Decisões

1. Manter FastAPI/SQLAlchemy/Alembic e monólito modular.
2. Migrar interface existente de React/JavaScript para React/TypeScript incrementalmente.
3. API REST é a única entrada para regras e autorização; banco não é exposto ao frontend.
4. PostgreSQL é o banco de referência para integração e release; SQLite pode continuar em testes rápidos, sem substituir a validação do banco-alvo.
5. Fazer importação CSV limitada e revisão durável no PostgreSQL; sem armazenamento do arquivo original nem worker permanente no primeiro deploy.
6. Workers/Redis e módulos extras são preservados, mas não necessários para a jornada pública.
7. Não depender de persistência do filesystem do Render.
8. Migrações são etapa explícita e controlada de release, com conexão de DDL apropriada.
9. Tokens, senhas e connection strings não entram em Git ou logs; variáveis VITE_* não contêm segredos.
10. O perfil público deve desativar capacidades que dependem de infraestrutura ausente.

## Consequências

- Cold start e limites dos provedores precisam de tratamento na UI e no cliente de banco.
- O CSV inicial tem limites estritos; importação massiva e processamento resiliente assíncrono ficam para fase posterior.
- Migração para workers preservará a revisão e a deduplicação no banco.
- Anexos persistentes exigirão provedor de object storage antes de entrar no escopo.
- Gratuidade não implica SLA, recursos ilimitados nem ausência de alterações futuras de plano.
- Terraform AWS permanece no repositório, sem ser caminho obrigatório de publicação.
- A hospedagem não comprova integridade de negócio: tests e demonstração devem provar rollback, autorização e prevenção de duplicações.

## Referências

- [MVP ativo](../MVP_PORTFOLIO.md)
- [Inventário do baseline](../REUSE_AUDIT_2026-11-08.md)
- [Render Free](https://render.com/docs/free)
- [Deploy e migrações no Render](https://render.com/docs/deploys)
- [Neon e SQLAlchemy](https://neon.com/docs/guides/sqlalchemy)
- [Neon Free](https://neon.com/pricing)

Condições dos provedores consultadas em 2026-11-08. Rever antes de criar recursos ou alterar plano.
