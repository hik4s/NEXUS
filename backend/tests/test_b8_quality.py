import threading
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.company import Company
from app.models.inventory import StockBalance, StockMovement, Warehouse
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_owner
from app.services.inventory_service import create_movement


def _owner():
    db = SessionLocal()
    payload = RegisterRequest(
        company_name=f"B8-{uuid.uuid4().hex[:8]}",
        company_slug=f"b8-{uuid.uuid4().hex[:12]}",
        full_name="B8 Owner",
        email=f"{uuid.uuid4().hex[:12]}@example.com",
        password="StrongPass123!",
    )
    user, _, _ = register_owner(db, payload)
    db.close()
    return payload, user


def _auth():
    payload, _ = _owner()
    client = TestClient(app)
    token = client.post("/api/v1/auth/login", json={"email": str(payload.email), "password": payload.password}).json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_security_headers_and_request_id():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_request_body_limit_rejects_oversized_header():
    client = TestClient(app)
    response = client.post("/api/v1/health", headers={"Content-Length": str(30 * 1024 * 1024)})
    assert response.status_code == 413
    assert response.json()["detail"] == "Request body too large"


def test_readiness_and_metrics_are_exposed():
    client = TestClient(app)
    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    metrics = client.get("/api/v1/health/metrics")
    assert metrics.status_code == 200
    assert "nexus_http_requests_total" in metrics.text


def test_invalid_xlsx_payload_is_rejected():
    client, headers = _auth()
    response = client.post(
        "/api/v1/integrations/files",
        files={"file": ("malicious.xlsx", b"not-a-zip", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert response.status_code == 422


def test_security_settings_reject_insecure_production_secret(monkeypatch):
    from app.core import security_config
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", "nexus-dev-secret-key-change-before-production-please")
    try:
        security_config.validate_security_configuration()
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("production must reject the development secret")


def test_concurrent_receipts_preserve_stock_total():
    db = SessionLocal()
    payload, actor = _owner()
    company = db.get(Company, actor.company_id)
    warehouse = Warehouse(company_id=company.id, name="B8 Warehouse", code=f"B8-{uuid.uuid4().hex[:6].upper()}")
    product = Product(company_id=company.id, name="Concurrency Product", sku=f"SKU-{uuid.uuid4().hex[:8]}", price=10)
    db.add_all([warehouse, product]); db.commit(); db.refresh(warehouse); db.refresh(product)
    db.close()

    errors = []
    def worker():
        session = SessionLocal()
        try:
            movement = type("P", (), {"warehouse_id": warehouse.id, "product_id": product.id, "movement_type": "receipt", "quantity": 1, "notes": "concurrency"})()
            create_movement(session, actor, movement)
        except Exception as exc:
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    check = SessionLocal()
    balance = check.scalar(select(StockBalance).where(StockBalance.warehouse_id == warehouse.id, StockBalance.product_id == product.id))
    movements = check.scalars(select(StockMovement).where(StockMovement.warehouse_id == warehouse.id, StockMovement.product_id == product.id)).all()
    check.close()
    assert not errors or all("database is locked" in str(exc).lower() for exc in errors)
    assert balance is not None
    assert balance.quantity == len(movements)
