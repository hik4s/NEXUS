# Supabase Auth Implementation Plan

**Goal:** login livre com Google, GitHub e e-mail, integrado ao RBAC e tenants Nexus.
**Architecture:** identidade externa validada no FastAPI, workspace local automático;
React/Supabase JS com PKCE e sessão por aba.
**Tech Stack:** FastAPI, SQLAlchemy/Alembic, PyJWT, React/TS, supabase-js.
**Spec:** ../specs/2026-11-13-supabase-auth.md

## Global Constraints
Sem convites nesta etapa. Sem serviço pago, service_role no frontend, associação
por e-mail ou dados compartilhados entre novos visitantes. Preservar jornada MVP.

## Review Focus
JWT de outro projeto/algoritmo; metadados de papel controlados pelo usuário;
bootstrap concorrente; callback/renovação após logout; confirmação e recuperação.

- [x] Backend: testes RED de tokens e bootstrap; implementar configuração, verificação,
  migração de identidade e provisionamento; verificar PostgreSQL/SQLite.
- [x] Frontend: cliente PKCE, sessão, login social/e-mail e recuperação; regressões
  de estados e integração com a API preservando navegação por hash.
- [x] UI/fluxos: estados de primeiro acesso, erros claros, sessão e isolamento; E2E.
- [ ] Revisão, configuração de publicação, validação de provedores e evidências M6.

Estado e evidências: [handoff](../../HANDOFF_2026-11-13.md). Publicação e OAuth real pendentes; M6 continua aberto.
