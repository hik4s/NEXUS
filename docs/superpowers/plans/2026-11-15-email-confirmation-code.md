# Email confirmation and OTP Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution.

**Goal:** confirmação robusta por link/código e e-mail NEXUS pt-BR.
**Architecture:** React com verificação explícita Supabase; token hash só em memória;
template HTML versionado e publicado no projeto existente.
**Tech Stack:** React/TypeScript, supabase-js 2.119.0, Vitest/Playwright.
**Spec:** ../specs/2026-11-15-email-confirmation-code.md

## Global Constraints

Sem desativar confirmação, sem sessão implícita, sem secrets no frontend.
Preservar login OAuth/recuperação/RBAC. Nunca registrar OTP/token hash.

## Review Focus

Pré-fetch de link não deve consumir prova; URL limpa; sessão antiga não aparece;
erro/expiração/reenvio não confirma conta; resposta tardia não troca conta;
email OTP usa tipo correto; teste real não dispara mensagens a terceiros.

## Task 1 — Verificação por link e código

- [ ] RED: testes de formulário OTP/cadastro/reenvio, link explícito sem auto-consumo,
  URL limpa, código inválido e erro legado orientado.
- [ ] Implementar EmailConfirmation.tsx e emailConfirmation.ts, integrar App e
  SupabaseLoginPage, mapear erros de callback, adicionar CSS focado.
- [ ] GREEN: suíte completa frontend, typecheck/build e smoke de navegador.

## Task 2 — Template e publicação

- [ ] Criar supabase/templates/confirmation.html e instruções/templates versionados.
- [ ] Renderizar prévia sintética desktop/mobile e inspecionar legibilidade/links.
- [ ] Revisão independente, testes reais de verifyOtp com contas sintéticas,
  corrigir regressões; abrir/integrar PR após CI.
- [ ] Publicar UI e template sem substituir SMTP/OAuth; validar configuração real.
- [ ] Atualizar handoff/evidências e informar limites verificados.
