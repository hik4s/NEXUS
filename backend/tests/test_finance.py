from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Finance Company {suffix}",
            "company_slug": f"finance-company-{suffix}",
            "full_name": "Finance Admin",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(client, headers, company_id, sku, price="100.00", cost="50.00"):
    response = client.post(
        f"/api/v1/companies/{company_id}/products",
        headers=headers,
        json={"name": f"Product {sku}", "sku": sku, "price": price, "cost": cost},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_warehouse(client, headers, suffix):
    response = client.post(
        "/api/v1/inventory/warehouses",
        headers=headers,
        json={"name": f"Finance Warehouse {suffix}", "code": f"FIN-{suffix}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_account(client, headers, name="Main Account", opening="100.00"):
    response = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": name, "account_type": "bank", "opening_balance": opening},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_financial_account_and_manual_transactions_update_balance():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        account = create_account(client, headers)

        income = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "account_id": account["id"],
                "transaction_type": "income",
                "amount": "50.00",
                "description": "Other income",
            },
        )
        assert income.status_code == 201, income.text

        expense = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "account_id": account["id"],
                "transaction_type": "expense",
                "amount": "30.00",
                "description": "Office expense",
            },
        )
        assert expense.status_code == 201, expense.text

        accounts = client.get("/api/v1/finance/accounts", headers=headers)
        assert accounts.status_code == 200
        assert accounts.json()[0]["current_balance"] == "120.00"


def test_confirmed_sale_creates_receivable_and_partial_payment():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        account = create_account(client, headers, opening="0.00")
        product = create_product(client, headers, company_id, f"SKU-{suffix}")
        warehouse = create_warehouse(client, headers, suffix)

        receipt = client.post(
            "/api/v1/inventory/movements",
            headers=headers,
            json={
                "warehouse_id": warehouse["id"],
                "product_id": product["id"],
                "movement_type": "receipt",
                "quantity": 2,
            },
        )
        assert receipt.status_code == 201

        order = client.post(
            "/api/v1/sales/orders",
            headers=headers,
            json={"items": [{"product_id": product["id"], "quantity": 2}]},
        )
        assert order.status_code == 201
        confirmed = client.patch(
            f"/api/v1/sales/orders/{order.json()['id']}/status",
            headers=headers,
            json={"status": "confirmed", "warehouse_id": warehouse["id"], "payment_terms_days": 7},
        )
        assert confirmed.status_code == 200

        receivables = client.get("/api/v1/finance/receivables", headers=headers)
        assert receivables.status_code == 200
        assert len(receivables.json()) == 1
        receivable = receivables.json()[0]
        assert receivable["amount"] == "200.00"
        assert receivable["status"] == "pending"

        partial = client.post(
            f"/api/v1/finance/receivables/{receivable['id']}/pay",
            headers=headers,
            json={"account_id": account["id"], "amount": "80.00"},
        )
        assert partial.status_code == 200
        assert partial.json()["status"] == "partially_paid"
        assert partial.json()["paid_amount"] == "80.00"

        full = client.post(
            f"/api/v1/finance/receivables/{receivable['id']}/pay",
            headers=headers,
            json={"account_id": account["id"]},
        )
        assert full.status_code == 200
        assert full.json()["status"] == "paid"

        accounts = client.get("/api/v1/finance/accounts", headers=headers)
        assert accounts.json()[0]["current_balance"] == "200.00"

        duplicate = client.post(
            f"/api/v1/finance/receivables/{receivable['id']}/pay",
            headers=headers,
            json={"account_id": account["id"], "amount": "1.00"},
        )
        assert duplicate.status_code == 409


def test_purchase_receipt_creates_payable_and_payment_reduces_cash():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}
        company_id = owner["user"]["company_id"]
        account = create_account(client, headers, opening="150.00")
        product = create_product(client, headers, company_id, f"SKU-{suffix}", cost="25.00")
        warehouse = create_warehouse(client, headers, suffix)
        supplier_response = client.post(
            "/api/v1/procurement/suppliers",
            headers=headers,
            json={"name": "Supplier Finance", "payment_terms_days": 10},
        )
        assert supplier_response.status_code == 201
        supplier = supplier_response.json()
        po = client.post(
            "/api/v1/procurement/purchase-orders",
            headers=headers,
            json={
                "supplier_id": supplier["id"],
                "warehouse_id": warehouse["id"],
                "items": [{"product_id": product["id"], "quantity": 4, "unit_cost": "25.00"}],
            },
        )
        assert po.status_code == 201
        po_id = po.json()["id"]
        for next_status in ("submitted", "approved"):
            response = client.patch(
                f"/api/v1/procurement/purchase-orders/{po_id}/status",
                headers=headers,
                json={"status": next_status},
            )
            assert response.status_code == 200

        receipt = client.post(
            f"/api/v1/procurement/purchase-orders/{po_id}/receipts",
            headers=headers,
            json={"items": [{"purchase_order_item_id": po.json()["items"][0]["id"], "quantity": 4}]},
        )
        assert receipt.status_code == 201, receipt.text

        payables = client.get("/api/v1/finance/payables", headers=headers)
        assert payables.status_code == 200
        assert len(payables.json()) == 1
        payable = payables.json()[0]
        assert payable["amount"] == "100.00"
        assert payable["status"] == "pending"

        paid = client.post(
            f"/api/v1/finance/payables/{payable['id']}/pay",
            headers=headers,
            json={"account_id": account["id"], "amount": "100.00"},
        )
        assert paid.status_code == 200
        assert paid.json()["status"] == "paid"

        accounts = client.get("/api/v1/finance/accounts", headers=headers)
        assert accounts.json()[0]["current_balance"] == "50.00"


def test_manager_can_read_finance_but_cannot_pay():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        created = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "full_name": "Finance Manager",
                "email": f"manager-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["manager"],
            },
        )
        assert created.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={"email": f"manager-{suffix}@example.com", "password": "StrongPass123!"},
        )
        manager_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        accounts = client.get("/api/v1/finance/accounts", headers=manager_headers)
        assert accounts.status_code == 200
        blocked = client.post(
            "/api/v1/finance/receivables/00000000-0000-0000-0000-000000000000/pay",
            headers=manager_headers,
            json={"account_id": "00000000-0000-0000-0000-000000000000", "amount": "1.00"},
        )
        assert blocked.status_code == 403


def test_finance_is_tenant_scoped():
    first_suffix = uuid4().hex[:8]
    second_suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        first = register(client, first_suffix)
        second = register(client, second_suffix)
        first_headers = {"Authorization": f"Bearer {first['access_token']}"}
        second_headers = {"Authorization": f"Bearer {second['access_token']}"}
        account = create_account(client, first_headers)
        transactions = client.get("/api/v1/finance/transactions", headers=second_headers)
        assert transactions.status_code == 200
        assert transactions.json() == []
        foreign_payment = client.post(
            "/api/v1/finance/receivables/00000000-0000-0000-0000-000000000000/pay",
            headers=second_headers,
            json={"account_id": account["id"], "amount": "10.00"},
        )
        assert foreign_payment.status_code in {403, 404}
