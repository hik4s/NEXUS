# Demonstração local — NEXUS

Requisitos: Docker/Compose 2.24+, Python 3.12 e Node 24.15+ (linha 24).
Os exemplos são para PowerShell; não use banco nem credenciais de produção.

## Instalação

Na raiz de um clone novo:

```powershell
python -m venv backend/.venv
./backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
cd frontend
npm ci
cd ..
Copy-Item .env.example .env
(Get-Content .env).Replace('APP_PROFILE=full','APP_PROFILE=portfolio') | Set-Content .env
docker compose up --build -d
```

A interface usa [localhost:5173](http://localhost:5173), a API
[localhost:8000](http://localhost:8000). Aguarde `/readiness` responder 200.
O Compose de desenvolvimento aplica migrações antes da API. A publicação usa
migrações controladas de release, conforme a etapa M5.

As portas POSTGRES_PORT, API_PORT e FRONTEND_PORT podem ser definidas no `.env`
para executar outro projeto simultaneamente. Ao trocar API/frontend, ajuste também
VITE_API_BASE_URL e CORS_ORIGINS. Os valores padrão são 5432, 8000 e 5173.

## Dados fictícios e acesso

O seed exige APP_ENV=demo/test, DATABASE_URL explícita, senha exclusiva de
demonstração com 12+ caracteres e `--confirm-demo`.

```powershell
$env:APP_ENV = 'demo'
$env:DATABASE_URL = 'postgresql+psycopg://nexus:nexus_dev_password@127.0.0.1:5432/nexus'
$env:NEXUS_DEMO_PASSWORD = 'escolha-uma-senha-exclusiva-demo'
./backend/.venv/Scripts/python.exe scripts/seed_demo.py --confirm-demo
```

| Empresa fictícia | Conta | Papel |
| --- | --- | --- |
| Aurora Comércio · Demo | admin.aurora@example.com | Administrador |
| Aurora Comércio · Demo | gestor.aurora@example.com | Gerente |
| Horizonte Atacado · Demo | admin.horizonte@example.com | Administrador |
| Horizonte Atacado · Demo | operador.horizonte@example.com | Operador |

Use a senha definida no ambiente acima. Não há senha embutida na interface ou no
script. O seed não imprime senhas e não redefine senhas, preços nem saldos que já
existam. Reexecutá-lo não repõe mercadoria consumida por pedidos. Execute um seed
por vez no banco dedicado; a criação inicial não é um provisionador concorrente.

Cada empresa recebe 3 produtos e 1 depósito: PROD-A (120 unidades), PROD-B (80) e
PROD-C (45). Nenhum pedido ou recebível é criado pelo seed.

## Jornada

1. Entre como gestor.aurora@example.com.
2. Abra **Importações** e baixe o modelo ou use os CSVs em `demo/`.
3. Envie `orders-with-errors.csv`: selecione apenas DEMO-001, que reconhece PROD-A.
4. Gere o rascunho e abra o pedido pelo link da referência.
5. Confira depósito, saldos e prazo; confirme a venda no diálogo.
6. Veja o recebível e o estoque; cancele o pedido sem recebimentos e confira a reversão.
7. Consulte a auditoria. Ao entrar com outra empresa, os mesmos registros não ficam acessíveis.

A sessão fica somente em memória: recarregar a página exige novo login. Após uma
falha de comunicação em uma ação, **Consultar estado salvo** faz somente GET; o
controle permanece bloqueado até a consulta terminar com sucesso. Nenhuma mutação
é repetida automaticamente. O usuário decide o próximo passo após consultar os dados.

## Verificações

```powershell
cd frontend
npm run typecheck
npm test -- --run
npm run build
```

Para E2E, crie um PostgreSQL descartável **novo** com nome começando por nexus_e2e.
As portas 8811 (API) e 5180 (UI) devem estar livres. Playwright inicia e encerra
esses servidores; não reutiliza serviços já abertos.

```powershell
$env:NEXUS_TEST_DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/nexus_e2e_local'
$env:NEXUS_DEMO_PASSWORD = 'senha-exclusiva-para-este-teste'
$env:NEXUS_PYTHON = (Resolve-Path ../backend/.venv/Scripts/python.exe).Path
npx playwright install chromium
npm run test:e2e
```

Em Linux, instalar dependências do navegador com `npx playwright install --with-deps chromium`.
O workflow frontend inclui PostgreSQL, typecheck, testes, build e E2E; a execução
no GitHub depende da integração/push do branch.

## Limites desta entrega

- O seletor de produtos na preparação de estoque mostra os primeiros 100 produtos;
  o catálogo em si é paginado. A demonstração usa três produtos por empresa.
- Movimentos recentes mostram 30 registros; recebíveis seguem o contrato de leitura
  atual sem paginação. Importações, pedidos, catálogo e auditoria são paginados.
- Não há promessa de conformidade WCAG: teclado, labels, foco, responsividade e
  movimento reduzido foram implementados; uma auditoria formal de acessibilidade
  permanece futura.
- Esta etapa prepara a aplicação local. Render/Neon, backup/restauração e smoke
  tests públicos pertencem a M5.
