from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Procurement Company {suffix}",
            "company_slug": f"procurement-company-{suffix}",
            "full_name": "Procurement Admin",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client: TestClient, headers: dict[str, str], company_id: str, sku: str, cost: str = "25.00"):
    response = client.post(
        f"/api/v1/companies/{company_id}/products",
        headers=headers,
        json={"name": f"Product {sku}", "sku": sku, "price": "50.00", "cost": cost},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_warehouse(client: TestClient, headers: dict[str, str], suffix: str):
    response = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": f"Main {suffix}", "code": f"MAIN-{suffix}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_supplier_and_supplier_product_catalog_are_tenant_scoped():
    first_suffix = uuid4().hex[:8]
    second_suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        first = register(client, first_suffix)
        second = register(client, second_suffix)
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        product = create_product(client, first_headers, first["user"]["company_id"], f"SKU-{first_suffix}")

        supplier = client.post(
            "/api/v1/procurement/suppliers",
            headers=first_headers,
            json={"name": "Fornecedor Alpha", "payment_terms_days": 30},
        )
        assert supplier.status_code == 201, supplier.text
        supplier_id = supplier.json()["id"]

        mapping = client.put(
            f"/api/v1/procurement/suppliers/{supplier_id}/products",
            headers=first_headers,
            json={"product_id": product["id"], "last_unit_cost": "24.50", "minimum_order_quantity": 5, "lead_time_days": 7, "is_preferred": True},
        )
        assert mapping.status_code == 200, mapping.text
        assert mapping.json()["last_unit_cost"] == "24.50"

        foreign = client.get(
            f"/api/v1/procurement/suppliers/{supplier_id}/products",
            headers=second_headers,
        )
        assert foreign.status_code == 200
        assert foreign.json() == []


def test_purchase_order_uses_supplier_cost_and_controls_status_flow():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, headers, company_id, f"SKU-{suffix}", cost="30.00")
        warehouse = create_warehouse(client, headers, suffix)
        supplier = client.post(
            "/api/v1/procurement/suppliers",
            headers=headers,
            json={"name": "Fornecedor Beta"},
        )
        assert supplier.status_code == 201
        supplier_id = supplier.json()["id"]

        configured = client.put(
            f"/api/v1/procurement/suppliers/{supplier_id}/products",
            headers=headers,
            json={"product_id": product["id"], "last_unit_cost": "28.50"},
        )
        assert configured.status_code == 200

        order = client.post(
            "/api/v1/procurement/purchase-orders",
            headers=headers,
            json={
                "supplier_id": supplier_id,
                "warehouse_id": warehouse["id"],
                "discount": "5.00",
                "items": [{"product_id": product["id"], "quantity": 10}],
            },
        )
        assert order.status_code == 201, order.text
        body = order.json()
        assert body["status"] == "draft"
        assert body["subtotal"] == "285.00"
        assert body["discount"] == "5.00"
        assert body["total"] == "280.00"
        assert body["items"][0]["unit_cost"] == "28.50"

        submitted = client.patch(
            f"/api/v1/procurement/purchase-orders/{body['id']}/status",
            headers=headers,
            json={"status": "submitted"},
        )
        assert submitted.status_code == 200

        approved = client.patch(
            f"/api/v1/procurement/purchase-orders/{body['id']}/status",
            headers=headers,
            json={"status": "approved"},
        )
        assert approved.status_code == 200

        invalid = client.patch(
            f"/api/v1/procurement/purchase-orders/{body['id']}/status",
            headers=headers,
            json={"status": "draft"},
        )
        assert invalid.status_code == 409


