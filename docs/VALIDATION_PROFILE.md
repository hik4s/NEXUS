# Perfil público — Task 5

Plano: `docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md`, Task 5.
Data: 2026-11-09. Base: `926054e`; branch `codex/portfolio-profile`.

## Comportamento

- APP_PROFILE aceita full (padrão compatível) ou portfolio; valor desconhecido é
  rejeitado na configuração. A lista de rotas é construída ao criar a aplicação;
  reiniciar o processo é necessário para mudar de perfil.
- portfolio inclui autenticação, empresas/usuários, catálogo, clientes básicos,
  vendas, depósitos/saldos/movimentos, leituras financeiras, auditoria e importação
  de pedidos. A seleção usa caminhos e métodos explícitos, preservando as
  dependências JWT/RBAC das rotas originais.
- Não inclui jobs, scheduler, upload legado persistente, integrações, IA,
  compras, logística, workflows, leads, interações, transferências ou métricas.
  Mutações financeiras não são montadas; recebem 404/405, inclusive para admin.
- Cadastro público é fechado por padrão em portfolio e aberto por padrão em full.
  PUBLIC_REGISTRATION_ENABLED permite configuração explícita no desenvolvimento.
  Produção portfolio exige cadastro fechado, PostgreSQL/psycopg e segredo adequado.
  Login/refresh de usuários pré-provisionados continuam disponíveis.
- Origens CORS autorizadas recebem cabeçalhos expostos de paginação; isso não
  concede acesso aos dados. O servidor continua verificando empresa/permissão.
- Consultas por UUID de outra empresa em companies/products passam a devolver
  404 em portfolio; full preserva o 403 anterior. Vendas/importação já filtram tenant.

## Readiness

`/readiness` e `/api/v1/health/ready` usam a mesma sondagem e devolvem 503 sanitizado
quando o banco falha. Health simples continua disponível sem consultar banco.
portfolio não consulta Redis nem exige configuração S3 para recursos desativados.

DB_TIMEOUT_SECONDS (1–30; padrão 3) configura conexão, espera do pool e sondagem.
O prazo HTTP cobre a sondagem inteira: a conexão PostgreSQL é isolada do pool ORM,
assíncrona e cancelável; também há statement_timeout no servidor. Ao exceder o
prazo, a API devolve 503 sem aguardar o término da limpeza do driver. Cancelar a
requisição também cancela sua task de sondagem e consome sua exceção.

No Windows, psycopg async exige SelectorEventLoop: a sondagem executa em thread
com loop próprio e prazo interno; a resposta HTTP mantém o prazo externo. Limpeza
do driver/thread pode terminar depois da resposta. SQLite local usa sondagem em
thread; não é permitido no perfil portfolio de produção. A sondagem comprova
conectividade do banco, não disponibilidade de slots no pool das requisições.

Referência consultada para async/cancelamento e Windows:
[documentação oficial psycopg](https://www.psycopg.org/psycopg3/docs/advanced/async.html).

## Falhas reproduzidas e corrigidas

- Testes iniciais falharam por ausência de factory/perfil. Após a implementação,
  7 cenários passaram e token expirado ainda gerou exceção JWT não tratada.
- Tokens access/refresh expirados ou malformados agora devolvem 401. Usuário
  inativo também não acessa a API nem renova a sessão.
- Revisão independente encontrou que manager podia misturar employee+admin ou
  employee+manager na criação/edição. Teste reproduziu a promoção indevida; o
  serviço agora exige roles:manage para qualquer papel elevado, mesmo misturado.
- A revisão apontou pre-ping síncrono antes do timeout SQL. A sondagem passou a
  usar conexão isolada e prazo externo. Teste de probe suspenso verifica 503 em
  menos de 1 s com prazo de teste de 50 ms e cancelamento efetivo. Outro teste
  verifica limpeza da task quando a requisição é cancelada.
- Falha simulada contendo senha/host privados devolve 503 sem esses valores.

## Reprodução

Com um banco local/dedicado e usuários pré-provisionados:

```powershell
$env:APP_PROFILE = 'portfolio'
$env:PUBLIC_REGISTRATION_ENABLED = 'false'
$env:REDIS_ENABLED = 'false'
$env:DB_TIMEOUT_SECONDS = '3'
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Para regressão completa, usar banco descartável vazio, APP_PROFILE=full e o
cadastro padrão desse perfil. A suíte cria apps portfolio isolados para testar
os limites; o restante continua exercitando full. Credenciais/dados são fictícios.
Migrações e ambiente iguais aos relatórios anteriores. Nenhuma nova migração.

Regressão final em bancos vazios, 2026-11-09:

- PostgreSQL `nexus_profile_regression`: **137 passed**, 2 avisos, em 105,62 s.
- SQLite `backend/data/profile-regression.db`: **105 passed, 32 skipped**, 1 aviso,
  em 40,06 s. Os 11 testes novos de perfil executaram nos dois bancos.
- Migrações do zero e Alembic check passaram nos dois bancos, sem divergências.
- Avisos de depreciação já existentes: Starlette/httpx e path_separator do Alembic.
- Revisão independente: os dois achados foram reproduzidos e corrigidos; a
  regressão final inclui RBAC misto, deadline e cancelamento da requisição.
- `git diff --check`: passou. Commits locais; integração e CI no GitHub pendentes.

## Decisões e limites

- As três permissões sales de manager já foram entregues em M2; esta etapa testa
  seu uso no perfil e corrige a promoção por papéis mistos no serviço compartilhado.
  Custo da correção: managers não podem atribuir papéis elevados nem combiná-los
  com employee, inclusive no modo full; esse é o limite de RBAC pretendido.
- A validação de PostgreSQL/cadastro fechado foi antecipada da publicação para
  impedir um perfil de produção incoerente. Desenvolvimento portfolio ainda pode
  usar SQLite e cadastro explicitamente habilitado para preparação local.
- Testes de prazo usam uma sondagem suspensa controlada, não uma falha real de
  rede externa. Conexões reais locais foram usadas nos testes de readiness.
- Sem deploy, navegador, rate limiting de login ou contas demo públicas nesta
  etapa. Antes de publicar, permanecem os passos M3–M6 do plano.
