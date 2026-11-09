"""Run against a disposable PostgreSQL database after `alembic upgrade head`."""
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.company import Company

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Requires PostgreSQL; SQLite is not migration evidence")


def test_postgres_migrations_bootstrap():
    tables = set(inspect(engine).get_table_names())
    assert {"alembic_version", "companies", "sales_orders", "stock_balances", "accounts_receivable"} <= tables
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()


def test_postgres_api_restart_preserves_data():
    slug = f"restart-{uuid4().hex}"
    with TestClient(app) as client:
        assert client.get("/readiness").status_code == 200
        with Session(engine) as db:
            db.add(Company(name="Disposable restart probe", slug=slug))
            db.commit()
    # A new lifespan must leave migrated tables and existing records intact.
    with TestClient(app) as client:
        assert client.get("/readiness").status_code == 200
        with Session(engine) as db:
            company = db.scalar(select(Company).where(Company.slug == slug))
            assert company is not None
            db.delete(company)
            db.commit()
