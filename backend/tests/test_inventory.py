from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Inventory Company {suffix}",
            "company_slug": f"inventory-company-{suffix}",
            "full_name": "Inventory Admin",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client: TestClient, headers: dict[str, str], company_id: str, sku: str):
    response = client.post(
        f"/api/v1/companies/{company_id}/products",
        headers=headers,
        json={"name": f"Product {sku}", "sku": sku, "price": "100.00", "cost": "50.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_warehouse(client: TestClient, headers: dict[str, str], name: str, code: str):
    response = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": name, "code": code},
    )
    assert response.status_code == 201, response.text
    return response.json()


def movement(client, headers, warehouse_id, product_id, movement_type, quantity):
    response = client.post(
        "/api/v1/inventory/movements",
        headers=headers,
        json={
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "movement_type": movement_type,
            "quantity": quantity,
        },
    )
    return response


def stock_for(client, headers, warehouse_id, product_id):
    response = client.get(
        "/api/v1/inventory/stock",
        headers=headers,
        params={"warehouse_id": warehouse_id, "product_id": product_id},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body[0]["quantity"] if body else 0


def test_warehouse_receipt_and_issue_update_balance():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        product = create_product(client, headers, owner["user"]["company_id"], f"SKU-{suffix}")
        warehouse = create_warehouse(client, headers, "Main Warehouse", f"MAIN-{suffix}")

        receipt = movement(client, headers, warehouse["id"], product["id"], "receipt", 10)
        assert receipt.status_code == 201, receipt.text
        assert receipt.json()["balance_after"] == 10
        assert stock_for(client, headers, warehouse["id"], product["id"]) == 10

        issue = movement(client, headers, warehouse["id"], product["id"], "issue", 3)
        assert issue.status_code == 201, issue.text
        assert issue.json()["balance_after"] == 7
        assert stock_for(client, headers, warehouse["id"], product["id"]) == 7

        insufficient = movement(client, headers, warehouse["id"], product["id"], "issue", 8)
        assert insufficient.status_code == 409
        assert stock_for(client, headers, warehouse["id"], product["id"]) == 7


def test_transfer_moves_stock_between_warehouses():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        product = create_product(client, headers, owner["user"]["company_id"], f"SKU-{suffix}")
        source = create_warehouse(client, headers, "Source", f"SRC-{suffix}")
        destination = create_warehouse(client, headers, "Destination", f"DST-{suffix}")
        assert movement(client, headers, source["id"], product["id"], "receipt", 12).status_code == 201

        transfer = client.post(
            "/api/v1/inventory/transfers",
            headers=headers,
            json={
                "source_warehouse_id": source["id"],
                "destination_warehouse_id": destination["id"],
                "product_id": product["id"],
                "quantity": 5,
            },
        )
        assert transfer.status_code == 201, transfer.text
        assert stock_for(client, headers, source["id"], product["id"]) == 7
        assert stock_for(client, headers, destination["id"], product["id"]) == 5


def test_sales_confirmation_consumes_stock_and_cancellation_returns_it():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, headers, company_id, f"SKU-{suffix}")
        warehouse = create_warehouse(client, headers, "Sales Warehouse", f"SALE-{suffix}")
        assert movement(client, headers, warehouse["id"], product["id"], "receipt", 8).status_code == 201

        order = client.post(
            "/api/v1/sales/orders",
            headers=headers,
            json={"items": [{"product_id": product["id"], "quantity": 3}]},
        )
        assert order.status_code == 201, order.text

        confirmed = client.patch(
            f"/api/v1/sales/orders/{order.json()['id']}/status",
            headers=headers,
            json={"status": "confirmed", "warehouse_id": warehouse["id"]},
        )
        assert confirmed.status_code == 200, confirmed.text
        body = confirmed.json()
        assert body["status"] == "confirmed"
        assert body["fulfillment"]["warehouse_id"] == warehouse["id"]
        assert stock_for(client, headers, warehouse["id"], product["id"]) == 5

        cancelled = client.patch(
            f"/api/v1/sales/orders/{order.json()['id']}/status",
            headers=headers,
            json={"status": "cancelled"},
        )
        assert cancelled.status_code == 200, cancelled.text
        assert cancelled.json()["fulfillment"]["status"] == "reversed"
        assert stock_for(client, headers, warehouse["id"], product["id"]) == 8


def test_sales_confirmation_requires_stock_and_does_not_confirm_order():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, headers, company_id, f"SKU-{suffix}")
        warehouse = create_warehouse(client, headers, "Sales Warehouse", f"SALE-{suffix}")

        order = client.post(
            "/api/v1/sales/orders",
            headers=headers,
            json={"items": [{"product_id": product["id"], "quantity": 2}]},
        )
        assert order.status_code == 201

        confirmed = client.patch(
            f"/api/v1/sales/orders/{order.json()['id']}/status",
            headers=headers,
            json={"status": "confirmed", "warehouse_id": warehouse["id"]},
        )
        assert confirmed.status_code == 409

        fetched = client.get(f"/api/v1/sales/orders/{order.json()['id']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "draft"


def test_inventory_is_tenant_scoped():
    first_suffix = uuid4().hex[:8]
    second_suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        first = register(client, first_suffix)
        second = register(client, second_suffix)
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        product = create_product(client, first_headers, first["user"]["company_id"], f"SKU-{first_suffix}")
        warehouse = create_warehouse(client, first_headers, "Private", f"PRV-{first_suffix}")
        assert movement(client, first_headers, warehouse["id"], product["id"], "receipt", 5).status_code == 201

        cross_stock = client.get(
            "/api/v1/inventory/stock",
            headers=second_headers,
            params={"warehouse_id": warehouse["id"]},
        )
        assert cross_stock.status_code == 200
        assert cross_stock.json() == []

        cross_transfer = client.post(
            "/api/v1/inventory/transfers",
            headers=second_headers,
            json={
                "source_warehouse_id": warehouse["id"],
                "destination_warehouse_id": warehouse["id"],
                "product_id": product["id"],
                "quantity": 1,
            },
        )
        assert cross_transfer.status_code == 400
