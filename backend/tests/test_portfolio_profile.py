from uuid import uuid4
import asyncio
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import TimeoutError as DatabaseTimeout
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.db.session import engine
from app.identity.security import create_access_token, create_refresh_token
from app.main import create_app
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_owner


@pytest.fixture
def portfolio(monkeypatch):
    monkeypatch.setattr(settings, 'APP_PROFILE', 'portfolio')
    monkeypatch.setattr(settings, 'PUBLIC_REGISTRATION_ENABLED', False)
    monkeypatch.setattr(settings, 'REDIS_ENABLED', False)
    monkeypatch.setattr(settings, 'STORAGE_BACKEND', 'local')
    with TestClient(create_app()) as client:
        yield client


def provision():
    suffix = uuid4().hex
    with Session(engine) as db:
        user, token, refresh = register_owner(db, RegisterRequest(company_name=suffix,
            company_slug=suffix, full_name='Portfolio Owner', email=f'{suffix}@example.com', password='StrongPass123!'))
        return dict(id=user.id, company=user.company_id, token=token, refresh=refresh, email=user.email)


def headers(owner):
    return {'Authorization': f"Bearer {owner['token']}"}


def test_profile_settings_fail_closed_and_preserve_full_defaults(monkeypatch):
    monkeypatch.delenv('APP_PROFILE', raising=False)
    monkeypatch.delenv('PUBLIC_REGISTRATION_ENABLED', raising=False)
    assert Settings(_env_file=None).APP_PROFILE == 'full'
    assert Settings(_env_file=None).PUBLIC_REGISTRATION_ENABLED is True
    assert Settings(_env_file=None, APP_PROFILE='portfolio').PUBLIC_REGISTRATION_ENABLED is False
    assert Settings(_env_file=None, APP_PROFILE='portfolio', PUBLIC_REGISTRATION_ENABLED=True).PUBLIC_REGISTRATION_ENABLED is True
    with pytest.raises(ValidationError):
        Settings(_env_file=None, APP_PROFILE='portoflio')


def test_portfolio_hides_unsupported_routes_including_upload_and_jobs(portfolio):
    paths = portfolio.app.openapi()['paths']
    assert '/api/v1/order-imports' in paths
    assert '/api/v1/crm/customers' in paths
    assert '/api/v1/audit-logs' in paths
    for method, path in [('post', '/api/v1/async/jobs'), ('post', '/api/v1/integrations/files'),
        ('get', '/api/v1/integrations'), ('get', '/api/v1/intelligence'),
        ('get', '/api/v1/procurement/orders'), ('get', '/api/v1/logistics/deliveries'),
        ('get', '/api/v1/workflow/tasks'), ('get', '/api/v1/crm/leads'),
        ('get', '/api/v1/crm/interactions'), ('post', '/api/v1/inventory/transfers'),
        ('post', '/api/v1/finance/accounts'), ('post', '/api/v1/finance/transactions'),
        ('post', f'/api/v1/finance/receivables/{uuid4()}/pay'), ('get', '/api/v1/health/metrics')]:
        response = portfolio.request(method, path, json={})
        assert response.status_code in {404, 405}, (path, response.text)
    assert all('/integrations' not in path and '/platform' not in path and '/intelligence' not in path and '/async' not in path for path in paths)
    assert all(set(spec) <= {'get'} for path, spec in paths.items() if path.startswith('/api/v1/finance/'))
    assert portfolio.get('/api/v1/health').json() == {'status': 'ok'}
    assert portfolio.get('/api/v1/health/ready').json() == {'status': 'ready', 'database': 'ok'}


