# M1 — integridade transacional

Plano: `docs/superpowers/plans/2026-11-08-nexus-portfolio-mvp.md`, Task 2.
Data: 2026-11-09. Base: `f347d08` (M0); branch `codex/m1-transactions`.

## Mudanças e garantias verificadas

- Transições bloqueiam o pedido no PostgreSQL e recarregam seu estado e relações.
  Duas confirmações ou cancelamentos sobre snapshots antigos têm um vencedor;
  a outra tentativa recebe 409, sem duplicar movimentação, recebível ou auditoria.
- Uma falha financeira após baixar estoque desfaz a transação inteira. O teste
  também verifica que um commit posterior do chamador não salva efeitos parciais.
- `create_order(..., commit=False)` permite que o chamador controle a transação;
  o padrão `commit=True` preserva a compatibilidade dos outros callers.
- Criação HTTP de pedido, auditoria e resposta idempotente usam um único commit.
  Reservas não são publicadas separadamente; a constraint de unicidade serializa
  duas requisições com a mesma chave.
- Falha antes de persistir a resposta deixa zero pedidos extras. Resposta perdida
  depois do commit é recuperada pela mesma chave, sem criar outro pedido.
- Pagamento e cancelamento consultam o recebível sob lock e com refresh do ORM.
  Os testes deste ponto cobrem snapshots obsoletos em duas sessões; não simulam
  dois escritores simultâneos de pagamento/cancelamento.
- Consultas financeiras projetam status de vencimento para a resposta, sem
  alterar ou commitar modelos persistentes. Um GET com snapshot antigo não pode
  sobrescrever um cancelamento confirmado por outra sessão.
- Constraints de unicidade de fulfillment e recebível por pedido já existiam;
  nenhuma migração nova foi necessária.

## Evidências e reprodução

`backend/tests/test_sales_concurrency.py` cobre os cenários acima com PostgreSQL
real e sessões independentes. Casos concorrentes usam barreira de threads; as
transições definem lock_timeout para não deixar um deadlock bloquear a suíte.

Antes das correções: 5 testes falharam e 1 passou. Foram observados IntegrityError
na segunda confirmação, dois cancelamentos bem-sucedidos, estoque parcial após
falha financeira e pedido salvo antes da resposta idempotente. Os dois testes
adicionais de snapshot financeiro também falharam antes dos locks/refresh.

A revisão independente encontrou gravações em consultas financeiras. Dois testes
novos reproduziram o problema antes da correção e verificam a ausência de writes
mesmo quando o chamador executa um commit posterior.

Use um banco descartável **novo para cada execução completa**. Parte da suíte
legada usa nomes de empresas fixos, portanto repetir no banco de M0 gera 409 de
cadastro. As execuções iniciais em bancos reutilizados tiveram 18 falhas por esse
motivo, sem representar o resultado da regressão em banco vazio.

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/NEW_DATABASE'
$env:REDIS_ENABLED = 'false'
cd backend
python -m alembic upgrade head
python -m alembic check
python -m pytest -q
```

Ambiente Python/driver e PostgreSQL iguais aos registrados em VALIDATION_MVP.md.
Banco PostgreSQL da regressão: `nexus_m1_regression`, no container descartável
`nexus-m0-postgres`, porta 55432. SQLite da regressão: `backend/data/m1-fresh.db`.

Resultado final em bancos novos:

- PostgreSQL: migrações do zero e Alembic check passaram; **80 passed**, 2 avisos
  de depreciação (Starlette/httpx e path_separator do Alembic), em 75,53 s.
- SQLite: migrações do zero passaram; **66 passed, 14 skipped**, 1 aviso de
  depreciação (Starlette/httpx), em 34,71 s.
- Os 12 testes novos exclusivos de PostgreSQL passaram na regressão completa.
- `git diff --check`: passou.

## Decisões e limites

- A remoção de writes nos GETs financeiros amplia M1 apenas para fechar a falha
  encontrada pela revisão. O contrato HTTP permanece igual; serviços de listagem
  agora retornam snapshots Pydantic, em vez de entidades ORM. Custo de eventual
  incompatibilidade: adaptar consumidores internos; a busca encontrou apenas as
  rotas correspondentes, cujas anotações foram atualizadas.
- Não se afirma proteção global de todos os fluxos de pagamento: movimentações
  concorrentes de caixa entre recebíveis distintos e contas a pagar precisam de
  avaliação própria. As garantias desta etapa são as do fluxo de vendas descrito.
- PostgreSQL é a evidência de locks; SQLite ignora os testes exclusivos de banco.
- Os commits continuam locais; execução de CI no GitHub e integração pendentes.
