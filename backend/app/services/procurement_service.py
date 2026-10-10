from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.models.inventory import Warehouse
from app.models.procurement import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    Supplier,
    SupplierProduct,
)
from app.models.product import Product
from app.models.user import User
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
    PurchaseReceiptCreate,
    SupplierCreate,
    SupplierProductUpsert,
)
from app.services.inventory_service import _apply_movement
from app.services.finance_service import ensure_payable_for_purchase_receipt

ALLOWED_PO_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"submitted", "cancelled"},
    "submitted": {"approved", "cancelled"},
    "approved": {"cancelled"},
    "partially_received": set(),
    "received": set(),
    "cancelled": set(),
}


def _get_supplier(db: Session, company_id: UUID, supplier_id: UUID) -> Supplier:
    supplier = db.scalar(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.company_id == company_id)
    )
    if supplier is None or not supplier.is_active:
        raise HTTPException(status_code=404, detail="Supplier not found or inactive")
    return supplier


def _get_warehouse(db: Session, company_id: UUID, warehouse_id: UUID) -> Warehouse:
    warehouse = db.scalar(
        select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.company_id == company_id)
    )
    if warehouse is None or not warehouse.is_active:
        raise HTTPException(status_code=404, detail="Warehouse not found or inactive")
    return warehouse