def test_registration_is_closed_but_existing_accounts_can_login_and_refresh(portfolio, monkeypatch):
    owner = provision()
    blocked = portfolio.post('/api/v1/auth/register', json={'company_name': 'Blocked',
        'company_slug': 'blocked', 'full_name': 'Blocked', 'email': 'blocked@example.com', 'password': 'StrongPass123!'})
    assert blocked.status_code == 403
    login = portfolio.post('/api/v1/auth/login', json={'email': owner['email'], 'password': 'StrongPass123!'})
    assert login.status_code == 200, login.text
    assert portfolio.post('/api/v1/auth/refresh', json={'refresh_token': owner['refresh']}).status_code == 200
    assert portfolio.get('/api/v1/auth/me', headers=headers(owner)).status_code == 200
    monkeypatch.setattr(settings, 'PUBLIC_REGISTRATION_ENABLED', True)
    suffix = uuid4().hex
    assert portfolio.post('/api/v1/auth/register', json={'company_name': suffix, 'company_slug': suffix,
        'full_name': 'Local opt-in', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!'}).status_code == 201


def test_employee_and_manager_limits_and_cross_tenant_ids(portfolio):
    owner, other = provision(), provision()
    auth = headers(owner)
    product = portfolio.post(f"/api/v1/companies/{owner['company']}/products", headers=auth,
        json={'sku': 'DEMO', 'name': 'Demo', 'price': '10.00', 'cost': '4.00'})
    assert product.status_code == 201, product.text
    order = portfolio.post('/api/v1/sales/orders', headers=auth,
        json={'items': [{'product_id': product.json()['id'], 'quantity': 1}]})
    assert order.status_code == 201
    for path in [f"/api/v1/companies/{owner['company']}",
        f"/api/v1/companies/{owner['company']}/products", f"/api/v1/sales/orders/{order.json()['id']}"]:
        assert portfolio.get(path, headers=headers(other)).status_code == 404

    role_headers, role_ids = {}, {}
    for role in ['manager', 'employee']:
        suffix = uuid4().hex
        created = portfolio.post('/api/v1/users', headers=auth, json={'full_name': role,
            'email': f'{suffix}@example.com', 'password': 'StrongPass123!', 'role_keys': [role]})
        assert created.status_code == 201, created.text
        role_ids[role] = created.json()['id']
        login = portfolio.post('/api/v1/auth/login', json={'email': f'{suffix}@example.com', 'password': 'StrongPass123!'})
        role_headers[role] = {'Authorization': f"Bearer {login.json()['access_token']}"}
    employee, manager = role_headers['employee'], role_headers['manager']
    assert portfolio.get(f"/api/v1/companies/{owner['company']}/products", headers=employee).status_code == 200
    assert portfolio.post('/api/v1/sales/orders', headers=employee,
        json={'items': [{'product_id': product.json()['id'], 'quantity': 1}]}).status_code == 403
    assert portfolio.post('/api/v1/order-imports', headers=employee,
        files={'file': ('orders.csv', b'external_order_id,sku,quantity\nDEMO,DEMO,1\n')}).status_code == 403
    review = portfolio.post('/api/v1/order-imports', headers=manager,
        files={'file': ('orders.csv', b'external_order_id,sku,quantity\nDEMO,DEMO,1\n')})
    assert review.status_code == 201, review.text
    batch = review.json()
    assert portfolio.post(f"/api/v1/order-imports/{batch['id']}/commit", headers=manager,
        json={'entry_ids': [batch['entries'][0]['id']]}).status_code == 200
    assert portfolio.post('/api/v1/users', headers=manager, json={'full_name': 'Elevated',
        'email': f'{uuid4().hex}@example.com', 'password': 'StrongPass123!', 'role_keys': ['admin']}).status_code == 403
    for roles in [['employee', 'admin'], ['employee', 'manager']]:
        assert portfolio.post('/api/v1/users', headers=manager, json={'full_name': 'Mixed roles',
            'email': f'{uuid4().hex}@example.com', 'password': 'StrongPass123!', 'role_keys': roles}).status_code == 403
        assert portfolio.patch(f"/api/v1/users/{role_ids['manager']}", headers=manager,
            json={'role_keys': roles}).status_code == 403


def test_expired_and_inactive_users_are_rejected(portfolio, monkeypatch):
    owner = provision()
    with monkeypatch.context() as expired_config:
        expired_config.setattr(settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', -1)
        expired = create_access_token(owner['id'])
    assert portfolio.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {expired}'}).status_code == 401
    assert portfolio.get('/api/v1/auth/me', headers={'Authorization': 'Bearer invalid-jwt'}).status_code == 401
    with monkeypatch.context() as expired_config:
        expired_config.setattr(settings, 'REFRESH_TOKEN_EXPIRE_MINUTES', -1)
        expired_refresh = create_refresh_token(owner['id'])
    assert portfolio.post('/api/v1/auth/refresh', json={'refresh_token': expired_refresh}).status_code == 401
    assert portfolio.post('/api/v1/auth/refresh', json={'refresh_token': 'invalid-jwt'}).status_code == 401
    with Session(engine) as db:
        db.get(User, owner['id']).is_active = False
        db.commit()
    assert portfolio.get('/api/v1/auth/me', headers=headers(owner)).status_code == 401
    assert portfolio.post('/api/v1/auth/refresh', json={'refresh_token': owner['refresh']}).status_code == 401


def test_cors_exposes_pagination_headers(portfolio):
    owner = provision()
    response = portfolio.get('/api/v1/order-imports', headers={**headers(owner), 'Origin': 'http://localhost:5173'})
    assert response.status_code == 200
    exposed = response.headers['access-control-expose-headers'].lower()
    assert all(header.lower() in exposed for header in ['X-Page', 'X-Page-Size', 'X-Total-Count', 'X-Total-Pages'])


def test_database_readiness_failure_is_503_without_secrets(portfolio, monkeypatch):
    from app.core import readiness
    async def broken_probe():
        raise DatabaseTimeout('postgresql://secret-password@private-db/secret-db')
    monkeypatch.setattr(readiness, '_probe_database', broken_probe)
    for path in ['/readiness', '/api/v1/health/ready']:
        response = portfolio.get(path)
        assert response.status_code == 503
        assert 'secret-password' not in response.text and 'private-db' not in response.text
    assert portfolio.get('/api/v1/health').status_code == 200


def test_readiness_deadline_cancels_a_hung_probe(portfolio, monkeypatch):
    from app.core import readiness
    cancelled = []
    async def hung_probe():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)
    monkeypatch.setattr(readiness, '_probe_database', hung_probe)
    monkeypatch.setattr(settings, 'DB_TIMEOUT_SECONDS', 0.05)
    started = time.monotonic()
    response = portfolio.get('/readiness')
    assert response.status_code == 503
    assert time.monotonic() - started < 1
    assert cancelled == [True]


def test_cancelled_readiness_request_cleans_up_its_probe(monkeypatch):
    from app.core import readiness
    async def exercise():
        started = asyncio.Event()
        cancelled = []
        async def probe():
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.append(True)
        monkeypatch.setattr(readiness, '_probe_database', probe)
        request = asyncio.create_task(readiness.database_readiness())
        await started.wait()
        request.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request
        await asyncio.sleep(0)
        assert cancelled == [True]
    asyncio.run(exercise())


def test_production_still_requires_a_real_secret(monkeypatch):
    monkeypatch.setattr(settings, 'APP_PROFILE', 'portfolio')
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    with pytest.raises(RuntimeError, match='SECRET_KEY'):
        with TestClient(create_app()):
            pass


def test_production_portfolio_rejects_unsafe_registration_and_sqlite(monkeypatch):
    from app.core.security_config import validate_security_configuration
    monkeypatch.setattr(settings, 'APP_PROFILE', 'portfolio')
    monkeypatch.setattr(settings, 'APP_ENV', 'production')
    monkeypatch.setattr(settings, 'SECRET_KEY', 'test-only-secret-with-adequate-length-123456789')
    monkeypatch.setattr(settings, 'DATABASE_URL', 'postgresql+psycopg://test:test@localhost/demo')
    monkeypatch.setattr(settings, 'PUBLIC_REGISTRATION_ENABLED', True)
    with pytest.raises(RuntimeError, match='PUBLIC_REGISTRATION_ENABLED'):
        validate_security_configuration()
    monkeypatch.setattr(settings, 'PUBLIC_REGISTRATION_ENABLED', False)
    monkeypatch.setattr(settings, 'DATABASE_URL', 'sqlite:///./data/test.db')
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        validate_security_configuration()
