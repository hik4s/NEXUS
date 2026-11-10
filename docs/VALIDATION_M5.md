# Validação M5 — produção Render + Neon

Data: 2026-11-09. Etapa em execução; não concluída apenas pela configuração.

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
- Static Site inicial está `live`; a atualização final e o smoke integrado
  dependem da API. Não é ainda aceite da jornada pública.

## Pendências antes do aceite

- Revisar e enviar a configuração ao GitHub, planejar/adotar somente NEXUS e
  criar o Static Site no Render Free.
- Aguardar os dois deploys e executar smoke tests públicos/persistência/cold start.
- Registrar commit e URLs comprovadas, preservando diferenças entre teste local,
  verificação remota e limitações ainda abertas.
