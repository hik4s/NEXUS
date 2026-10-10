from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.models.customer import Customer
from app.models.order import SalesOrder, SalesOrderItem
from app.models.product import Product
from app.models.user import User
from app.services.inventory_service import fulfill_sales_order, reverse_sales_order_fulfillment
from app.services.finance_service import cancel_receivable_for_sales_order, ensure_receivable_for_sales_order
from app.rbac.service import user_has_permission
from app.schemas.sales import SalesOrderCreate, SalesOrderStatusUpdate

ZERO = Decimal("0.00")
ALLOWED_TRANSITIONS = {
    "draft": {"confirmed", "cancelled"},
    "confirmed": {"cancelled"},
    "cancelled": set(),
}


def _get_product(db: Session, company_id: UUID, product_id: UUID) -> Product:
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


def _get_customer(db: Session, company_id: UUID, customer_id: UUID) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.company_id == company_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


def _assert_discount_permission(db: Session, actor: User, line_discount: Decimal, order_discount: Decimal) -> None:
    if (line_discount > ZERO or order_discount > ZERO) and not user_has_permission(
        db, actor.id, "sales:discount"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Discount permission required",
        )


def create_order(db: Session, actor: User, payload: SalesOrderCreate, request=None) -> SalesOrder:
    if payload.customer_id is not None:
        _get_customer(db, actor.company_id, payload.customer_id)

    _assert_discount_permission(db, actor, ZERO, payload.order_discount)

    product_ids = [item.product_id for item in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A product can appear only once per order",
        )

    order = SalesOrder(
        company_id=actor.company_id,
        customer_id=payload.customer_id,
        seller_user_id=actor.id,
        order_number=f"ORD-{uuid4().hex[:12].upper()}",
        status="draft",
        subtotal=ZERO,
        item_discount_total=ZERO,
        order_discount=payload.order_discount,
        total=ZERO,
        notes=payload.notes,
    )
    db.add(order)

    subtotal = ZERO
    item_discount_total = ZERO

    for item_payload in payload.items:
        product = _get_product(db, actor.company_id, item_payload.product_id)
        unit_price = product.price if item_payload.unit_price is None else item_payload.unit_price
        if item_payload.unit_price is not None and unit_price != product.price:
            if not user_has_permission(db, actor.id, "sales:discount"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Price override permission required",
                )
        gross_total = (unit_price * item_payload.quantity).quantize(Decimal("0.01"))
        line_discount = item_payload.line_discount
        _assert_discount_permission(db, actor, line_discount, ZERO)
        if line_discount > gross_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Line discount cannot exceed gross total for product {product.sku}",
            )
        line_total = gross_total - line_discount
        subtotal += gross_total
        item_discount_total += line_discount

        order.items.append(
            SalesOrderItem(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=item_payload.quantity,
                unit_price=unit_price,
                line_discount=line_discount,
                gross_total=gross_total,
                total=line_total,
            )
        )

    if payload.order_discount > subtotal - item_discount_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order discount cannot exceed the amount after item discounts",
        )

    order.subtotal = subtotal
    order.item_discount_total = item_discount_total
    order.total = subtotal - item_discount_total - payload.order_discount
    db.flush()
    record_audit(
        db,
        request=request,
        action="sales_order.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="sales_order",
        resource_id=order.id,
        metadata={
            "order_number": order.order_number,
            "status": order.status,
            "total": str(order.total),
        },
    )
    db.commit()
    return get_order(db, actor.company_id, order.id)


def get_order(db: Session, company_id: UUID, order_id: UUID) -> SalesOrder:
    order = db.scalar(
        select(SalesOrder)
        .options(selectinload(SalesOrder.items), selectinload(SalesOrder.fulfillment))
        .where(SalesOrder.id == order_id, SalesOrder.company_id == company_id)
    )
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def list_orders(db: Session, company_id: UUID, status_filter: str | None = None) -> list[SalesOrder]:
    stmt = (
        select(SalesOrder)
        .options(selectinload(SalesOrder.items), selectinload(SalesOrder.fulfillment))
        .where(SalesOrder.company_id == company_id)
        .order_by(SalesOrder.created_at.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(SalesOrder.status == status_filter)
    return list(db.scalars(stmt).unique().all())


def update_order_status(
    db: Session,
    actor: User,
    order: SalesOrder,
    payload: SalesOrderStatusUpdate,
    request=None,
) -> SalesOrder:
    if payload.status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition order from {order.status} to {payload.status}",
        )

    if order.status == "draft" and payload.status == "confirmed":
        if payload.warehouse_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="warehouse_id is required when confirming an order",
            )
        fulfill_sales_order(db, actor, order, payload.warehouse_id, request=request)
        ensure_receivable_for_sales_order(db, actor, order, request=request, due_in_days=payload.payment_terms_days)
    elif order.status == "confirmed" and payload.status == "cancelled":
        cancel_receivable_for_sales_order(db, actor, order, request=request)
        reverse_sales_order_fulfillment(db, actor, order, request=request)

    order.status = payload.status
    db.flush()
    record_audit(
        db,
        request=request,
        action="sales_order.status_changed",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="sales_order",
        resource_id=order.id,
        metadata={"order_number": order.order_number, "status": order.status},
    )
    db.commit()
    return get_order(db, actor.company_id, order.id)
