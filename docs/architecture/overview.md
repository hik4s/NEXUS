# Arquitetura do NEXUS

Atualização ativa: 2026-11-08. A aplicação continua sendo um monólito modular. O recorte de entrega atual é a jornada de pedidos, estoque e recebíveis.

| Componente | Responsabilidade | Execução alvo |
| --- | --- | --- |
| React + TypeScript + Vite | Interface pt-BR, sessão e revisão humana | Render Static Site |
| FastAPI + Pydantic | Contratos HTTP, identidade e autorização | Render Web Service |
| Serviços existentes | Regras de vendas, estoque, recebíveis e auditoria | Mesmo processo da API |
| SQLAlchemy + Alembic | Persistência e migrações versionadas | Conexão PostgreSQL |
| PostgreSQL | Dados, revisão durável, constraints e transações | Neon; Docker local |

Frontend comunica somente com a API; a API consulta serviços e banco. Não há conexão do navegador ao PostgreSQL.

## Estado atual versus alvo

- Backend modular, modelos, migrações e pytest já existem.
- Frontend atual é React/JavaScript com acesso e produtos; TypeScript e telas da jornada estão planejados.
- Importador atual processa clientes. Revisão/importação de pedidos é nova.
- Render/Neon ainda precisam de configuração e homologação.
- Workers/Redis, IA, integrações e Terraform AWS permanecem no repositório como evolução, sem serem dependências da demonstração pública.

## Fronteiras

- Tenant e permissões são resolvidos na API.
- Confirmar/cancelar exige uma transação para pedido, estoque, recebível e auditoria.
- Revisão não reserva estoque; confirmação revalida o saldo.
- CSV limitado é processado em requisição; conteúdo normalizado e resultado ficam no banco. Não há dependência de arquivo local ou worker permanente.
- Identidade externa e constraints impedem duplicação de importações.
- Migrações são etapa explícita de release. Segredos ficam no ambiente do serviço.

Consulte os contratos completos em [MVP_PORTFOLIO.md](../MVP_PORTFOLIO.md), as decisões em [ADR 0002](../adr/0002-portfolio-render-neon.md) e o [inventário](../REUSE_AUDIT_2026-11-08.md).
