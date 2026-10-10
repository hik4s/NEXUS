from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.order import SalesOrder


def register(client, company, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": company,
            "company_slug": company.lower().replace(" ", "-") + uuid4().hex[:6],
            "full_name": "Owner",
            "email": email,
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_product(client, token, company_id, sku="SKU-1"):
    response = client.post(
        f"/api/v1/companies/{company_id}/products",
        headers=auth(token),
        json={"sku": sku, "name": "Notebook", "price": "100.00", "cost": "60.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_pagination_headers_and_sorting():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Pagination Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token))
        company_id = me.json()["company_id"]
        create_product(client, token, company_id, "SKU-B")
        create_product(client, token, company_id, "SKU-A")

        response = client.get(
            f"/api/v1/companies/{company_id}/products",
            headers=auth(token),
            params={"page": 1, "page_size": 1, "sort_by": "sku", "sort_order": "asc"},
        )
        assert response.status_code == 200, response.text
        assert len(response.json()) == 1
        assert response.json()[0]["sku"] == "SKU-A"
        assert response.headers["X-Total-Count"] == "2"
        assert response.headers["X-Page"] == "1"
        assert response.headers["X-Page-Size"] == "1"
        assert response.headers["X-Total-Pages"] == "2"


def test_sales_order_idempotency_replays_same_result_and_rejects_reuse_with_different_payload():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Idempotency Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        product = create_product(client, token, me["company_id"], "SKU-IDEMP")
        key = f"order-{uuid4().hex}"
        payload = {"items": [{"product_id": product["id"], "quantity": 2}]}

        first = client.post("/api/v1/sales/orders", headers={**auth(token), "Idempotency-Key": key}, json=payload)
        assert first.status_code == 201, first.text
        second = client.post("/api/v1/sales/orders", headers={**auth(token), "Idempotency-Key": key}, json=payload)
        assert second.status_code == 201, second.text
        assert second.json()["id"] == first.json()["id"]

        with SessionLocal() as db:
            orders = db.query(SalesOrder).filter(SalesOrder.company_id == UUID(me["company_id"])).all()
            assert len(orders) == 1

        different = client.post(
            "/api/v1/sales/orders",
            headers={**auth(token), "Idempotency-Key": key},
            json={"items": [{"product_id": product["id"], "quantity": 3}]},
        )
        assert different.status_code == 409


def test_api_key_scopes_and_revocation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "API Keys Co", f"owner-{suffix}@example.com")
        created = client.post(
            "/api/v1/platform/api-keys",
            headers=auth(token),
            json={"name": "Automation Worker", "scopes": ["reports:read", "webhooks:dispatch"]},
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["secret"].startswith("nx_live_")
        assert body["key_prefix"] == body["secret"][:16]

        check = client.get(
            "/api/v1/platform/api-keys/validate",
            headers={"X-API-Key": body["secret"]},
            params={"scope": "reports:read"},
        )
        assert check.status_code == 200, check.text
        denied = client.get(
            "/api/v1/platform/api-keys/validate",
            headers={"X-API-Key": body["secret"]},
            params={"scope": "finance:write"},
        )
        assert denied.status_code == 403

        revoked = client.delete(f"/api/v1/platform/api-keys/{body['id']}", headers=auth(token))
        assert revoked.status_code == 200
        after = client.get("/api/v1/platform/api-keys/validate", headers={"X-API-Key": body["secret"]})
        assert after.status_code == 401


def test_webhook_signature_retry_and_dead_letter():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Webhook Co", f"owner-{suffix}@example.com")
        created = client.post(
            "/api/v1/platform/webhooks",
            headers=auth(token),
            json={
                "name": "Operations",
                "url": "https://example.com/nexus",
                "subscribed_events": ["sales.order.created"],
                "max_attempts": 2,
            },
        )
        assert created.status_code == 201, created.text
        endpoint = created.json()
        assert endpoint["secret"].startswith("whsec_")

        event = client.post(
            f"/api/v1/platform/webhooks/{endpoint['id']}/test-event",
            headers=auth(token),
            json={"event_name": "sales.order.created", "payload": {"order_id": "abc"}},
        )
        assert event.status_code == 200, event.text
        delivery = event.json()[0]
        assert delivery["status"] == "pending"
        assert delivery["signature"].startswith("sha256=")

        first_retry = client.post(
            f"/api/v1/platform/webhook-deliveries/{delivery['id']}/retry",
            headers=auth(token),
        )
        assert first_retry.status_code == 200
        assert first_retry.json()["status"] == "pending"
        assert first_retry.json()["attempts"] == 1

        second_retry = client.post(
            f"/api/v1/platform/webhook-deliveries/{delivery['id']}/retry",
            headers=auth(token),
        )
        assert second_retry.status_code == 200
        assert second_retry.json()["status"] == "dead_letter"
        assert second_retry.json()["attempts"] == 2

        mismatch = client.post(
            f"/api/v1/platform/webhooks/{endpoint['id']}/test-event",
            headers=auth(token),
            json={"event_name": "finance.payment.created", "payload": {}},
        )
        assert mismatch.status_code == 409


def test_platform_permissions_are_admin_only_for_api_keys_and_webhooks():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        owner_token = register(client, "Permission Co", f"owner-{suffix}@example.com")
        created_user = client.post(
            "/api/v1/users",
            headers=auth(owner_token),
            json={"full_name": "Manager", "email": f"manager-{suffix}@example.com", "password": "StrongPass123!", "role_keys": ["manager"]},
        )
        assert created_user.status_code == 201, created_user.text
        login = client.post("/api/v1/auth/login", json={"email": f"manager-{suffix}@example.com", "password": "StrongPass123!"})
        manager_token = login.json()["access_token"]

        assert client.post("/api/v1/platform/api-keys", headers=auth(manager_token), json={"name": "Nope"}).status_code == 403
        assert client.post("/api/v1/platform/webhooks", headers=auth(manager_token), json={"name": "Nope", "url": "https://example.com", "subscribed_events": ["x"]}).status_code == 403
