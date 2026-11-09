"""Transactional guarantees exercised with independent PostgreSQL sessions."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4
from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.session import engine
from app.main import app
from app.models.audit import AuditLog
from app.models.finance import AccountsReceivable
from app.models.inventory import SalesOrderFulfillment, StockBalance, StockMovement
from app.models.order import SalesOrder
from app.models.platform import IdempotencyRecord
from app.models.user import User
from app.schemas.sales import SalesOrderCreate, SalesOrderStatusUpdate
from app.services import sales_service
from app.services.finance_service import pay_receivable
from app.services import finance_service
from app.schemas.finance import PaymentCreate
from app.api.v1.routes import sales as sales_routes

pytestmark = pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Requires real PostgreSQL locks")


@pytest.fixture
def sale():
    suffix = uuid4().hex
    with TestClient(app) as client:
        response = client.post('/api/v1/auth/register', json={
            'company_name': f'Transaction probe {suffix}', 'company_slug': suffix,
            'full_name': 'Owner', 'email': f'{suffix}@example.com', 'password': 'StrongPass123!',
        })
        assert response.status_code == 201, response.text
        owner = response.json()
        headers = {'Authorization': f"Bearer {owner['access_token']}"}
        company = owner['user']['company_id']
        product = client.post(f'/api/v1/companies/{company}/products', headers=headers,
                              json={'name': 'Probe', 'sku': suffix, 'price': '10.00', 'cost': '5.00'})
        assert product.status_code == 201, product.text
        warehouse = client.post('/api/v1/inventory/warehouses', headers=headers,
                                json={'name': 'Probe', 'code': suffix})
        assert warehouse.status_code == 201, warehouse.text
        movement = client.post('/api/v1/inventory/movements', headers=headers, json={
            'warehouse_id': warehouse.json()['id'], 'product_id': product.json()['id'],
            'movement_type': 'receipt', 'quantity': 10,
        })
        assert movement.status_code == 201, movement.text
        payload = {'items': [{'product_id': product.json()['id'], 'quantity': 2}]}
        order = client.post('/api/v1/sales/orders', headers=headers, json=payload)
        assert order.status_code == 201, order.text
        yield dict(client=client, headers=headers, payload=payload,
                   company=UUID(company), actor=UUID(owner['user']['id']),
                   order=UUID(order.json()['id']), warehouse=UUID(warehouse.json()['id']))


def transition(db, sale, target):
    actor = db.get(User, sale['actor'])
    order = sales_service.get_order(db, sale['company'], sale['order'])
    return sales_service.update_order_status(db, actor, order, SalesOrderStatusUpdate(
        status=target, warehouse_id=sale['warehouse']))


def assert_effects(sale, *, balance, status, movement, receivable_status):
    with Session(engine) as db:
        assert db.get(SalesOrder, sale['order']).status == status
        assert db.scalar(select(StockBalance.quantity).where(StockBalance.company_id == sale['company'])) == balance
        assert db.scalar(select(func.count()).select_from(SalesOrderFulfillment).where(SalesOrderFulfillment.order_id == sale['order'])) == 1
        rows = list(db.scalars(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order'])))
        assert len(rows) == 1 and rows[0].status == receivable_status
        assert db.scalar(select(func.count()).select_from(StockMovement).where(
            StockMovement.reference_id == sale['order'], StockMovement.movement_type == movement)) == 1


@pytest.mark.parametrize('target', ['confirmed', 'cancelled'])
def test_concurrent_transitions_have_one_winner(sale, target):
    if target == 'cancelled':
        with Session(engine) as db:
            transition(db, sale, 'confirmed')
    barrier = Barrier(2)

    def attempt():
        with Session(engine) as db:
            db.execute(text("SET LOCAL lock_timeout = '5s'"))
            actor = db.get(User, sale['actor'])
            # Both sessions deliberately load the same old status and relationships.
            order = sales_service.get_order(db, sale['company'], sale['order'])
            barrier.wait(timeout=10)
            try:
                sales_service.update_order_status(db, actor, order, SalesOrderStatusUpdate(
                    status=target, warehouse_id=sale['warehouse']))
                return 200
            except HTTPException as error:
                db.rollback()
                return error.status_code
            except Exception as error:
                db.rollback()
                return type(error).__name__

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results, key=str) == [200, 409], results
    assert_effects(sale, balance=8 if target == 'confirmed' else 10, status=target,
                   movement='sale' if target == 'confirmed' else 'sale_return',
                   receivable_status='pending' if target == 'confirmed' else 'cancelled')
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.resource_id == str(sale['order']),
            AuditLog.action == 'sales_order.status_changed')) == (1 if target == 'confirmed' else 2)


def test_receivable_failure_rolls_back_stock(sale, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('simulated finance failure')
    monkeypatch.setattr(sales_service, 'ensure_receivable_for_sales_order', fail)
    with Session(engine) as db:
        with pytest.raises(RuntimeError, match='finance failure'):
            transition(db, sale, 'confirmed')
        # Even a caller that commits after handling the failure must not persist partial effects.
        db.commit()
    with Session(engine) as db:
        assert db.get(SalesOrder, sale['order']).status == 'draft'
        assert db.scalar(select(StockBalance.quantity).where(StockBalance.company_id == sale['company'])) == 10
        for model in (SalesOrderFulfillment, AccountsReceivable):
            assert db.scalar(select(func.count()).select_from(model).where(model.company_id == sale['company'])) == 0
        assert db.scalar(select(func.count()).select_from(StockMovement).where(StockMovement.reference_id == sale['order'])) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog).where(
            AuditLog.resource_id == str(sale['order']), AuditLog.action != 'sales_order.created')) == 0


def test_paid_order_cannot_cancel(sale):
    with Session(engine) as db:
        transition(db, sale, 'confirmed')
        receivable = db.scalar(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order']))
        receivable.paid_amount = 1
        receivable.status = 'partially_paid'
        db.commit()
        with pytest.raises(HTTPException) as error:
            transition(db, sale, 'cancelled')
        assert error.value.status_code == 409
        db.commit()
    assert_effects(sale, balance=8, status='confirmed', movement='sale', receivable_status='partially_paid')


def test_idempotency_completion_failure_leaves_no_order(sale, monkeypatch):
    key = uuid4().hex
    original = sales_routes.complete_idempotency
    def fail(*args, **kwargs):
        raise RuntimeError('simulated response persistence failure')
    monkeypatch.setattr(sales_routes, 'complete_idempotency', fail)
    with pytest.raises(RuntimeError):
        sale['client'].post('/api/v1/sales/orders', headers={**sale['headers'], 'Idempotency-Key': key}, json=sale['payload'])
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.company_id == sale['company'])) == 1
        assert db.scalar(select(func.count()).select_from(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == key)) == 0
    monkeypatch.setattr(sales_routes, 'complete_idempotency', original)
    first = sale['client'].post('/api/v1/sales/orders', headers={**sale['headers'], 'Idempotency-Key': key}, json=sale['payload'])
    replay = sale['client'].post('/api/v1/sales/orders', headers={**sale['headers'], 'Idempotency-Key': key}, json=sale['payload'])
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()


def test_create_order_can_join_callers_transaction(sale):
    with Session(engine) as db:
        order = sales_service.create_order(db, db.get(User, sale['actor']),
            SalesOrderCreate.model_validate(sale['payload']), commit=False)
        order_id = order.id
        db.rollback()
    with Session(engine) as db:
        assert db.get(SalesOrder, order_id) is None


def test_lost_response_replays_committed_order(sale, monkeypatch):
    key = uuid4().hex
    def lose_response(*args, **kwargs):
        raise RuntimeError('connection lost after commit')
    monkeypatch.setattr(sales_routes, 'JSONResponse', lose_response)
    with pytest.raises(RuntimeError, match='after commit'):
        sale['client'].post('/api/v1/sales/orders', headers={**sale['headers'], 'Idempotency-Key': key}, json=sale['payload'])
    replay = sale['client'].post('/api/v1/sales/orders', headers={**sale['headers'], 'Idempotency-Key': key}, json=sale['payload'])
    assert replay.status_code == 201, replay.text
    with Session(engine) as db:
        record = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == key))
        assert record.state == 'completed'
        assert replay.json() == record.response_body
        assert db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.company_id == sale['company'])) == 2


def test_concurrent_idempotency_creates_one_order(sale):
    key = uuid4().hex
    barrier = Barrier(2)
    def attempt():
        with Session(engine) as db:
            actor = db.get(User, sale['actor'])
            request = Request({'type': 'http', 'method': 'POST', 'path': '/api/v1/sales/orders',
                'headers': [(b'idempotency-key', key.encode())], 'server': ('testserver', 80), 'scheme': 'http'})
            barrier.wait(timeout=10)
            return sales_routes.create_sales_order(SalesOrderCreate.model_validate(sale['payload']),
                request, current_user=actor, db=db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].body == results[1].body
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.company_id == sale['company'])) == 2


def test_cancel_refreshes_received_payment_snapshot(sale):
    with Session(engine) as stale, Session(engine) as payment:
        transition(stale, sale, 'confirmed')
        snapshot = stale.scalar(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order']))
        received = payment.get(AccountsReceivable, snapshot.id)
        received.paid_amount = 1
        received.status = 'partially_paid'
        payment.commit()
        with pytest.raises(HTTPException) as error:
            transition(stale, sale, 'cancelled')
        assert error.value.status_code == 409
    assert_effects(sale, balance=8, status='confirmed', movement='sale', receivable_status='partially_paid')


def test_payment_refreshes_cancelled_receivable_snapshot(sale):
    with Session(engine) as stale, Session(engine) as cancellation:
        transition(stale, sale, 'confirmed')
        snapshot = stale.scalar(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order']))
        transition(cancellation, sale, 'cancelled')
        # Must reject before even looking up a payment account.
        with pytest.raises(HTTPException) as error:
            pay_receivable(stale, stale.get(User, sale['actor']), snapshot.id, PaymentCreate(account_id=uuid4()))
        assert error.value.status_code == 409
        stale.rollback()
    assert_effects(sale, balance=10, status='cancelled', movement='sale_return', receivable_status='cancelled')


@pytest.mark.parametrize('reader', ['list_receivables', 'summary'])
def test_finance_reads_do_not_overwrite_concurrent_cancellation(sale, reader):
    with Session(engine) as setup:
        transition(setup, sale, 'confirmed')
        ar = setup.scalar(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order']))
        ar.due_date = date.today() - timedelta(days=1)
        setup.commit()
    with Session(engine) as stale, Session(engine) as cancellation:
        snapshot = stale.scalar(select(AccountsReceivable).where(AccountsReceivable.sales_order_id == sale['order']))
        assert snapshot.status == 'pending'
        transition(cancellation, sale, 'cancelled')
        getattr(finance_service, reader)(stale, sale['company'])
        # Also catch ORM mutations that a later unrelated commit might persist.
        stale.commit()
    assert_effects(sale, balance=10, status='cancelled', movement='sale_return', receivable_status='cancelled')
