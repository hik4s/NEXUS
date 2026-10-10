from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client: TestClient, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"RBAC Company {suffix}",
            "company_slug": f"rbac-company-{suffix}",
            "full_name": "Admin User",
            "email": f"admin-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_refresh_token_and_role_based_permissions():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_token = owner["access_token"]
        headers = {"Authorization": f"Bearer {owner_token}"}
        company_id = owner["user"]["company_id"]

        refreshed = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": owner["refresh_token"]},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["access_token"]

        user_response = client.post(
            "/api/v1/users",
            headers=headers,
            json={
                "full_name": "Employee User",
                "email": f"employee-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["employee"],
            },
        )
        assert user_response.status_code == 201, user_response.text
        employee_id = user_response.json()["id"]
        assert user_response.json()["roles"] == ["employee"]

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"employee-{suffix}@example.com",
                "password": "StrongPass123!",
            },
        )
        assert login.status_code == 200
        employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        roles = client.get("/api/v1/users/roles", headers=employee_headers)
        assert roles.status_code == 403

        users = client.get("/api/v1/users", headers=employee_headers)
        assert users.status_code == 403

        company = client.get("/api/v1/companies/me", headers=employee_headers)
        assert company.status_code == 200

        product = client.post(
            f"/api/v1/companies/{company_id}/products",
            headers=employee_headers,
            json={
                "name": "Employee Product",
                "sku": f"EMP-{suffix}",
                "price": "10.00",
                "cost": "5.00",
            },
        )
        assert product.status_code == 403

        owner_users = client.get("/api/v1/users", headers=headers)
        assert owner_users.status_code == 200
        assert any(user["id"] == employee_id for user in owner_users.json())

        audit = client.get("/api/v1/audit-logs", headers=headers)
        assert audit.status_code == 200
        actions = {item["action"] for item in audit.json()}
        assert "auth.register" in actions
        assert "auth.login" in actions
        assert "user.created" in actions


def test_tenant_isolation_for_users():
    first = uuid4().hex[:8]
    second = uuid4().hex[:8]
    with TestClient(app) as client:
        one = register(client, first)
        two = register(client, second)
        target_id = one["user"]["id"]
        headers = {"Authorization": f"Bearer {two['access_token']}"}

        response = client.patch(
            f"/api/v1/users/{target_id}",
            headers=headers,
            json={"full_name": "Should Not Work"},
        )
        assert response.status_code == 404


def test_manager_cannot_assign_elevated_roles_or_remove_last_admin():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        owner_headers = {"Authorization": f"Bearer {owner['access_token']}"}

        manager = client.post(
            "/api/v1/users",
            headers=owner_headers,
            json={
                "full_name": "Manager User",
                "email": f"manager-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["manager"],
            },
        )
        assert manager.status_code == 201, manager.text

        manager_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"manager-{suffix}@example.com",
                "password": "StrongPass123!",
            },
        )
        assert manager_login.status_code == 200
        manager_headers = {"Authorization": f"Bearer {manager_login.json()['access_token']}"}

        elevated = client.post(
            "/api/v1/users",
            headers=manager_headers,
            json={
                "full_name": "Elevated User",
                "email": f"elevated-{suffix}@example.com",
                "password": "StrongPass123!",
                "role_keys": ["admin"],
            },
        )
        assert elevated.status_code == 403

        deactivate_owner = client.patch(
            f"/api/v1/users/{owner['user']['id']}",
            headers=manager_headers,
            json={"is_active": False},
        )
        assert deactivate_owner.status_code == 403

        self_deactivate = client.patch(
            f"/api/v1/users/{manager.json()['id']}",
            headers=manager_headers,
            json={"is_active": False},
        )
        assert self_deactivate.status_code == 400
