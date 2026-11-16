# NEXUS — memória do projeto

Consolidada em 15/11/2026. Estado de operação e pendências:
[handoff atual](HANDOFF_2026-11-15.md).

## Propósito e recorte

Transformar operações de pequenas empresas em fluxos rastreáveis. O MVP ativo
é CSV de pedidos → revisão → rascunhos → venda → estoque/recebível → cancelamento
com reversão. M0–M5 estão entregues; M6 é apresentação, vídeo e fechamento das
evidências. A visão ampla de ERP/IA não é o critério de conclusão deste recorte.

## Arquitetura e decisões duráveis

- Monólito modular FastAPI/Pydantic/SQLAlchemy/Alembic, dados de negócio e RBAC
  no PostgreSQL Neon. Frontend React/TypeScript/Vite; API e UI no Render.
- Supabase é identidade, não um segundo banco de negócio. Projeto correto:
  NEXUS Auth `mszdilxysgnmkyekknat`. Não modificar CareerOS por engano.
- Acesso livre, workspace privado e admin local no primeiro login. Convites
  adiados. Tenant/papéis vêm do banco local, nunca de metadata editável do usuário.
- Não vincular automaticamente por e-mail. Contas legadas são preservadas e
  exigem migração explícita; modo `legacy` continua para ambientes locais.
- Sessão por aba em sessionStorage; não introduzir bearer tokens no localStorage.
  Provas PKCE temporárias podem atravessar abas do mesmo navegador/origem.
- Migração controlada antes do deploy, sem executar DDL a cada boot. Serviços
  gratuitos e auto-deploy off. Sem Redis/worker permanente/arquivos locais no
  caminho crítico do MVP público. Não contratar recursos pagos incidentalmente.
- Preços/estoque/financeiro/autorização permanecem sob autoridade da API; valores
  monetários usam Decimal. Não repetir mutações após resposta incerta: consultar
  estado salvo antes de permitir decisão explícita do usuário.

## Evolução recente comprovada

MVP Render/Neon e backup/restauração têm evidências em M5. Em 15/11, PR #3 integrou
autenticação Supabase revisada e a migração `0552c7d5fe36`, com backup antes da
alteração. Login por senha e duas empresas isoladas foram verificados em HTTPS.

Um e-mail de confirmação padrão chegou em spam; o clique confirmou o endereço,
mas não concluiu a sessão no aplicativo. PR #4 adicionou link com confirmação
explícita e alternativa por código, orientações de erros e trava entre operações.
Template pt-BR com botão/OTP foi publicado no Supabase, preservando SMTP Brevo.

Link usa fragmento, é limpo antes da interface e não consome a prova ao carregar.
Código usa `verifyOtp(type=email)`. Esse tipo genérico também pode aceitar outras
provas de e-mail do provedor; não anunciar exclusividade criptográfica de signup.
Reenvio de confirmação usa callback PKCE para mensagens durante a troca de modelo.

## Regras que não devem regredir

- Não aceitar sessão implícita da URL para contornar uma confirmação quebrada.
- Recuperação exige prova do provedor vinculada à conta/sessão; uma flag de URL
  não concede elegibilidade para redefinir senha.
- Callback inválido não abre silenciosamente a conta já persistida na aba.
- Troca de conta esconde workspace anterior; respostas tardias não restauram
  outra identidade. Link, código e reenvio não podem disputar a sessão.
- Não desabilitar confirmação, expor secret/service_role, publicar senhas demo,
  DSNs, relatórios, OTPs ou tokens. Somente chave publishable no frontend.
- Usar dados fictícios e limpar apenas identidades/workspaces de teste próprios.

## Validação e interpretação

187 testes PostgreSQL e 153 SQLite/34 skips na revisão backend; 43 frontend e
2 E2E de negócio após a evolução de confirmação. CI e build aprovados. As provas
reais por código/hash foram verificadas no provedor e no site publicado com
contas sintéticas, depois removidas. O template foi salvo e reaberto no painel.

E2E de negócio em legacy não comprova OAuth. Geração administrativa de provas
sem envio não comprova entrega SMTP. Novo visual não corrige reputação do remetente
por si só. OAuth completo foi relatado pelo usuário em 15/11. Mensagem nova recebida por destinatário real e recovery
fim a fim ainda precisam de evidências. JWT já emitido pode durar até expirar;
não se promete revogação imediata em todas as chamadas da API.

## Próxima sessão

Começar pelo handoff, confirmar branch/commit e ambiente antes de alterar algo.
Não reimplementar as entregas já integradas. Priorizar homologação real dos
provedores/entrega/recovery e M6; depois operação/backup, cold start e melhorias de paginação/acessibilidade. Histórias locais antigas
continuam preservadas no [arquivo da auditoria](docs/archive/MEMORIA_PROJETO_2026-11-15_ANTES_DA_CONSOLIDACAO.md).

## Fontes

- [README e execução](README.md)
- [Handoff atual](HANDOFF_2026-11-15.md)
- [Release Supabase](docs/RELEASE_AUTH_2026-11-15.md)
- [Link/código e template](docs/EMAIL_CONFIRMATION_2026-11-15.md)
- [Template versionado](supabase/templates/README.md)
- [Deploy controlado](docs/DEPLOY_RENDER_NEON.md)
- [Master plan](MASTER_PLAN.md)

### Continuação de carregamento — 15/11

Workspace carregado após login, com espera e opção de recarregar em falha.
Limpeza proativa de provas PKCE inválidas/vencidas preserva fluxos válidos.
Build Supabase: entrada 473,20 kB e workspace separado 48,32 kB minificados.
Validação: [registro de continuidade](docs/NEXUS_LOADING_PLAN_2026-11-15.md).

## Continuidade em 16/11 — preparação de M6

Main afd94f2 já publicada; autenticação não foi refeita. Regressão de 187 backend/46
frontend/2 E2E aprovada, vídeo local de 33 s e capturas adicionados. Produção permaneceu
sem mudanças. Integração/tag de M6 e limites operacionais continuam abertos.
Retomar pelo [handoff de 16/11](HANDOFF_2026-11-16.md).
