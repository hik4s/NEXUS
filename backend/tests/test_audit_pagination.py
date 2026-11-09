from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.audit import AuditLog


def test_audit_pages_are_stable_and_tenant_scoped():
    with TestClient(app) as client:
        suffix = uuid4().hex
        owner = client.post('/api/v1/auth/register', json={'company_name': suffix, 'company_slug': suffix,
            'full_name': 'Audit owner', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!'}).json()
        with Session(engine) as db:
            for _ in range(3):
                db.add(AuditLog(company_id=UUID(owner['user']['company_id']), action='test.pagination', status='success'))
            db.commit()
        headers = {'Authorization': f"Bearer {owner['access_token']}"}
        first = client.get('/api/v1/audit-logs?page=1&page_size=2', headers=headers)
        second = client.get('/api/v1/audit-logs?page=2&page_size=2', headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.headers['X-Total-Count'] == '4'
        assert len(first.json()) == len(second.json()) == 2
        assert {row['id'] for row in first.json()}.isdisjoint({row['id'] for row in second.json()})
        assert all(row['company_id'] == owner['user']['company_id'] for row in first.json() + second.json())
