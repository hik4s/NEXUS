from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_company_access_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/companies/me")
        assert response.status_code == 401


def test_company_access_after_registration() -> None:
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={
                "company_name": f"Company Test {suffix}",
                "company_slug": f"company-test-{suffix}",
                "full_name": "Test Owner",
                "email": f"owner-{suffix}@example.com",
                "password": "StrongPass123!",
            },
        )
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        company_id = registration.json()["user"]["company_id"]

        response = client.get(
            "/api/v1/companies/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == company_id
