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
- [x] Revisão e correções de autenticação; regressões e suites aprovadas.
- [x] Integração, migração Neon e configuração/deploy API/frontend.
- [x] Login por senha, isolamento, reload/logout e confirmação por link/código em HTTPS.
- [x] Novo template de confirmação publicado no NEXUS Auth.
- [ ] Conclusão OAuth Google/GitHub por uma pessoa real.
- [ ] Entrega da nova confirmação a destinatário real e recovery completo/nova aba.
- [ ] Evidências finais de portfólio e M6.

Estado consolidado em 15/11: [handoff atual](../../../HANDOFF_2026-11-15.md).
Evidências: [revisão](../../AUTH_REVIEW_2026-11-15.md),
[publicação](../../RELEASE_AUTH_2026-11-15.md) e
[link/código](../../EMAIL_CONFIRMATION_2026-11-15.md).
