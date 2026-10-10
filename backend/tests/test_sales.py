from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Sales Company {suffix}",
            "company_slug": f"sales-company-{suffix}",
            "full_name": "Sales Admin",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client: TestClient, headers: dict[str, str], company_id: str, sku: str, price: str = "100.00"):
    response = client.post(
        f"/api/v1/companies/{company_id}/products",
        headers=headers,
        json={"name": f"Product {sku}", "sku": sku, "price": price, "cost": "50.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_sales_order_creation_totals_and_status_flow():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        product = create_product(client, headers, owner["user"]["company_id"], f"SKU-{suffix}")
        warehouse = client.post(
            "/api/v1/inventory/warehouses",
            headers=headers,
            json={"name": "Sales Warehouse", "code": f"SALE-{suffix}"},
        )
        assert warehouse.status_code == 201
        receipt = client.post(
            "/api/v1/inventory/movements",
            headers=headers,
            json={
                "warehouse_id": warehouse.json()["id"],
                "product_id": product["id"],
                "movement_type": "receipt",
                "quantity": 2,
            },
        )
        assert receipt.status_code == 201, receipt.text
        customer = client.post(
            "/api/v1/crm/customers",
            headers=headers,
            json={"name": "Sales Customer", "email": f"customer-{suffix}@example.com"},
        )
        assert customer.status_code == 201

        order = client.post(
            "/api/v1/sales/orders",
            headers=headers,
            json={
                "customer_id": customer.json()["id"],
                "order_discount": "20.00",
                "items": [
                    {"product_id": product["id"], "quantity": 2, "line_discount": "10.00"}
                ],
            },
        )
        assert order.status_code == 201, order.text
        body = order.json()
        assert body["status"] == "draft"
        assert body["subtotal"] == "200.00"
        assert body["item_discount_total"] == "10.00"
        assert body["order_discount"] == "20.00"
        assert body["total"] == "170.00"
        assert body["items"][0]["total"] == "190.00"

        confirmed = client.patch(
            f"/api/v1/sales/orders/{body['id']}/status",
            headers=headers,
            json={"status": "confirmed", "warehouse_id": warehouse.json()["id"]},
        )
        assert confirmed.status_code == 200, confirmed.text
        assert confirmed.json()["status"] == "confirmed"

        invalid = client.patch(
            f"/api/v1/sales/orders/{body['id']}/status",
            headers=headers,
            json={"status": "draft"},
        )
        assert invalid.status_code == 409


def test_employee_cannot_apply_discount_or_price_override():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        product = create_product(client, owner_headers, company_id, f"SKU-{suffix}")

        created_user = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "full_name": "Sales Employee",
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

        discount = client.post(
            "/api/v1/sales/orders",
            headers=employee_headers,
            json={
                "order_discount": "10.00",
                "items": [{"product_id": product["id"], "quantity": 1}],
            },
        )
        assert discount.status_code == 403

        override = client.post(
            "/api/v1/sales/orders",
            headers=employee_headers,
            json={
                "items": [{"product_id": product["id"], "quantity": 1, "unit_price": "80.00"}],
            },
        )
        assert override.status_code == 403


def test_sales_order_tenant_isolation():
    first = uuid4().hex[:8]
    second = uuid4().hex[:8]
    with TestClient(app) as client:
        one = register(client, first)
        two = register(client, second)
        one_headers = {"Authorization": f"Bearer {one['access_token']}"}
        two_headers = {"Authorization": f"Bearer {two['access_token']}"}
        product = create_product(client, one_headers, one["user"]["company_id"], f"SKU-{first}")
        order = client.post(
            "/api/v1/sales/orders",
            headers=one_headers,
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )
        assert order.status_code == 201
        order_id = order.json()["id"]

        get_other = client.get(f"/api/v1/sales/orders/{order_id}", headers=two_headers)
        assert get_other.status_code == 404

        foreign_product = client.post(
            "/api/v1/sales/orders",
            headers=two_headers,
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )
        assert foreign_product.status_code == 404