def test_partial_and_full_receiving_updates_inventory_and_reference_cost():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, headers, company_id, f"SKU-{suffix}", cost="30.00")
        warehouse = create_warehouse(client, headers, suffix)
        supplier = client.post(
            "/api/v1/procurement/suppliers",
            headers=headers,
            json={"name": "Fornecedor Gamma"},
        )
        assert supplier.status_code == 201
        supplier_id = supplier.json()["id"]

        order = client.post(
            "/api/v1/procurement/purchase-orders",
            headers=headers,
            json={
                "supplier_id": supplier_id,
                "warehouse_id": warehouse["id"],
                "items": [{"product_id": product["id"], "quantity": 10, "unit_cost": "27.50"}],
            },
        )
        assert order.status_code == 201
        order_id = order.json()["id"]
        item_id = order.json()["items"][0]["id"]

        approved = client.patch(
            f"/api/v1/procurement/purchase-orders/{order_id}/status",
            headers=headers,
            json={"status": "submitted"},
        )
        assert approved.status_code == 200
        approved = client.patch(
            f"/api/v1/procurement/purchase-orders/{order_id}/status",
            headers=headers,
            json={"status": "approved"},
        )
        assert approved.status_code == 200

        first_receipt = client.post(
            f"/api/v1/procurement/purchase-orders/{order_id}/receipts",
            headers=headers,
            json={"items": [{"purchase_order_item_id": item_id, "quantity": 6}]},
        )
        assert first_receipt.status_code == 201, first_receipt.text

        fetched = client.get(f"/api/v1/procurement/purchase-orders/{order_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "partially_received"
        assert fetched.json()["items"][0]["quantity_received"] == 6

        stock = client.get(
            "/api/v1/inventory/stock",
            headers=headers,
            params={"warehouse_id": warehouse["id"], "product_id": product["id"]},
        )
        assert stock.status_code == 200
        assert stock.json()[0]["quantity"] == 6

        second_receipt = client.post(
            f"/api/v1/procurement/purchase-orders/{order_id}/receipts",
            headers=headers,
            json={"items": [{"purchase_order_item_id": item_id, "quantity": 4, "unit_cost": "28.00"}]},
        )
        assert second_receipt.status_code == 201, second_receipt.text

        fetched = client.get(f"/api/v1/procurement/purchase-orders/{order_id}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "received"
        assert fetched.json()["items"][0]["quantity_received"] == 10

        stock = client.get(
            "/api/v1/inventory/stock",
            headers=headers,
            params={"warehouse_id": warehouse["id"], "product_id": product["id"]},
        )
        assert stock.json()[0]["quantity"] == 10

        products = client.get(
            f"/api/v1/companies/{company_id}/products",
            headers=headers,
        )
        assert products.status_code == 200
        current = next(item for item in products.json() if item["id"] == product["id"])
        assert Decimal(current["cost"]) == Decimal("28.00")


def test_receiving_more_than_ordered_is_rejected_without_changing_status():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, headers, company_id, f"SKU-{suffix}")
        warehouse = create_warehouse(client, headers, suffix)
        supplier = client.post(
            "/api/v1/procurement/suppliers",
            headers=headers,
            json={"name": "Fornecedor Delta"},
        ).json()

        order = client.post(
            "/api/v1/procurement/purchase-orders",
            headers=headers,
            json={
                "supplier_id": supplier["id"],
                "warehouse_id": warehouse["id"],
                "items": [{"product_id": product["id"], "quantity": 5}],
            },
        ).json()
        item_id = order["items"][0]["id"]

        for next_status in ("submitted", "approved"):
            response = client.patch(
                f"/api/v1/procurement/purchase-orders/{order['id']}/status",
                headers=headers,
                json={"status": next_status},
            )
            assert response.status_code == 200

        receipt = client.post(
            f"/api/v1/procurement/purchase-orders/{order['id']}/receipts",
            headers=headers,
            json={"items": [{"purchase_order_item_id": item_id, "quantity": 6}]},
        )
        assert receipt.status_code == 409

        fetched = client.get(f"/api/v1/procurement/purchase-orders/{order['id']}", headers=headers)
        assert fetched.json()["status"] == "approved"
        assert fetched.json()["items"][0]["quantity_received"] == 0


def test_employee_cannot_manage_procurement():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        created_user = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "full_name": "Operational Employee",
                "email": f"employee-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["employee"],
            },
        )
        assert created_user.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={"email": f"employee-{suffix}@example.com", "password": "StrongPass123!"},
        )
        employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        suppliers = client.get("/api/v1/procurement/suppliers", headers=employee_headers)
        assert suppliers.status_code == 403
        create_supplier_response = client.post(
            "/api/v1/procurement/suppliers",
            headers=employee_headers,
            json={"name": "Blocked Supplier"},
        )
        assert create_supplier_response.status_code == 403
