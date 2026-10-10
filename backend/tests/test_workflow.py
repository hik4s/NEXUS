from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def register(client, company, email):
    r = client.post("/api/v1/auth/register", json={"company_name": company, "company_slug": company.lower().replace(" ", "-") + uuid4().hex[:4], "full_name": "Owner", "email": email, "password": "StrongPass123!"})
    assert r.status_code == 201, r.text
    data = r.json()
    return data["access_token"], data["user"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_user(client, token, email, role_keys):
    r = client.post("/api/v1/users", headers=auth(token), json={"full_name": email.split("@")[0], "email": email, "password": "StrongPass123!", "role_keys": role_keys})
    assert r.status_code == 201, r.text
    return r.json()


def test_workflow_task_sla_approval_comment_and_escalation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token, _ = register(client, "Workflow Co", f"owner-{suffix}@example.com")
        second = create_user(client, token, f"manager-{suffix}@example.com", ["manager"])

        r = client.post("/api/v1/workflow/tasks", headers=auth(token), json={"title":"Approve supplier quote", "priority":"high", "assignee_user_id":second["id"], "sla_minutes":60})
        assert r.status_code == 201, r.text
        task = r.json()
        assert task["sla"]["target_minutes"] == 60

        r = client.post(f"/api/v1/workflow/tasks/{task['id']}/comments", headers=auth(token), json={"body":"Please review this today."})
        assert r.status_code == 201

        r = client.post(f"/api/v1/workflow/tasks/{task['id']}/approvals", headers=auth(token), json={"approver_user_id":second["id"]})
        assert r.status_code == 201, r.text
        approval_id = r.json()["id"]

        r = client.patch(f"/api/v1/workflow/approvals/{approval_id}", headers=auth(token), json={"status":"approved"})
        assert r.status_code == 403

        login = client.post("/api/v1/auth/login", json={"email":f"manager-{suffix}@example.com", "password":"StrongPass123!"})
        assert login.status_code == 200
        manager_token = login.json()["access_token"]
        r = client.patch(f"/api/v1/workflow/approvals/{approval_id}", headers=auth(manager_token), json={"status":"approved", "decision_note":"Approved."})
        assert r.status_code == 200

        r = client.post(f"/api/v1/workflow/tasks/{task['id']}/escalations", headers=auth(token), json={"to_user_id":second["id"], "reason":"Needs management attention."})
        assert r.status_code == 201, r.text
        assert r.json()["level"] == 1

        r = client.patch(f"/api/v1/workflow/tasks/{task['id']}/status", headers=auth(token), json={"status":"in_progress"})
        assert r.status_code == 200


def test_workflow_tenant_isolation():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token_a, _ = register(client, "Company A", f"owner-a-{suffix}@example.com")
        token_b, _ = register(client, "Company B", f"owner-b-{suffix}@example.com")

        r = client.post("/api/v1/workflow/tasks", headers=auth(token_a), json={"title":"Private task"})
        assert r.status_code == 201
        task_id = r.json()["id"]

        r = client.get(f"/api/v1/workflow/tasks/{task_id}", headers=auth(token_b))
        assert r.status_code == 404


def test_workflow_invalid_transition_and_attachment():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token, _ = register(client, "Transitions Co", f"owner-{suffix}@example.com")
        r = client.post("/api/v1/workflow/tasks", headers=auth(token), json={"title":"Task"})
        assert r.status_code == 201
        task_id = r.json()["id"]

        r = client.patch(f"/api/v1/workflow/tasks/{task_id}/status", headers=auth(token), json={"status":"completed"})
        assert r.status_code == 409

        r = client.post(f"/api/v1/workflow/tasks/{task_id}/attachments", headers=auth(token), json={"file_name":"spec.pdf","object_key":"tasks/spec.pdf","mime_type":"application/pdf","size_bytes":1200})
        assert r.status_code == 201
        assert r.json()["object_key"] == "tasks/spec.pdf"
