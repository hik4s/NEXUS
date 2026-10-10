from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.inventory import SalesOrderFulfillment, StockBalance, StockMovement, StockTransfer, Warehouse
from app.models.order import SalesOrder
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import StockMovementCreate, StockTransferCreate, WarehouseCreate


def _get_product(db: Session, company_id: UUID, product_id: UUID) -> Product:
    product = db.scalar(select(Product).where(Product.id == product_id, Product.company_id == company_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _get_warehouse(db: Session, company_id: UUID, warehouse_id: UUID) -> Warehouse:
    warehouse = db.scalar(
        select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.company_id == company_id)
    )
    if warehouse is None or not warehouse.is_active:
        raise HTTPException(status_code=404, detail="Warehouse not found or inactive")
    return warehouse


def _get_or_create_balance(db: Session, company_id: UUID, warehouse_id: UUID, product_id: UUID) -> StockBalance:
    stmt = select(StockBalance).where(
        StockBalance.company_id == company_id,
        StockBalance.warehouse_id == warehouse_id,
        StockBalance.product_id == product_id,
    ).with_for_update()
    balance = db.scalar(stmt)
    if balance is not None:
        return balance

    # Race-safe creation: the unique constraint is the final arbiter.
    try:
        with db.begin_nested():
            balance = StockBalance(
                company_id=company_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=0,
            )
            db.add(balance)
            db.flush()
    except IntegrityError:
        pass

    return db.scalar(stmt)


def _apply_movement(
    db: Session,
    actor: User,
    *,
    warehouse_id: UUID,
    product_id: UUID,
    movement_type: str,
    quantity: int,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    notes: str | None = None,
) -> StockMovement:
    _get_warehouse(db, actor.company_id, warehouse_id)
    _get_product(db, actor.company_id, product_id)
    balance = _get_or_create_balance(db, actor.company_id, warehouse_id, product_id)

    increases = movement_type in {"receipt", "adjustment_in", "sale_return", "transfer_in"}
    delta = quantity if increases else -quantity

    # Atomic balance update: the database evaluates the current quantity at write time.
    # This prevents lost updates when multiple workers receive/issue the same SKU concurrently.
    conditions = [StockBalance.id == balance.id]
    if delta < 0:
        conditions.append(StockBalance.quantity + delta >= 0)
    result = db.execute(
        update(StockBalance)
        .where(*conditions)
        .values(quantity=StockBalance.quantity + delta)
    )
    if result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock",
        )

    db.refresh(balance)
    movement = StockMovement(
        company_id=actor.company_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity=quantity,
        balance_after=balance.quantity,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        created_by_user_id=actor.id,
    )
    db.add(movement)
    db.flush()
    return movement


def create_warehouse(db: Session, actor: User, payload: WarehouseCreate, request=None) -> Warehouse:
    name = payload.name.strip()
    code = payload.code.strip().upper()
    if db.scalar(select(Warehouse).where(Warehouse.company_id == actor.company_id, Warehouse.name == name)):
        raise HTTPException(status_code=409, detail="Warehouse name already exists")
    if db.scalar(select(Warehouse).where(Warehouse.company_id == actor.company_id, Warehouse.code == code)):
        raise HTTPException(status_code=409, detail="Warehouse code already exists")

    warehouse = Warehouse(company_id=actor.company_id, name=name, code=code)
    db.add(warehouse)
    db.flush()
    record_audit(
        db,
        request=request,
        action="warehouse.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="warehouse",
        resource_id=warehouse.id,
        metadata={"name": warehouse.name, "code": warehouse.code},
    )
    db.commit()
    db.refresh(warehouse)
    return warehouse


def list_warehouses(db: Session, company_id: UUID) -> list[Warehouse]:
    stmt = select(Warehouse).where(Warehouse.company_id == company_id).order_by(Warehouse.name.asc())
    return list(db.scalars(stmt).all())


def create_movement(db: Session, actor: User, payload: StockMovementCreate, request=None) -> StockMovement:
    movement = _apply_movement(
        db,
        actor,
        warehouse_id=payload.warehouse_id,
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    record_audit(
        db,
        request=request,
        action="inventory.movement.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="stock_movement",
        resource_id=movement.id,
        metadata={
            "movement_type": movement.movement_type,
            "quantity": movement.quantity,
            "warehouse_id": str(movement.warehouse_id),
            "product_id": str(movement.product_id),
        },
    )
    db.commit()
    db.refresh(movement)
    return movement


def list_stock(db: Session, company_id: UUID, warehouse_id: UUID | None = None) -> list[StockBalance]:
    stmt = select(StockBalance).where(StockBalance.company_id == company_id).order_by(StockBalance.updated_at.desc())
    if warehouse_id is not None:
        stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)
    return list(db.scalars(stmt).all())


