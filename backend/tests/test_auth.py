from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_register_login_and_me():
    suffix = uuid4().hex[:8]
    email = f"kauan-{suffix}@example.com"
    slug = f"nexus-demo-{suffix}"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "company_name": f"NEXUS Demo {suffix}",
                "company_slug": slug,
                "full_name": "Kauan Demo",
                "email": email,
                "password": "StrongPass123!",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["token_type"] == "bearer"
        token = body["access_token"]
        assert body["user"]["role"] == "admin"

        me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == email

        company = client.get("/api/v1/companies/me", headers={"Authorization": f"Bearer {token}"})
        assert company.status_code == 200
        assert company.json()["slug"] == slug

        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "StrongPass123!"},
        )
        assert login.status_code == 200


def test_auth_required_for_me():
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
