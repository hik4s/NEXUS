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

Em implementação. Critérios e evidências finais serão registrados nesta seção.
