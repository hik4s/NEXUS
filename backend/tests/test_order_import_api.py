from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.order import SalesOrder
from app.models.product import Product
from app.models.finance import AccountsReceivable
from app.models.inventory import StockMovement
from app.models.audit import AuditLog
from app.models.user import User

HEADER = b'external_order_id,sku,quantity\n'
pytestmark = pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Requires PostgreSQL migrations/locks')


def register(client):
    suffix = uuid4().hex
    result = client.post('/api/v1/auth/register', json={'company_name': suffix, 'company_slug': suffix,
        'full_name': 'Import Owner', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!'})
    assert result.status_code == 201, result.text
    return result.json()


@pytest.fixture
def workspace():
    with TestClient(app) as client:
        owner = register(client)
        headers = {'Authorization': f"Bearer {owner['access_token']}"}
        company = owner['user']['company_id']
        product = client.post(f'/api/v1/companies/{company}/products', headers=headers,
            json={'name': 'Demo product', 'sku': 'SKU', 'price': '10.00', 'cost': '5.00'})
        assert product.status_code == 201, product.text
        yield dict(client=client, headers=headers, company=UUID(company),
            actor=UUID(owner['user']['id']), product=UUID(product.json()['id']))


def upload(w, content=HEADER+b'A,SKU,2\n', expected=201, filename='orders.csv'):
    response = w['client'].post('/api/v1/order-imports', headers=w['headers'],
        files={'file': (filename, content, 'text/csv')})
    assert response.status_code == expected, response.text
    return response.json()


def commit(w, batch, entries=None):
    return w['client'].post(f"/api/v1/order-imports/{batch['id']}/commit", headers=w['headers'],
        json={'entry_ids': entries if entries is not None else [e['id'] for e in batch['entries']]})


def count(db, model, company):
    return db.scalar(select(func.count()).select_from(model).where(model.company_id == company))


def test_review_is_durable_bounded_and_has_no_business_effects(workspace):
    w = workspace
    batch = upload(w, HEADER+b'A,SKU,2\nB,UNKNOWN,1\n,SKU,1\n', filename='../../orders.csv')
    assert batch['filename'] == 'orders.csv'
    assert batch['status'] == 'reviewed'
    assert [e['status'] for e in batch['entries']] == ['valid', 'invalid']
    assert batch['entries'][1]['errors'][0]['code'] == 'sku_not_found'
    assert batch['unassigned_errors'][0]['row'] == 4
    assert batch['entries'][0]['warnings'][0]['code'] == 'insufficient_stock'
    assert batch['entries'][0]['normalized_items'][0]['unit_price'] == '10.00'
    repeat = upload(w, HEADER+b'A,SKU,2\nB,UNKNOWN,1\n,SKU,1\n', expected=200)
    assert repeat['id'] == batch['id']
    fetched = w['client'].get(f"/api/v1/order-imports/{batch['id']}", headers=w['headers'])
    assert fetched.status_code == 200 and fetched.json() == batch
    page = w['client'].get('/api/v1/order-imports?page_size=1', headers=w['headers'])
    assert page.status_code == 200 and page.headers['X-Total-Count'] == '1'
    with Session(engine) as db:
        for model in (SalesOrder, StockMovement, AccountsReceivable):
            assert count(db, model, w['company']) == 0


def test_structural_errors_and_size_leave_no_batches(workspace):
    from app.models.order_imports import OrderImportBatch
    w = workspace
    upload(w, HEADER+b'A,SKU,1,extra\n', expected=422)
    upload(w, b'x'*(1048576+1), expected=413)
    with Session(engine) as db:
        assert count(db, OrderImportBatch, w['company']) == 0


def test_partial_selection_replay_and_mixed_selection(workspace):
    w = workspace
    batch = upload(w, HEADER+b'A,SKU,1\nB,SKU,2\nC,UNKNOWN,1\n')
    a, b, invalid = [e['id'] for e in batch['entries']]
    assert commit(w, batch, [a, invalid]).status_code == 422
    assert commit(w, batch, []).status_code == 422
    assert commit(w, batch, [a, a]).status_code == 422
    assert commit(w, batch, [str(uuid4())]).status_code == 422
    first = commit(w, batch, [a])
    assert first.status_code == 200, first.text
    mixed = commit(w, batch, [a, b])
    assert mixed.status_code == 200, mixed.text
    assert mixed.json()['orders'][0]['reused'] is True
    assert mixed.json()['orders'][0]['order_id'] == first.json()['orders'][0]['order_id']
    replay = commit(w, batch, [a, b])
    assert all(o['reused'] for o in replay.json()['orders'])
    with Session(engine) as db:
        assert count(db, SalesOrder, w['company']) == 2
        assert count(db, StockMovement, w['company']) == count(db, AccountsReceivable, w['company']) == 0


def test_catalog_change_requires_explicit_revalidation_with_audit(workspace):
    w = workspace
    batch = upload(w)
    with Session(engine) as db:
        db.get(Product, w['product']).price = 12
        db.commit()
    changed = commit(w, batch)
    assert changed.status_code == 409 and changed.json()['detail']['code'] == 'catalog_changed'
    revised = w['client'].post(f"/api/v1/order-imports/{batch['id']}/revalidate", headers=w['headers'])
    assert revised.status_code == 200, revised.text
    assert revised.json()['entries'][0]['normalized_items'][0]['unit_price'] == '12.00'
    saved = commit(w, revised.json())
    assert saved.status_code == 200, saved.text
    with Session(engine) as db:
        order = db.get(SalesOrder, UUID(saved.json()['orders'][0]['order_id']))
        assert str(order.total) == '24.00'
        audit = db.scalar(select(AuditLog).where(AuditLog.company_id == w['company'],
            AuditLog.action == 'order_import.revalidated'))
        assert audit.metadata_json['before'][0]['normalized_items'][0]['unit_price'] == '10.00'
        assert audit.metadata_json['after'][0]['normalized_items'][0]['unit_price'] == '12.00'


def test_external_identity_cannot_be_reused_in_other_files(workspace):
    w = workspace
    first = upload(w)
    assert commit(w, first).status_code == 200
    second = upload(w, HEADER+b'A,SKU,3\n')
    assert second['entries'][0]['status'] == 'duplicate'
    assert commit(w, second).status_code == 409
    with Session(engine) as db:
        assert count(db, SalesOrder, w['company']) == 1


def test_tenant_isolation_includes_hashes_selection_and_export(workspace):
    w = workspace
    batch = upload(w)
    other = register(w['client'])
    other_headers = {'Authorization': f"Bearer {other['access_token']}"}
    for method, path, body in [
        ('get', '', None), ('get', '/errors.csv', None), ('post', '/revalidate', None),
        ('post', '/commit', {'entry_ids': [batch['entries'][0]['id']]}),
    ]:
        response = w['client'].request(method, f"/api/v1/order-imports/{batch['id']}{path}",
            headers=other_headers, json=body)
        assert response.status_code == 404, response.text
    own = upload({**w, 'headers': other_headers})
    assert own['id'] != batch['id']
    assert own['entries'][0]['errors'][0]['code'] == 'sku_not_found'
    assert commit(w, batch, [own['entries'][0]['id']]).status_code == 422


def test_create_failure_rolls_back_whole_selection(workspace, monkeypatch):
    from app.services import order_import_service as service
    w = workspace
    batch = upload(w, HEADER+b'A,SKU,1\nB,SKU,2\n')
    original = service.create_order
    calls = 0
    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('injected failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(service, 'create_order', fail_second)
    with pytest.raises(RuntimeError, match='injected failure'):
        commit(w, batch)
    with Session(engine) as db:
        assert count(db, SalesOrder, w['company']) == 0
    monkeypatch.setattr(service, 'create_order', original)
    assert commit(w, batch).status_code == 200


def test_two_batches_concurrently_claim_same_external_reference(workspace):
    from app.services.order_import_service import commit_review
    w = workspace
    batches = [upload(w), upload(w, HEADER+b'A,SKU,2\n\n')]
    barrier = Barrier(2)
    def attempt(batch):
        with Session(engine) as db:
            actor = db.get(User, w['actor'])
            barrier.wait(timeout=10)
            try:
                return commit_review(db, actor, UUID(batch['id']), [UUID(batch['entries'][0]['id'])])
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, batches))
    assert sum(isinstance(r, int) and r == 409 for r in results) == 1
    with Session(engine) as db:
        assert count(db, SalesOrder, w['company']) == 1


@pytest.mark.parametrize('existing,daily', [(19, True), (99, False)])
def test_batch_quota_boundaries(workspace, existing, daily):
    from app.models.order_imports import OrderImportBatch
    w = workspace
    with Session(engine) as db:
        for i in range(existing):
            db.add(OrderImportBatch(company_id=w['company'], actor_id=w['actor'], filename='probe.csv',
                sha256=f'{i:064x}', status='reviewed', unassigned_errors=[],
                created_at=datetime.now(timezone.utc) - timedelta(days=0 if daily else 2)))
        db.commit()
    upload(w)
    blocked = w['client'].post('/api/v1/order-imports', headers=w['headers'],
        files={'file': ('new.csv', HEADER+b'B,SKU,1\n')})
    assert blocked.status_code == 429 if daily else blocked.status_code == 409
    upload(w, expected=200)  # A retry never consumes another quota slot.


def test_errors_csv_neutralizes_formulas_and_requires_permission(workspace):
    w = workspace
    batch = upload(w, HEADER+b'=1+1,UNKNOWN,1\n')
    exported = w['client'].get(f"/api/v1/order-imports/{batch['id']}/errors.csv", headers=w['headers'])
    assert exported.status_code == 200
    assert "'=1+1" in exported.text
    assert w['client'].get(f"/api/v1/order-imports/{batch['id']}/errors.csv").status_code == 401
    suffix = uuid4().hex
    user = w['client'].post('/api/v1/users', headers=w['headers'], json={
        'full_name': 'Employee', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!', 'role_keys': ['employee']})
    assert user.status_code == 201
    token = w['client'].post('/api/v1/auth/login', json={'email': f'{suffix}@example.com', 'password': 'StrongPass123!'}).json()['access_token']
    assert w['client'].get(f"/api/v1/order-imports/{batch['id']}/errors.csv", headers={'Authorization': f'Bearer {token}'}).status_code == 403


def test_same_batch_concurrent_commit_and_hash_retry(workspace):
    from app.services.order_import_service import commit_review, create_review
    from app.models.order_imports import OrderImportBatch
    w = workspace
    barrier = Barrier(2)
    def review_attempt(_):
        with Session(engine) as db:
            actor = db.get(User, w['actor'])
            barrier.wait(timeout=10)
            batch, created = create_review(db, actor, 'orders.csv', HEADER+b'A,SKU,1\n')
            return batch.id, batch.entries[0].id, created
    with ThreadPoolExecutor(max_workers=2) as pool:
        reviews = list(pool.map(review_attempt, range(2)))
    assert reviews[0][:2] == reviews[1][:2]
    assert sorted(r[2] for r in reviews) == [False, True]
    barrier = Barrier(2)
    def commit_attempt(_):
        with Session(engine) as db:
            actor = db.get(User, w['actor'])
            barrier.wait(timeout=10)
            return commit_review(db, actor, reviews[0][0], [reviews[0][1]])
    with ThreadPoolExecutor(max_workers=2) as pool:
        commits = list(pool.map(commit_attempt, range(2)))
    assert commits[0].orders[0].order_id == commits[1].orders[0].order_id
    assert sorted(c.orders[0].reused for c in commits) == [False, True]
    with Session(engine) as db:
        assert count(db, OrderImportBatch, w['company']) == count(db, SalesOrder, w['company']) == 1


@pytest.mark.parametrize('existing,daily', [(19, True), (99, False)])
def test_quota_is_serialized_for_concurrent_uploads(workspace, existing, daily):
    from app.services.order_import_service import create_review
    from app.models.order_imports import OrderImportBatch
    w = workspace
    with Session(engine) as db:
        db.add_all([OrderImportBatch(company_id=w['company'], actor_id=w['actor'], filename='probe.csv',
            sha256=f'{i:064x}', status='reviewed', unassigned_errors=[],
            created_at=datetime.now(timezone.utc) - timedelta(days=0 if daily else 2)) for i in range(existing)])
        db.commit()
    barrier = Barrier(2)
    def attempt(index):
        with Session(engine) as db:
            actor = db.get(User, w['actor'])
            barrier.wait(timeout=10)
            try:
                create_review(db, actor, 'orders.csv', HEADER+f'O{index},SKU,1\n'.encode())
                return 201
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [201, 429 if daily else 409]


def test_revalidation_keeps_parser_errors_and_committed_prices(workspace):
    w = workspace
    batch = upload(w, HEADER+b'A,SKU,1\nB,SKU,0\nC,UNKNOWN,1\n')
    saved = commit(w, batch, [batch['entries'][0]['id']])
    assert saved.status_code == 200, saved.text
    with Session(engine) as db:
        db.get(Product, w['product']).price = 15
        db.add(Product(company_id=w['company'], name='Now known', sku='UNKNOWN', price=4, cost=2))
        db.commit()
    revised = w['client'].post(f"/api/v1/order-imports/{batch['id']}/revalidate", headers=w['headers']).json()
    a, b, c = revised['entries']
    assert a['status'] == 'committed' and a['normalized_items'][0]['unit_price'] == '10.00'
    assert b['status'] == 'invalid' and b['errors'][0]['code'] == 'invalid_quantity'
    assert c['status'] == 'valid' and c['normalized_items'][0]['unit_price'] == '4.00'
    final = commit(w, revised, [a['id'], c['id']])
    assert final.status_code == 200 and final.json()['orders'][0]['reused'] is True


def test_manager_can_import_and_generate_without_payment_or_discount_privileges(workspace):
    w = workspace
    suffix = uuid4().hex
    user = w['client'].post('/api/v1/users', headers=w['headers'], json={
        'full_name': 'Manager', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!', 'role_keys': ['manager']})
    assert user.status_code == 201
    token = w['client'].post('/api/v1/auth/login', json={'email': f'{suffix}@example.com', 'password': 'StrongPass123!'}).json()['access_token']
    manager = {**w, 'headers': {'Authorization': f'Bearer {token}'}}
    batch = upload(manager)
    saved = commit(manager, batch)
    assert saved.status_code == 200, saved.text
    denied = w['client'].post('/api/v1/sales/orders', headers=manager['headers'], json={
        'items': [{'product_id': str(w['product']), 'quantity': 1}], 'order_discount': '1.00'})
    assert denied.status_code == 403
    payment = w['client'].post(f'/api/v1/finance/receivables/{uuid4()}/pay', headers=manager['headers'],
        json={'account_id': str(uuid4())})
    assert payment.status_code == 403


def test_invalid_sku_cannot_break_other_orders(workspace):
    w = workspace
    batch = upload(w, HEADER+b'A,SKU\x00,1\nB,SKU,1\n')
    assert batch['entries'][0]['status'] == 'invalid'
    assert batch['entries'][0]['errors'][0]['code'] == 'invalid_sku'
    assert batch['entries'][1]['status'] == 'valid'
    assert commit(w, batch, [batch['entries'][1]['id']]).status_code == 200


def test_imported_order_connects_to_confirmation_and_cancellation(workspace):
    w = workspace
    warehouse = w['client'].post('/api/v1/inventory/warehouses', headers=w['headers'], json={'name': 'Import warehouse', 'code': 'IMP'})
    assert warehouse.status_code == 201
    batch = upload(w)
    receipt = w['client'].post('/api/v1/inventory/movements', headers=w['headers'], json={
        'warehouse_id': warehouse.json()['id'], 'product_id': str(w['product']), 'movement_type': 'receipt', 'quantity': 3})
    assert receipt.status_code == 201
    saved = commit(w, batch)
    assert saved.status_code == 200
    refreshed = w['client'].get(f"/api/v1/order-imports/{batch['id']}", headers=w['headers']).json()
    assert refreshed['entries'][0]['warnings'] == []
    order_id = saved.json()['orders'][0]['order_id']
    confirmed = w['client'].patch(f'/api/v1/sales/orders/{order_id}/status', headers=w['headers'],
        json={'status': 'confirmed', 'warehouse_id': warehouse.json()['id']})
    assert confirmed.status_code == 200, confirmed.text
    cancelled = w['client'].patch(f'/api/v1/sales/orders/{order_id}/status', headers=w['headers'], json={'status': 'cancelled'})
    assert cancelled.status_code == 200, cancelled.text
    from app.models.inventory import StockBalance
    with Session(engine) as db:
        assert db.scalar(select(StockBalance.quantity).where(StockBalance.company_id == w['company'])) == 3
        ar = db.scalar(select(AccountsReceivable).where(AccountsReceivable.company_id == w['company']))
        assert ar.status == 'cancelled' and str(ar.amount) == '20.00'
