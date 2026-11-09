# M2 — importação e revisão de pedidos

Plano: `docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md`, Tasks 3–4.
Data: 2026-11-09. Base: `599c973`; branch `codex/m2-order-imports`.

## Task 3: parser concluído

Teste inicial falhou na importação do módulo ainda inexistente. Após implementar,
`python -m pytest -q tests/test_order_import_parser.py`: **26 passed**.
Exemplos em `demo/` contêm somente dados fictícios.

Decisões: limite de 200 itens invalida o arquivo inteiro; linhas com quantidade
de colunas incorreta também. Linha vazia vira erro não associado. A contagem de
500 linhas usa registros CSV, e source_lines aponta a linha física inicial de
cada registro (inclusive com campos CSV multilinha). Não há truncamento.

## Task 4: revisão persistida

Implementação: tabelas dedicadas de batches, entries e fontes externas; API de
upload, listagem paginada, detalhe, revalidação, commit da seleção e exportação
de erros. Não usa FileAsset, arquivo persistente, Redis ou worker.

Primeiro teste da API falhou com 404 antes das rotas existirem. A suíte específica
final passou com **46 testes** (26 parser, 18 API/PostgreSQL, 2 limite ASGI).

Cobertura inclui:

- revisão sem efeitos em vendas/estoque/recebíveis, SKU desconhecido, hash repetido
  e erros não associados a pedidos;
- isolamento de hashes, detalhe, seleção, revalidação e exportação entre empresas;
- seleção parcial, mistura de rascunhos novos/existentes e reenvio da seleção;
- mesmo batch em dois commits concorrentes; dois batches com a mesma referência;
  dois uploads do mesmo hash; quotas concorrentes de 20/dia e 100 retidos;
- preço alterado exige 409 catalog_changed; revalidação explícita conserva preços
  committed e erros de parser, com snapshots antes/depois na auditoria;
- falha na segunda criação reverte todos os rascunhos novos da seleção;
- gerente pode gerar rascunhos sem receber privilégios de desconto/pagamento;
  funcionário e usuário não autenticado não exportam a revisão;
- CSV de erros neutraliza fórmulas; SKU com NUL fica inválido sem derrubar outros
  pedidos válidos do mesmo arquivo;
- saldo é apenas aviso na revisão, atualizado novamente na geração; o rascunho
  importado conecta ao fluxo confirmação → baixa/recebível → cancelamento/reversão.

## Revisão e decisões

- A revisão independente apontou SKU inválido com NUL chegando ao parâmetro SQL.
  O teste reproduziu a falha antes do filtro; a linha e seu erro são preservados
  no JSON da revisão, sem enviar esse SKU ao PostgreSQL como parâmetro textual.
- A revisão também apontou que UploadFile recebe o multipart antes da leitura
  limitada. Middleware ASGI agora limita o corpo **antes** do parser multipart,
  mesmo sem Content-Length. Teste sem fim do corpo prova interrupção ao cruzar o
  limite, sem invocar o app/parser. O corpo fica em buffer limitado em memória;
  rotas diferentes continuam com o streaming anterior.
- Limite do conteúdo CSV: 1 MiB; limite adicional do envelope multipart: 64 KiB.
  Uploads com metadados maiores recebem 413. Esse limite não substitui o do arquivo.
- Foram antecipadas de Task 5 apenas as três permissões sales do gerente, pois
  são necessárias à matriz de acesso do MVP em M2. Sem finance:pay/sales:discount.
- Company é bloqueada antes de batch/produtos para serializar quotas e identidades
  externas por tenant. Constraints únicas continuam sendo a garantia no banco.
  Custo: uploads/commits de uma mesma empresa aguardam uns aos outros.
- Entries incluem posição, erros do parser e avisos; batch inclui erros não
  associados. Esses campos permitem ordem estável e revalidação sem perder erros.
- SKUs ambíguos no catálogo são recusados; pedidos cujo total excede Numeric(14,2)
  ficam inválidos, prevenindo erro de banco durante a geração.
- Migração nova `d82b966f6b46` gerada pelo Alembic. O primeiro check SQLite detectou
  default now() específico de PostgreSQL; a revisão ainda não publicada passou a
  usar sa.func.now(), que compila de forma portátil. Migrações históricas intactas.

## Reprodução e limites

Usar PostgreSQL descartável vazio e o ambiente Python registrado em
VALIDATION_MVP.md. Redis fica desabilitado.

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/NEW_DATABASE'
$env:REDIS_ENABLED = 'false'
cd backend
python -m alembic upgrade head
python -m alembic check
python -m pytest -q
```

Todos os testes específicos usam registros fictícios. Os testes de API/concorrência
exigem PostgreSQL; SQLite não é evidência de locks. A suíte legada precisa de banco
novo por execução completa, conforme VALIDATION_M1.md.

Regressão final em bancos vazios, em 2026-11-09:

- PostgreSQL `nexus_m2_regression`: **126 passed**, 2 avisos de depreciação,
  em 98,95 s. As migrações foram também reaplicadas do zero no banco descartável
  `nexus_m2_migrations` após o ajuste de portabilidade; check sem divergências.
- SQLite `backend/data/m2-portable.db`: **94 passed, 32 skipped**, 1 aviso,
  em 34,97 s; migrações e Alembic check passaram.
- Avisos: Starlette/httpx e, no PostgreSQL, path_separator do Alembic.
- `git diff --check`: passou.

Frontend, perfil público restrito, integração/CI no GitHub e deploy seguem pendentes.
Esta entrega testa a jornada por API; não executa navegador nem publica recursos.
