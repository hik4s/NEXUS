from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"CRM Company {suffix}",
            "company_slug": f"crm-company-{suffix}",
            "full_name": "Admin User",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_customer_lead_and_interaction_flow():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = {"Authorization": f"Bearer {owner['access_token']}"}

        customer = client.post(
            "/api/v1/crm/customers",
            headers=headers,
            json={
                "name": "Acme Corporation",
                "email": f"contact-{suffix}@acme.example",
                "phone": "18999990000",
                "source": "website",
            },
        )
        assert customer.status_code == 201, customer.text
        customer_id = customer.json()["id"]

        duplicate = client.post(
            "/api/v1/crm/customers",
            headers=headers,
            json={"name": "Duplicate", "email": f"contact-{suffix}@acme.example"},
        )
        assert duplicate.status_code == 409

        lead = client.post(
            "/api/v1/crm/leads",
            headers=headers,
            json={
                "name": "Acme Expansion",
                "customer_id": customer_id,
                "source": "referral",
                "expected_value": "12500.00",
            },
        )
        assert lead.status_code == 201, lead.text
        lead_id = lead.json()["id"]

        update = client.patch(
            f"/api/v1/crm/leads/{lead_id}",
            headers=headers,
            json={"status": "qualified", "expected_value": "14000.00"},
        )
        assert update.status_code == 200
        assert update.json()["status"] == "qualified"

        interaction = client.post(
            "/api/v1/crm/interactions",
            headers=headers,
            json={
                "customer_id": customer_id,
                "type": "call",
                "channel": "phone",
                "subject": "Discovery call",
                "content": "Client confirmed interest in expansion.",
            },
        )
        assert interaction.status_code == 201, interaction.text

        interactions = client.get(
            f"/api/v1/crm/interactions?customer_id={customer_id}", headers=headers
        )
        assert interactions.status_code == 200
        assert len(interactions.json()) == 1

        logs = client.get("/api/v1/audit-logs", headers=headers)
        actions = {item["action"] for item in logs.json()}
        assert {"customer.created", "lead.created", "lead.updated", "interaction.created"}.issubset(actions)


def test_crm_tenant_isolation():
    first = uuid4().hex[:8]
    second = uuid4().hex[:8]
    with TestClient(app) as client:
        one = register(client, first)
        two = register(client, second)
        one_headers = {"Authorization": f"Bearer {one['access_token']}"}
        two_headers = {"Authorization": f"Bearer {two['access_token']}"}

        customer = client.post(
            "/api/v1/crm/customers",
            headers=one_headers,
            json={"name": "Private Customer", "email": f"private-{first}@example.com"},
        )
        assert customer.status_code == 201
        customer_id = customer.json()["id"]

        get_other = client.get(f"/api/v1/crm/customers/{customer_id}", headers=two_headers)
        assert get_other.status_code == 404

        interaction = client.post(
            "/api/v1/crm/interactions",
            headers=two_headers,
            json={
                "customer_id": customer_id,
                "content": "Cross-tenant access attempt",
            },
        )
        assert interaction.status_code == 400


def test_employee_has_crm_access_but_only_inside_company():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}
        employee = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "full_name": "Sales Employee",
                "email": f"employee-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["employee"],
            },
        )
        assert employee.status_code == 201
        login = client.post(
            "/api/v1/auth/login",
            json={"email": f"employee-{suffix}@example.com", "password": "StrongPass123!"},
        )
        employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        customer = client.post(
            "/api/v1/crm/customers",
            headers=employee_headers,
            json={"name": "Employee Customer", "email": f"employee-{suffix}@example.com"},
        )
        assert customer.status_code == 201
        lead = client.post(
            "/api/v1/crm/leads",
            headers=employee_headers,
            json={"name": "Employee Lead", "source": "whatsapp"},
        )
        assert lead.status_code == 201
