import copy
import hashlib
import re
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.models.company import Company
from app.models.inventory import StockBalance
from app.models.order_imports import OrderImportBatch, OrderImportEntry, OrderImportSource
from app.models.product import Product
from app.models.user import User
from app.schemas.order_imports import CommitOrderResult, CommitReviewResult
from app.schemas.sales import SalesOrderCreate, SalesOrderItemCreate
from app.services.order_import_parser import OrderImportFormatError, parse_order_csv
from app.services.sales_service import create_order


def fail(code: str, message: str, status: int = 422):
    raise HTTPException(status_code=status, detail={'code': code, 'message': message})


def _lock_company(db: Session, actor: User):
    # Serialize tenant quotas and external identities across batches/instances.
    if db.scalar(select(Company.id).where(Company.id == actor.company_id).with_for_update()) is None:
        fail('company_not_found', 'Empresa não encontrada.', 404)


def get_review(db: Session, actor: User, batch_id: UUID, *, lock: bool = False) -> OrderImportBatch:
    statement = select(OrderImportBatch).where(OrderImportBatch.id == batch_id,
        OrderImportBatch.company_id == actor.company_id).options(selectinload(OrderImportBatch.entries))
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    batch = db.scalar(statement)
    if batch is None:
        fail('batch_not_found', 'Importação não encontrada.', 404)
    return batch


def _catalog(db, actor, entries, *, lock=False):
    skus = {item['sku'] for entry in entries for item in entry.normalized_items
        if item['sku'] and len(item['sku']) <= 80 and '\x00' not in item['sku']}
    statement = select(Product).where(Product.company_id == actor.company_id, Product.sku.in_(skus)).order_by(Product.id)
    if lock:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    result = {}
    for product in db.scalars(statement):
        result.setdefault(product.sku, []).append(product)
    return result


def _issue(row, field, code, message):
    return dict(row=row, field=field, code=code, message=message)


def _assess_entry(db, actor, entry, catalog):
    errors = copy.deepcopy(entry.parser_errors)
    warnings = []
    normalized = []
    total = Decimal('0')
    for raw in entry.normalized_items:
        item = {key: raw[key] for key in ('sku', 'quantity', 'row')}
        products = catalog.get(item['sku'], [])
        if len(products) != 1:
            errors.append(_issue(item['row'], 'sku', 'sku_not_found' if not products else 'sku_ambiguous',
                'SKU não encontrado.' if not products else 'SKU não é único no catálogo.'))
        else:
            product = products[0]
            item.update(product_id=str(product.id), unit_price=str(product.price), product_name=product.name)
            total += product.price * item['quantity']
            stock = db.scalar(select(func.coalesce(func.sum(StockBalance.quantity), 0)).where(
                StockBalance.company_id == actor.company_id, StockBalance.product_id == product.id))
            if stock < item['quantity']:
                warnings.append(_issue(item['row'], 'quantity', 'insufficient_stock',
                    'Saldo total insuficiente; o depósito será verificado na confirmação.'))
        normalized.append(item)
    if total > Decimal('999999999999.99'):
        errors.append(_issue(entry.source_lines[0], None, 'order_total_exceeded', 'Total excede o limite do pedido.'))
    duplicate = db.scalar(select(OrderImportSource.id).where(OrderImportSource.company_id == actor.company_id,
        OrderImportSource.external_order_id == entry.external_order_id))
    if duplicate:
        errors.append(_issue(entry.source_lines[0], 'external_order_id', 'duplicate_external_order_id',
            'Esta referência já gerou um pedido nesta empresa.'))
    entry.normalized_items = normalized
    entry.errors = errors
    entry.warnings = warnings
    entry.status = 'duplicate' if duplicate else ('invalid' if errors else 'valid')


def _snapshot(batch):
    return [dict(entry_id=str(e.id), status=e.status, normalized_items=copy.deepcopy(e.normalized_items),
        errors=copy.deepcopy(e.errors), warnings=copy.deepcopy(e.warnings)) for e in batch.entries]


