from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client, company, email):
    r = client.post(
        "/api/v1/auth/register",
        json={"company_name": company, "company_slug": company.lower().replace(" ", "-") + uuid4().hex[:4], "full_name": "Owner", "email": email, "password": "StrongPass123!"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_intelligence_chat_uses_controlled_tool_and_stores_call():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "AI Chat Co", f"owner-{suffix}@example.com")
        created = client.post("/api/v1/intelligence/conversations", headers=auth(token), json={"title": "Operations"})
        assert created.status_code == 201, created.text
        conversation_id = created.json()["id"]

        message = client.post(
            f"/api/v1/intelligence/conversations/{conversation_id}/messages",
            headers=auth(token),
            json={"content": "Como estão minhas vendas?"},
        )
        assert message.status_code == 200, message.text
        body = message.json()
        assert body["role"] == "assistant"
        assert body["provider"] == "mock"
        assert body["metadata_json"]["tool_calls"] == 1

        conversation = client.get(f"/api/v1/intelligence/conversations/{conversation_id}", headers=auth(token))
        assert conversation.status_code == 200
        assert [m["role"] for m in conversation.json()["messages"]] == ["user", "assistant"]


def test_intelligence_action_requires_approval_and_executes_workflow_task():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "AI Actions Co", f"owner-{suffix}@example.com")
        created = client.post("/api/v1/intelligence/conversations", headers=auth(token), json={})
        cid = created.json()["id"]

        message = client.post(
            f"/api/v1/intelligence/conversations/{cid}/messages",
            headers=auth(token),
            json={"content": "Crie uma tarefa para revisar o estoque"},
        )
        assert message.status_code == 200, message.text

        proposals = client.get("/api/v1/intelligence/action-proposals", headers=auth(token))
        assert proposals.status_code == 200
        assert len(proposals.json()) == 1
        proposal = proposals.json()[0]
        assert proposal["status"] == "pending"

        before = client.post(f"/api/v1/intelligence/action-proposals/{proposal['id']}/execute", headers=auth(token))
        assert before.status_code == 409

        approved = client.post(f"/api/v1/intelligence/action-proposals/{proposal['id']}/approve", headers=auth(token))
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        executed = client.post(f"/api/v1/intelligence/action-proposals/{proposal['id']}/execute", headers=auth(token))
        assert executed.status_code == 200, executed.text
        assert executed.json()["status"] == "executed"
        assert executed.json()["result_json"]["task_id"]


def test_intelligence_tenant_and_conversation_isolation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token_a = register(client, "AI Company A", f"owner-a-{suffix}@example.com")
        token_b = register(client, "AI Company B", f"owner-b-{suffix}@example.com")
        created = client.post("/api/v1/intelligence/conversations", headers=auth(token_a), json={})
        cid = created.json()["id"]

        forbidden = client.get(f"/api/v1/intelligence/conversations/{cid}", headers=auth(token_b))
        assert forbidden.status_code == 404


def test_intelligence_manager_can_chat_but_employee_cannot_approve():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        owner = register(client, "AI Roles Co", f"owner-{suffix}@example.com")
        created_user = client.post(
            "/api/v1/users",
            headers=auth(owner),
            json={"full_name": "Employee", "email": f"employee-{suffix}@example.com", "password": "StrongPass123!", "role_keys": ["employee"]},
        )
        assert created_user.status_code == 201, created_user.text
        employee_login = client.post("/api/v1/auth/login", json={"email": f"employee-{suffix}@example.com", "password": "StrongPass123!"})
        employee_token = employee_login.json()["access_token"]

        created = client.post("/api/v1/intelligence/conversations", headers=auth(employee_token), json={})
        assert created.status_code == 201

        # Employee may chat, but cannot approve action proposals.
        fake_id = str(uuid4())
        response = client.post(f"/api/v1/intelligence/action-proposals/{fake_id}/approve", headers=auth(employee_token))
        assert response.status_code == 403
