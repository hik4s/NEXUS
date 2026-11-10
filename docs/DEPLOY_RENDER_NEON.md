# Publicação de demonstração — Render + Neon (M5)

Configuração de release criada em 2026-11-09. O estado comprovado de publicação
fica em [VALIDATION_M5.md](VALIDATION_M5.md); a existência deste roteiro não
comprova que um serviço esteja disponível.

## Recursos e custo

O `render.yaml` contém somente `NEXUS` (Web Service Docker, plano Free,
Virginia) e `nexus-portfolio-ui` (Static Site). O PostgreSQL é externo, no Neon
Free. Não provisionar Postgres Render, Redis, worker, disco ou plano pago.
O Blueprint mantém deploy automático desligado para permitir a migração antes
de publicar código novo. Uma sincronização inicial ainda pode iniciar builds.

Confira uso e limites nas contas antes de cada release. Gratuidade não é SLA.
Não habilite upgrades automáticos ou cobrança para ultrapassar as cotas.
Referências: [Render Free](https://render.com/docs/free),
[Neon Free](https://neon.com/pricing).

## Banco e segredos

Use um projeto dedicado somente a dados fictícios. O provisionamento inicial
deste ambiente utilizou Neon PostgreSQL 18, região São Paulo; a API Render está
em Virginia. As regiões distintas acrescentam latência e devem entrar nas
medições, sem alegações de desempenho não observado.

Guarde a URL direta em `NEXUS_RELEASE_DATABASE_URL` no arquivo local `.env.m5`,
ignorado pelo Git. A URL aceita `postgresql://` (normalizado para psycopg pelo
comando de release) ou `postgresql+psycopg://`, mantendo `sslmode=require` ou
verificação de certificado mais forte. Não use o hostname `-pooler` em migrações.

`DATABASE_URL` no Render precisa do prefixo `postgresql+psycopg://`. A aplicação
pode usar conexão direta com o pool pequeno configurado, ou uma conexão pooled
validada separadamente. A conexão direta evita DDL pelo pooler. Cada processo
permite 2 conexões persistentes + 1 overflow; readiness abre uma conexão adicional.
Há pre-ping, reciclagem em 300 s e timeout de conexão/pool de 10 s no Blueprint.

O arquivo local também pode guardar `NEXUS_SECRET_KEY` e `NEXUS_DEMO_PASSWORD`.
Não enviar esse arquivo, backups, tokens ou credenciais ao GitHub. Nunca inserir
segredos em variáveis `VITE_*`, que ficam no JavaScript público.

## Migração controlada

Na raiz do repositório, com dependências do backend instaladas e o banco correto
selecionado:

```powershell
$env:APP_ENV = 'production'
# Defina NEXUS_RELEASE_DATABASE_URL com o mecanismo local de secrets.
# Informe somente o hostname e o nome do banco, nunca a URL na linha de comando.
./backend/.venv/Scripts/python.exe scripts/migrate_release.py `
  --expected-host SEU_HOST_DIRETO --expected-database SEU_BANCO --confirm-release
```

O comando recusa ambiente implícito, SQLite, alvo divergente, pooler e ausência de
TLS em produção. Adquire advisory lock de sessão, aplica `upgrade head`, verifica
drift e retorna a revisão. Falha de conexão retorna erro sem imprimir o DSN.
Não executa downgrade e não migra a cada boot. Testes `APP_ENV=test` só aceitam
host local. Execute uma release por vez e faça backup antes de futuras migrações.

Para o primeiro seed, use uma operação administrativa separada com `APP_ENV=demo`,
`DATABASE_URL` explícita, `NEXUS_DEMO_PASSWORD` exclusiva e
`scripts/seed_demo.py --confirm-demo`. Volte o serviço para `APP_ENV=production`;
não altere o ambiente da API publicada para viabilizar o seed. O seed não redefine
senha nem repõe saldos existentes. Exponha apenas a conta gerente de demonstração,
nunca a conta administradora. O cadastro público continua fechado.

## Build e ambiente da API

No serviço existente ou no Blueprint:

| Campo | Valor |
| --- | --- |
| Branch | `main` |
| Runtime | `Docker` |
| Root Directory | `backend` |
| Dockerfile Path | `./Dockerfile` |
| Docker Context | `.` |
| Docker Command | vazio; usa o CMD da imagem |
| Health Check Path | `/readiness` |
| Plano | `Free` |

O Dockerfile usa `0.0.0.0:${PORT:-8000}`, com `exec` para entregar SIGTERM ao
Uvicorn. Não combina migrações com o start. O contexto exclui `.env`, dados locais
e caches. Não copiar o Dockerfile para a raiz sem ajustar o contexto e os COPY.

Variáveis: `APP_ENV=production`, `APP_PROFILE=portfolio`,
`PUBLIC_REGISTRATION_ENABLED=false`, `REDIS_ENABLED=false`,
`ENABLE_DOCS_IN_PRODUCTION=false`, `ENABLE_METRICS_ENDPOINT=false`,
`DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS` e `TRUSTED_HOSTS`.

`CORS_ORIGINS` contém a origem HTTPS exata do Static Site, sem caminho ou barra
final. `TRUSTED_HOSTS` contém o hostname exato da API, sem protocolo. Não usar `*`.
O backend recusa configurações publicadas inseguras. Configure secrets antes de
ativar tráfego; `sync:false` só solicita valores na criação, e não atualiza
secrets de serviços já existentes. `generateValue:true` preserva secrets existentes.

## Frontend

Static Site, Root Directory `frontend`, Node `24.21.0`, build
`npm ci && npm run build`, publish directory `dist`.
Defina `VITE_API_BASE_URL=https://HOST_DA_API/api/v1` antes do build.
O Blueprint reescreve `/*` para `/index.html`. Alterar essa variável requer novo
build, não apenas restart da API. Não publicar pelo Dockerfile de desenvolvimento.

## Operação da release

1. Rodar regressões PostgreSQL, frontend e E2E em bancos locais descartáveis.
2. Revisar diff e atualizar `main`; Render precisa ler arquivos já enviados.
3. Fazer backup, migrar o Neon pela conexão direta e confirmar revisão/drift.
4. Planejar a sincronização do Blueprint com adoção apenas do serviço NEXUS.
   Conferir o plano: não modificar outros serviços do workspace.
5. Configurar variáveis exatas, aplicar o plano e acompanhar cada deploy até `live`.
6. Verificar readiness, login, CSV com erro, commit, confirmação, recebível,
   cancelamento e isolamento; testar persistência após novo processo/deploy.
7. Registrar URLs/commit e tempos observados no relatório. Um build verde sem
   smoke test não conclui M5.

O Free pode hibernar; a UI informa indisponibilidade e não repete mutações.
Requisições iniciais podem exceder o timeout de 15 s do cliente. Aguarde o serviço
ficar pronto e consulte o estado salvo antes de decidir repetir uma ação.

## Exportação e restauração

Use clientes PostgreSQL da mesma versão do servidor ou mais novos. Para Neon 18,
use `pg_dump`/`pg_restore` 18. Configure as variáveis PGHOST, PGDATABASE, PGUSER,
PGPASSWORD e PGSSLMODE em ambiente protegido, sem credenciais nos argumentos:

```text
pg_dump --format=custom --no-owner --no-acl --file=nexus-demo.dump
# Apenas em banco novo, dedicado e explicitamente descartável:
pg_restore --exit-on-error --no-owner --no-acl --dbname=BANCO_NOVO nexus-demo.dump
```

Restaure em banco vazio, não use `--clean` sobre dados existentes. Compare revisão,
contagens e registros do fluxo e faça smoke test com a API apontando ao restaurado.
Backups contêm hashes de senha e devem ficar fora de Git, artifacts públicos e
logs. Armazene-os com acesso restrito e proteção adequada; o dump local sozinho
não é estratégia de retenção nem comprovação de recuperação contínua do provedor.

Referências verificáveis: [Blueprint](https://render.com/docs/blueprint-spec),
[Docker](https://render.com/docs/docker),
[Deploys](https://render.com/docs/deploys),
[Neon pg_dump/pg_restore](https://neon.com/docs/import/import-from-postgres).
