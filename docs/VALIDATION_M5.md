# Validação M5 — produção Render + Neon

Data: 2026-11-09 (America/Sao_Paulo). **M5 publicado e validado.**

## Evidências já obtidas

- Configuração de produção: TLS, CORS HTTPS explícito e hosts sem wildcard.
  Testes inicialmente falharam para esses casos e passaram após implementação.
- Comando de migração com alvo explícito, conexão direta e advisory lock;
  migração do zero e drift check passaram em PostgreSQL 17 descartável.
- Backend final: **169 testes passaram em PostgreSQL**, em 122,28 s, com dois
  avisos conhecidos (Starlette/httpx e configuração Alembic).
- Frontend: typecheck, **15 testes**, build com a URL pública da API e
  **2 E2E locais** com PostgreSQL real passaram (33,7 s).
- Revisão independente encontrou parâmetros libpq que poderiam sobrescrever o
  alvo da migração; nove casos falharam antes da correção e passaram na regressão
  final. O comando aceita somente parâmetros TLS `sslmode` e `channel_binding`.
- `render.yaml` validado contra o JSON Schema oficial obtido do Render.
  Render CLI não está instalado; validação de plataforma ocorre no planejamento.
- Imagem Docker construída; container usando `PORT=10000` respondeu HTTP 200
  em `/readiness` contra PostgreSQL real.
- Neon dedicado: todas as migrações aplicadas até `d82b966f6b46`, sem drift.
  Credenciais permanecem no ambiente local ignorado e na configuração do serviço.
- Seed real Neon criou duas empresas fictícias, quatro usuários, seis produtos,
  dois depósitos e seis saldos iniciais, sem pedidos pré-criados.
- Backup custom PostgreSQL 18 do Neon: 238.161 bytes. Restaurado com
  `pg_restore --exit-on-error` em PostgreSQL 18 novo; **59 tabelas / 203 registros**
  coincidiram por contagem e SHA-256 do conteúdo ordenado de todas as linhas.
  Arquivo e configurações de cliente permanecem locais e ignorados.
- A API conectada ao banco restaurado também passou readiness, login real e
  consulta dos três saldos da empresa gerente.
- Regressão SQLite: **135 passed, 34 skipped**, em 44,02 s. Os skips não substituem
  a suíte PostgreSQL. Migrações do zero e drift check também passaram no SQLite.

## Deploys e CI comprovados

Implementação de produção: `3887b52`. Ajustes de configuração do Static Site:
`495559e` e `36525c8`. Não houve alteração do código da API após `3887b52`.

| Recurso | Revisão e estado observado |
| --- | --- |
| [Frontend](https://nexus-portfolio-ui.onrender.com) | `36525c8`, deploy `dep-dbp8fo7f3r2c73fdcea0`, **live** |
| [API/readiness](https://nexus-up1i.onrender.com/readiness) | `495559e`, deploy `dep-dbp8d27f3r2c73fd63s0`, **live**, HTTP 200 |
| Blueprint `NEXUS Portfolio` | `exs-dbp8a9ff3r2c73fcuv00`; plano final **no_changes** |
| [CI backend](https://github.com/hik4s/NEXUS/actions/runs/42745175731) | `495559e`, **success** |
| [CI frontend/E2E](https://github.com/hik4s/NEXUS/actions/runs/42744829867) | `3887b52`, **success**; frontend fonte inalterado nos ajustes posteriores |

O usuário aprovou a aplicação do plano. Foram adotados apenas os dois serviços
NEXUS; demais serviços do workspace permaneceram fora do Blueprint. API Free,
Static Site e Neon Free, sem Redis, disco ou banco temporário Render.
Auto-deploy e auto-sync permanecem desligados: cada release exige migrar antes de
publicar. Não foi configurado keep-alive para impedir hibernação.

A adoção via integração não persistiu de forma coerente os campos do Static Site;
os logs mostraram build bem-sucedido seguido de publish directory inexistente.
A configuração foi corrigida pelo painel com **Verify Settings → Update Fields**:
root `frontend/`, build `npm ci && npm run build`, publish `dist`. Um novo build
publicou com sucesso; o plano final sem mudanças confirma alinhamento com o YAML.

## Smoke público e persistência

Executado contra HTTPS real, com contas fictícias provisionadas e senha exclusiva
guardada localmente, sem credenciais no bundle:

- Login gerente e administrador da segunda empresa; cadastro público recusado.
- Upload com pedido válido e SKU desconhecido; revisão sem alterar estoque.
- Commit repetido devolveu o mesmo pedido; rascunho não criou recebível.
- Confirmação baixou duas unidades, criou um único recebível de R$ 65,80 e
  repetição da confirmação retornou 409 sem novo efeito.
- Cancelamento restaurou o estoque e cancelou o recebível.
- Outra empresa recebeu 404 para o pedido e a revisão; CORS aceitou a origem
  exata da UI e não autorizou uma origem externa. Docs/jobs fora do perfil: 404.
- HTML e JavaScript públicos responderam 200; bundle aponta à API de produção.
  Rewrite de um caminho da SPA também respondeu 200.
- Depois de um novo deploy da API, os mesmos IDs de pedido, revisão e recebível
  continuaram acessíveis, com status cancelado e recebível único.

Registro de prova: batch `1daead31-1645-4d68-91e4-23db84e3f5dd`, pedido
`ac852a29-1740-4c0a-b55d-19e3e3cc8b4b`. São dados fictícios e seus IDs não
substituem autenticação/autorização.

Medições desta execução: readiness em **1,531 s**, sequência do smoke em
**32,14 s**; rede externa, API Virginia e banco São Paulo. O redeploy da API levou
aproximadamente **55 s** entre início e `live`, incluindo build e inicialização.
Essas medidas não representam latência de produção em escala nem SLA.

## Limites e próxima etapa

- Hibernação natural após ociosidade não foi cronometrada. Foram comprovados
  inicialização, readiness, persistência após redeploy e tratamento de serviço
  indisponível na suíte da UI; não se atribui o tempo de redeploy ao cold start
  por hibernação. A primeira requisição pode exigir aguardar e consultar novamente.
- Backup local/restauração foi um ensaio pontual com dados fictícios; não há
  agendamento de backup ou promessa de retenção do provedor.
- Credenciais demo não foram publicadas. Antes de divulgar acesso em M6, usar
  senha de gerente distinta da administração e revisar o controle de abuso.
- As limitações de paginação/acessibilidade de M3/M4 continuam documentadas em
  [LOCAL_DEMO.md](LOCAL_DEMO.md). M6 (vídeo, apresentação e release) fica pendente.
