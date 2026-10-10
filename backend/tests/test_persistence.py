from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.db.transaction import transaction
from app.db.session import engine
from app.models.company import Company


def test_database_contains_core_schema() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "companies",
        "users",
        "products",
        "sales_orders",
        "stock_balances",
        "purchase_orders",
        "financial_accounts",
        "deliveries",
        "workflow_tasks",
        "api_keys",
        "webhook_deliveries",
    }
    assert expected.issubset(tables)


def test_transaction_context_rolls_back_on_failure() -> None:
    slug = f"rollback-{uuid4().hex[:12]}"
    with Session(engine) as db:
        try:
            with transaction(db):
                db.add(Company(name="Rollback Probe", slug=slug))
                db.flush()
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        assert db.scalar(select(Company).where(Company.slug == slug)) is None