def _get_product(db: Session, company_id: UUID, product_id: UUID) -> Product:
    product = db.scalar(
        select(Product).where(Product.id == product_id, Product.company_id == company_id)
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _generate_order_number(prefix: str = "PO") -> str:
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def create_supplier(db: Session, actor: User, payload: SupplierCreate, request=None) -> Supplier:
    name = payload.name.strip()
    if db.scalar(select(Supplier).where(Supplier.company_id == actor.company_id, Supplier.name == name)):
        raise HTTPException(status_code=409, detail="Supplier name already exists")

    supplier = Supplier(
        company_id=actor.company_id,
        name=name,
        legal_name=payload.legal_name.strip() if payload.legal_name else None,
        tax_id=payload.tax_id.strip() if payload.tax_id else None,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        payment_terms_days=payload.payment_terms_days,
        notes=payload.notes,
    )
    db.add(supplier)
    db.flush()
    record_audit(
        db,
        request=request,
        action="supplier.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="supplier",
        resource_id=supplier.id,
        metadata={"name": supplier.name},
    )
    db.commit()
    db.refresh(supplier)
    return supplier


def list_suppliers(db: Session, company_id: UUID) -> list[Supplier]:
    return list(
        db.scalars(
            select(Supplier)
            .where(Supplier.company_id == company_id)
            .order_by(Supplier.is_active.desc(), Supplier.name.asc())
        ).all()
    )


def upsert_supplier_product(
    db: Session,
    actor: User,
    supplier_id: UUID,
    payload: SupplierProductUpsert,
    request=None,
) -> SupplierProduct:
    _get_supplier(db, actor.company_id, supplier_id)
    _get_product(db, actor.company_id, payload.product_id)
    mapping = db.scalar(
        select(SupplierProduct).where(
            SupplierProduct.company_id == actor.company_id,
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.product_id == payload.product_id,
        )
    )
    if mapping is None:
        mapping = SupplierProduct(
            company_id=actor.company_id,
            supplier_id=supplier_id,
            product_id=payload.product_id,
        )
        db.add(mapping)

    if payload.is_preferred:
        preferred = db.scalars(
            select(SupplierProduct).where(
                SupplierProduct.company_id == actor.company_id,
                SupplierProduct.product_id == payload.product_id,
                SupplierProduct.supplier_id != supplier_id,
            )
        ).all()
        for other in preferred:
            other.is_preferred = False

    mapping.last_unit_cost = payload.last_unit_cost
    mapping.minimum_order_quantity = payload.minimum_order_quantity
    mapping.lead_time_days = payload.lead_time_days
    mapping.is_preferred = payload.is_preferred
    db.flush()

    record_audit(
        db,
        request=request,
        action="supplier_product.upserted",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="supplier_product",
        resource_id=mapping.id,
        metadata={
            "supplier_id": str(supplier_id),
            "product_id": str(payload.product_id),
            "preferred": payload.is_preferred,
        },
    )
    db.commit()
    db.refresh(mapping)
    return mapping


def list_supplier_products(db: Session, company_id: UUID, supplier_id: UUID) -> list[SupplierProduct]:
    return list(
        db.scalars(
            select(SupplierProduct)
            .where(SupplierProduct.company_id == company_id, SupplierProduct.supplier_id == supplier_id)
            .order_by(SupplierProduct.updated_at.desc())
        ).all()
    )


def create_purchase_order(
    db: Session,
    actor: User,
    payload: PurchaseOrderCreate,
    request=None,
) -> PurchaseOrder:
    supplier = _get_supplier(db, actor.company_id, payload.supplier_id)
    _get_warehouse(db, actor.company_id, payload.warehouse_id)

    subtotal = Decimal("0")
    items: list[PurchaseOrderItem] = []
    seen_products: set[UUID] = set()

    for item_payload in payload.items:
        if item_payload.product_id in seen_products:
            raise HTTPException(status_code=422, detail="The same product cannot appear twice in a purchase order")
        seen_products.add(item_payload.product_id)
        product = _get_product(db, actor.company_id, item_payload.product_id)

        supplier_product = db.scalar(
            select(SupplierProduct).where(
                SupplierProduct.company_id == actor.company_id,
                SupplierProduct.supplier_id == supplier.id,
                SupplierProduct.product_id == product.id,
            )
        )
        unit_cost = item_payload.unit_cost
        if unit_cost is None:
            if supplier_product is not None and supplier_product.last_unit_cost > 0:
                unit_cost = supplier_product.last_unit_cost
            else:
                unit_cost = product.cost

        line_total = (Decimal(unit_cost) * item_payload.quantity).quantize(Decimal("0.01"))
        subtotal += line_total
        items.append(
            PurchaseOrderItem(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity_ordered=item_payload.quantity,
                quantity_received=0,
                unit_cost=unit_cost,
                line_total=line_total,
            )
        )

    if payload.discount > subtotal:
        raise HTTPException(status_code=422, detail="Discount cannot exceed purchase order subtotal")

    purchase_order = PurchaseOrder(
        company_id=actor.company_id,
        supplier_id=supplier.id,
        warehouse_id=payload.warehouse_id,
        buyer_user_id=actor.id,
        order_number=_generate_order_number(),
        status="draft",
        subtotal=subtotal,
        discount=payload.discount,
        total=subtotal - payload.discount,
        expected_date=payload.expected_date,
        notes=payload.notes,
        items=items,
    )
    db.add(purchase_order)
    db.flush()

    record_audit(
        db,
        request=request,
        action="purchase_order.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="purchase_order",
        resource_id=purchase_order.id,
        metadata={
            "order_number": purchase_order.order_number,
            "supplier_id": str(supplier.id),
            "total": str(purchase_order.total),
        },
    )
    db.commit()
    return get_purchase_order(db, actor.company_id, purchase_order.id)


def list_purchase_orders(db: Session, company_id: UUID, status_filter: str | None = None) -> list[PurchaseOrder]:
    stmt = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.company_id == company_id)
        .order_by(PurchaseOrder.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(PurchaseOrder.status == status_filter)
    return list(db.scalars(stmt).unique().all())


def get_purchase_order(db: Session, company_id: UUID, order_id: UUID) -> PurchaseOrder:
    order = db.scalar(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == order_id, PurchaseOrder.company_id == company_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order


def update_purchase_order_status(
    db: Session,
    actor: User,
    order: PurchaseOrder,
    payload: PurchaseOrderStatusUpdate,
    request=None,
) -> PurchaseOrder:
    if payload.status not in ALLOWED_PO_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition purchase order from {order.status} to {payload.status}",
        )

    order.status = payload.status
    db.flush()
    record_audit(
        db,
        request=request,
        action="purchase_order.status_changed",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="purchase_order",
        resource_id=order.id,
        metadata={"order_number": order.order_number, "status": payload.status},
    )
    db.commit()
    return get_purchase_order(db, actor.company_id, order.id)


def receive_purchase_order(
    db: Session,
    actor: User,
    order: PurchaseOrder,
    payload: PurchaseReceiptCreate,
    request=None,
) -> PurchaseReceipt:
    if order.status not in {"approved", "partially_received"}:
        raise HTTPException(status_code=409, detail="Only approved or partially received orders can be received")

    supplier = _get_supplier(db, actor.company_id, order.supplier_id)

    if not payload.items:
        raise HTTPException(status_code=422, detail="At least one receipt item is required")

    items_by_id = {item.id: item for item in order.items}
    seen_items: set[UUID] = set()
    for item_payload in payload.items:
        if item_payload.purchase_order_item_id in seen_items:
            raise HTTPException(status_code=422, detail="The same purchase order item cannot be received twice")
        seen_items.add(item_payload.purchase_order_item_id)
        if item_payload.purchase_order_item_id not in items_by_id:
            raise HTTPException(status_code=404, detail="Purchase order item not found")

    receipt = PurchaseReceipt(
        company_id=actor.company_id,
        purchase_order_id=order.id,
        warehouse_id=order.warehouse_id,
        received_by_user_id=actor.id,
        receipt_number=f"GRN-{uuid4().hex[:12].upper()}",
        notes=payload.notes,
    )
    db.add(receipt)
    db.flush()

    for item_payload in payload.items:
        order_item = items_by_id[item_payload.purchase_order_item_id]
        remaining = order_item.quantity_ordered - order_item.quantity_received
        if item_payload.quantity > remaining:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot receive {item_payload.quantity} units; only {remaining} remain for {order_item.product_sku}",
            )

        unit_cost = item_payload.unit_cost if item_payload.unit_cost is not None else order_item.unit_cost
        line_total = (Decimal(unit_cost) * item_payload.quantity).quantize(Decimal("0.01"))

        _apply_movement(
            db,
            actor,
            warehouse_id=order.warehouse_id,
            product_id=order_item.product_id,
            movement_type="receipt",
            quantity=item_payload.quantity,
            reference_type="purchase_receipt",
            reference_id=receipt.id,
            notes=f"Receipt {receipt.receipt_number} for purchase order {order.order_number}",
        )

        receipt_item = PurchaseReceiptItem(
            receipt_id=receipt.id,
            purchase_order_item_id=order_item.id,
            product_id=order_item.product_id,
            quantity_received=item_payload.quantity,
            unit_cost=unit_cost,
            line_total=line_total,
        )
        db.add(receipt_item)
        order_item.quantity_received += item_payload.quantity

        product = _get_product(db, actor.company_id, order_item.product_id)
        # This is the current reference cost, not a formal inventory valuation method.
        product.cost = unit_cost

        supplier_product = db.scalar(
            select(SupplierProduct).where(
                SupplierProduct.company_id == actor.company_id,
                SupplierProduct.supplier_id == order.supplier_id,
                SupplierProduct.product_id == order_item.product_id,
            )
        )
        if supplier_product is None:
            supplier_product = SupplierProduct(
                company_id=actor.company_id,
                supplier_id=order.supplier_id,
                product_id=order_item.product_id,
                last_unit_cost=unit_cost,
            )
            db.add(supplier_product)
        supplier_product.last_unit_cost = unit_cost
        supplier_product.last_received_at = datetime.now(timezone.utc)

    db.flush()
    all_received = all(item.quantity_received == item.quantity_ordered for item in order.items)
    order.status = "received" if all_received else "partially_received"
    db.flush()

    record_audit(
        db,
        request=request,
        action="purchase_receipt.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="purchase_receipt",
        resource_id=receipt.id,
        metadata={
            "purchase_order_id": str(order.id),
            "receipt_number": receipt.receipt_number,
            "status_after_receipt": order.status,
        },
    )
    db.flush()
    receipt = db.scalar(
        select(PurchaseReceipt)
        .options(selectinload(PurchaseReceipt.items), selectinload(PurchaseReceipt.purchase_order))
        .where(PurchaseReceipt.id == receipt.id)
    )
    ensure_payable_for_purchase_receipt(db, actor, receipt, request=request, due_in_days=supplier.payment_terms_days)
    db.commit()
    return receipt
