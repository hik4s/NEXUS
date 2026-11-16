# M6 — evidências de preparação da release

Data: **16/11/2026**, America/Sao_Paulo. Código avaliado:
[`afd94f2e8c5f1e939c80f22337ca7cc0cb3eac81`](https://github.com/hik4s/NEXUS/commit/afd94f2e8c5f1e939c80f22337ca7cc0cb3eac81).
Esta branch acrescenta materiais e documentação; não altera aplicação ou schema.
**M6 continua aberto até integração, CI e identificação da release.**

## Regressão desta execução

| Verificação | Resultado |
| --- | --- |
| Instalação frontend pelo lockfile | npm ci aprovado |
| PostgreSQL 17, banco vazio, Alembic upgrade head | aprovado, revisão 0552c7d5fe36 |
| Alembic check | sem operações novas |
| Backend completo | 187 passed, 2 warnings, 66,37 s |
| Frontend TypeScript | aprovado |
| Frontend Vitest | 46 passed, 9 arquivos |
| Build Supabase / API pública configurada | aprovado |
| Chromium, duas empresas + mobile | 2 passed, 49,3 s com gravação e pausas de leitura |

Ambiente: Python 3.12.14, Node 24.22.1, Chromium Playwright 1254, PostgreSQL 17 em
contêiner dedicado. Bancos `nexus_m6_regression` e `nexus_e2e_m6`, somente locais.
Não houve acesso a dados de negócio reais nem criação de contas em produção.
Avisos existentes: Starlette TestClient/httpx e Alembic path_separator.

Build: entrada 473,20 kB / gzip 135,97; workspace separado 48,32 kB / gzip 11,26.
Tamanhos são do build observado, sem medição de rede de usuários nem teste de carga.

A gravação usa a jornada existente em `frontend/e2e/portfolio-flow.spec.ts`, com
pausas de leitura, vídeo habilitado e legendas. Asserções de negócio e isolamento
foram preservadas. E2E usa auth **legacy local**, API real e PostgreSQL: comprova a
jornada ERP, não OAuth nem entrega SMTP. As pausas elevam o tempo do teste; não são
latência do produto. Regressão SQLite não foi repetida nesta entrega documental.

## Materiais

- [Vídeo MP4, 33,04 s, legendas pt-BR](media/2026-11-16/nexus-jornada.mp4).
- [Galeria e condições de captura](media/2026-11-16/README.md).
- [Roteiro para avaliar no site](AVALIAR_NEXUS.md), com produto, saldo e CSV de exemplo.

O vídeo mostra a revisão com SKU desconhecido bloqueado, rascunho válido,
confirmação, cancelamento e tentativa recusada de abrir pedido de outra empresa.
Verificações da API: rascunho não altera saldo; confirmar reduz duas unidades e
cria recebível de R$ 65,80; cancelar restaura saldo e cancela o recebível; outra
empresa recebe 404 para pedido/importação. A automação também verifica navegação
mobile sem transbordamento horizontal e carregamento do workspace após login.

## Consulta pública em 16/11

| Recurso | Resultado desta consulta |
| --- | --- |
| Interface HTTPS | 200, 0,43 s |
| `/readiness` API | 200, `status=ready`, `database=ok`, 45,48 s |

Valores medidos da máquina de teste com relógio monotônico, incluindo proxy/rede.
Não identificamos o estado anterior de hibernação; **não é medição de cold start
natural**. Não generalizar a disponibilidade nem o tempo observado. Os assets
públicos `index-gEWkeGFA.js` e `index-IGLSp6oR.css` coincidem com o build observado.
Essa consulta não é nova homologação de login, venda pública ou OAuth.

## Reproduzir os checks

Em bancos descartáveis, com dependências já instaladas:

```bash
cd backend
# Defina DATABASE_URL para PostgreSQL local descartável, nunca produção.
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic check
.venv/bin/python -m pytest -q
cd ../frontend
npm ci
npm run typecheck
npm test -- --run
# Defina VITE_AUTH_PROVIDER, VITE_SUPABASE_URL, VITE_SUPABASE_PUBLISHABLE_KEY
# e VITE_API_BASE_URL conforme .env.example para verificar o build publicado.
npm run build
# Defina NEXUS_TEST_DATABASE_URL (banco novo nexus_e2e*),
# NEXUS_DEMO_PASSWORD exclusiva e NEXUS_PYTHON se necessário.
npm run test:e2e
```

Para gerar novamente as capturas existentes, `NEXUS_CAPTURE_DIR` define o diretório
de saída do E2E. O vídeo desta entrega foi exportado via FFmpeg a partir de uma
configuração temporária de gravação; sua identificação consta no manifesto
SHA-256 da galeria. Não há senhas/tokens nos materiais versionados.

## Pendências que não foram encerradas

- Integrar este material, verificar CI do commit final e criar tag/release.
- Entrega real do novo e-mail e recuperação de senha completa, incluindo nova aba.
- Medir inicialização após hibernação natural com condição anterior conhecida.
- Backup periódico/retenção e novo ensaio de restauração.
- Paginação de recebíveis, seletor de estoque acima de 100 produtos e melhorias
  de acessibilidade são evoluções seguintes, sem implementação nesta branch.

Nenhum deploy é necessário para atualizar somente Markdown e mídia no GitHub.
