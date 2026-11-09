import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.company import Company
from app.models.inventory import StockBalance, StockMovement, Warehouse
from app.models.product import Product
from app.models.user import User


def load_seed():
    path = Path(__file__).resolve().parents[2] / 'scripts' / 'seed_demo.py'
    spec = importlib.util.spec_from_file_location('nexus_demo_seed', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_requires_explicit_demo_environment_and_flag(monkeypatch):
    seed = load_seed()
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('NEXUS_DEMO_PASSWORD', 'test-only-demo-password')
    with pytest.raises(ValueError, match='APP_ENV'):
        seed.validate_environment(True)
    monkeypatch.setenv('APP_ENV', 'demo')
    with pytest.raises(ValueError, match='confirm-demo'):
        seed.validate_environment(False)
    monkeypatch.delenv('NEXUS_DEMO_PASSWORD')
    with pytest.raises(ValueError, match='NEXUS_DEMO_PASSWORD'):
        seed.validate_environment(True)


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Demo seed integration uses PostgreSQL')
def test_demo_seed_is_idempotent_and_does_not_reset_stock():
    seed = load_seed()
    with Session(engine) as db:
        first = seed.seed_demo(db, 'test-only-demo-password')
        assert len(first) == 2
        companies = list(db.scalars(select(Company).where(Company.slug.in_(['aurora-demo', 'horizonte-demo']))))
        ids = [company.id for company in companies]
        for model, expected in [(User, 4), (Product, 6), (Warehouse, 2), (StockBalance, 6), (StockMovement, 6)]:
            assert db.scalar(select(func.count()).select_from(model).where(model.company_id.in_(ids))) == expected
        balance = db.scalar(select(StockBalance).where(StockBalance.company_id == ids[0]))
        balance.quantity -= 1
        balance_id, quantity = balance.id, balance.quantity
        db.commit()
        second = seed.seed_demo(db, 'test-only-demo-password')
        assert first == second
        assert db.get(StockBalance, balance_id).quantity == quantity
        assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.company_id.in_(ids))) == 6