def create_review(db: Session, actor: User, filename: str, content: bytes) -> tuple[OrderImportBatch, bool]:
    try:
        parsed = parse_order_csv(content)
    except OrderImportFormatError as error:
        fail(error.code, error.message, 413 if error.code == 'file_too_large' else 422)
    try:
        _lock_company(db, actor)
        digest = hashlib.sha256(content).hexdigest()
        existing = db.scalar(select(OrderImportBatch).where(OrderImportBatch.company_id == actor.company_id,
            OrderImportBatch.sha256 == digest))
        if existing is not None:
            return get_review(db, actor, existing.id), False
        count = db.scalar(select(func.count()).select_from(OrderImportBatch).where(OrderImportBatch.company_id == actor.company_id))
        if count >= 100:
            fail('retained_batch_limit', 'Limite de 100 importações retidas. Solicite limpeza ao administrador.', 409)
        midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily = db.scalar(select(func.count()).select_from(OrderImportBatch).where(
            OrderImportBatch.company_id == actor.company_id, OrderImportBatch.created_at >= midnight))
        if daily >= 20:
            fail('daily_batch_limit', 'Limite diário de 20 importações atingido.', 429)
        basename = filename.replace('\\', '/').split('/')[-1]
        safe_name = re.sub(r'[^\w. -]', '_', basename)[:120] or 'orders.csv'
        batch = OrderImportBatch(company_id=actor.company_id, actor_id=actor.id, filename=safe_name,
            sha256=digest, status='reviewed', unassigned_errors=[i.model_dump() for i in parsed.unassigned_errors])
        for position, order in enumerate(parsed.orders):
            batch.entries.append(OrderImportEntry(company_id=actor.company_id, external_order_id=order.external_order_id,
                position=position, source_lines=order.source_lines, status='invalid',
                parser_errors=[i.model_dump() for i in order.errors],
                normalized_items=[dict(sku=item.sku, quantity=item.quantity, row=row)
                    for item, row in zip(order.items, order.source_lines)]))
        db.add(batch)
        # Assess after assigning entries, before flushing to persist only complete results.
        catalog = _catalog(db, actor, batch.entries, lock=True)
        for entry in batch.entries:
            _assess_entry(db, actor, entry, catalog)
        db.flush()
        record_audit(db, request=None, action='order_import.reviewed', company_id=actor.company_id,
            actor_user_id=actor.id, resource_type='order_import_batch', resource_id=batch.id,
            metadata={'sha256': digest, 'entries': len(batch.entries)})
        batch_id = batch.id
        db.commit()
        return get_review(db, actor, batch_id), True
    except Exception:
        db.rollback()
        raise


def revalidate_review(db: Session, actor: User, batch_id: UUID) -> OrderImportBatch:
    try:
        _lock_company(db, actor)
        batch = get_review(db, actor, batch_id, lock=True)
        before = _snapshot(batch)
        entries = [entry for entry in batch.entries if entry.status != 'committed']
        catalog = _catalog(db, actor, entries, lock=True)
        for entry in entries:
            _assess_entry(db, actor, entry, catalog)
        record_audit(db, request=None, action='order_import.revalidated', company_id=actor.company_id,
            actor_user_id=actor.id, resource_type='order_import_batch', resource_id=batch.id,
            metadata={'before': before, 'after': _snapshot(batch)})
        db.commit()
        return get_review(db, actor, batch_id)
    except Exception:
        db.rollback()
        raise


def commit_review(db: Session, actor: User, batch_id: UUID, entry_ids: list[UUID]) -> CommitReviewResult:
    try:
        _lock_company(db, actor)
        batch = get_review(db, actor, batch_id, lock=True)
        if not 1 <= len(entry_ids) <= 100 or len(set(entry_ids)) != len(entry_ids):
            fail('invalid_selection', 'Selecione de 1 a 100 itens distintos.')
        by_id = {entry.id: entry for entry in batch.entries if entry.company_id == actor.company_id}
        if any(entry_id not in by_id for entry_id in entry_ids):
            fail('invalid_selection', 'A seleção não pertence a esta importação.')
        entries = [by_id[entry_id] for entry_id in entry_ids]
        pending = [entry for entry in entries if entry.status != 'committed']
        catalog = _catalog(db, actor, pending, lock=True)
        # Validate the entire selection before creating the first draft.
        for entry in pending:
            if db.scalar(select(OrderImportSource.id).where(OrderImportSource.company_id == actor.company_id,
                OrderImportSource.external_order_id == entry.external_order_id)):
                fail('duplicate_external_order_id', 'Esta referência já gerou um pedido nesta empresa.', 409)
            if entry.status != 'valid':
                fail('invalid_selection', 'A seleção contém pedidos inválidos.')
            for item in entry.normalized_items:
                products = catalog.get(item['sku'], [])
                if len(products) != 1 or str(products[0].id) != item.get('product_id') or products[0].price != Decimal(item['unit_price']):
                    fail('catalog_changed', 'O catálogo mudou. Revalide a importação antes de continuar.', 409)
            # Refresh stock warnings without reserving stock or silently changing price.
            _assess_entry(db, actor, entry, catalog)
        orders = []
        for entry in entries:
            reused = entry.status == 'committed'
            if not reused:
                payload = SalesOrderCreate(items=[SalesOrderItemCreate(product_id=UUID(item['product_id']),
                    quantity=item['quantity']) for item in entry.normalized_items])
                order = create_order(db, actor, payload, commit=False)
                db.add(OrderImportSource(company_id=actor.company_id, external_order_id=entry.external_order_id,
                    sales_order_id=order.id))
                entry.sales_order_id = order.id
                entry.status = 'committed'
            orders.append(CommitOrderResult(entry_id=entry.id, order_id=entry.sales_order_id, reused=reused))
        committed_count = sum(entry.status == 'committed' for entry in batch.entries)
        batch.status = 'committed' if committed_count == len(batch.entries) else 'partially_committed'
        record_audit(db, request=None, action='order_import.committed', company_id=actor.company_id,
            actor_user_id=actor.id, resource_type='order_import_batch', resource_id=batch.id,
            metadata={'orders': [o.model_dump(mode='json') for o in orders]})
        db.commit()
        return CommitReviewResult(batch_id=batch_id, orders=orders)
    except Exception:
        db.rollback()
        raise