def create_transfer(db: Session, actor: User, payload: StockTransferCreate, request=None) -> StockTransfer:
    if payload.source_warehouse_id == payload.destination_warehouse_id:
        raise HTTPException(status_code=400, detail="Source and destination warehouses must differ")

    transfer = StockTransfer(
        company_id=actor.company_id,
        source_warehouse_id=payload.source_warehouse_id,
        destination_warehouse_id=payload.destination_warehouse_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        notes=payload.notes,
        created_by_user_id=actor.id,
        status="completed",
    )
    db.add(transfer)
    db.flush()

    _apply_movement(
        db,
        actor,
        warehouse_id=payload.source_warehouse_id,
        product_id=payload.product_id,
        movement_type="transfer_out",
        quantity=payload.quantity,
        reference_type="stock_transfer",
        reference_id=transfer.id,
        notes=payload.notes,
    )
    _apply_movement(
        db,
        actor,
        warehouse_id=payload.destination_warehouse_id,
        product_id=payload.product_id,
        movement_type="transfer_in",
        quantity=payload.quantity,
        reference_type="stock_transfer",
        reference_id=transfer.id,
        notes=payload.notes,
    )

    record_audit(
        db,
        request=request,
        action="inventory.transfer.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="stock_transfer",
        resource_id=transfer.id,
        metadata={
            "quantity": payload.quantity,
            "product_id": str(payload.product_id),
            "source_warehouse_id": str(payload.source_warehouse_id),
            "destination_warehouse_id": str(payload.destination_warehouse_id),
        },
    )
    db.commit()
    db.refresh(transfer)
    return transfer


def fulfill_sales_order(db: Session, actor: User, order: SalesOrder, warehouse_id: UUID, request=None) -> SalesOrderFulfillment:
    warehouse = _get_warehouse(db, actor.company_id, warehouse_id)
    if order.fulfillment is not None:
        raise HTTPException(status_code=409, detail="Sales order already has a fulfillment")

    # Validate the complete order before changing any stock.
    balances: dict[UUID, StockBalance] = {}
    for item in sorted(order.items, key=lambda candidate: str(candidate.product_id)):
        balance = _get_or_create_balance(db, actor.company_id, warehouse.id, item.product_id)
        balances[item.product_id] = balance
        if balance.quantity < item.quantity:
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient stock for product {item.product_sku}",
            )

    fulfillment = SalesOrderFulfillment(
        company_id=actor.company_id,
        order_id=order.id,
        warehouse_id=warehouse.id,
        status="fulfilled",
    )
    db.add(fulfillment)
    db.flush()

    for item in order.items:
        _apply_movement(
            db,
            actor,
            warehouse_id=warehouse.id,
            product_id=item.product_id,
            movement_type="sale",
            quantity=item.quantity,
            reference_type="sales_order",
            reference_id=order.id,
            notes=f"Sales order {order.order_number}",
        )

    record_audit(
        db,
        request=request,
        action="inventory.sales_order.fulfilled",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="sales_order",
        resource_id=order.id,
        metadata={"warehouse_id": str(warehouse.id), "order_number": order.order_number},
    )
    return fulfillment


def reverse_sales_order_fulfillment(db: Session, actor: User, order: SalesOrder, request=None) -> None:
    fulfillment = order.fulfillment
    if fulfillment is None or fulfillment.status == "reversed":
        return

    for item in order.items:
        _apply_movement(
            db,
            actor,
            warehouse_id=fulfillment.warehouse_id,
            product_id=item.product_id,
            movement_type="sale_return",
            quantity=item.quantity,
            reference_type="sales_order",
            reference_id=order.id,
            notes=f"Cancellation of sales order {order.order_number}",
        )

    fulfillment.status = "reversed"
    db.flush()
    record_audit(
        db,
        request=request,
        action="inventory.sales_order.fulfillment_reversed",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="sales_order",
        resource_id=order.id,
        metadata={"warehouse_id": str(fulfillment.warehouse_id), "order_number": order.order_number},
    )
