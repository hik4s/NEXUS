from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.inventory import StockBalance, Warehouse, StockMovement
from app.models.product import Product
from app.models.user import User
from app.schemas.inventory import (
    StockBalanceRead,
    StockMovementCreate,
    StockMovementRead,
    StockTransferCreate,
    StockTransferRead,
    WarehouseCreate,
    WarehouseRead,
)
from app.services.inventory_service import create_movement, create_transfer, create_warehouse, list_stock, list_warehouses

router = APIRouter(prefix="/inventory")


@router.get("/warehouses", response_model=list[WarehouseRead])
def get_warehouses(
    current_user: User = Depends(require_permission("inventory:read")),
    db: Session = Depends(get_db),
) -> list[Warehouse]:
    return list_warehouses(db, current_user.company_id)


@router.post("/warehouses", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def create_warehouse_route(
    payload: WarehouseCreate,
    request: Request,
    current_user: User = Depends(require_permission("inventory:write")),
    db: Session = Depends(get_db),
) -> Warehouse:
    return create_warehouse(db, current_user, payload, request=request)


@router.get("/stock", response_model=list[StockBalanceRead])
def get_stock(
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    current_user: User = Depends(require_permission("inventory:read")),
    db: Session = Depends(get_db),
) -> list[StockBalanceRead]:
    balances = list_stock(db, current_user.company_id, warehouse_id=warehouse_id)
    if product_id is not None:
        balances = [balance for balance in balances if balance.product_id == product_id]

    products = db.scalars(
        select(Product).where(Product.company_id == current_user.company_id)
    ).all()
    products_by_id = {product.id: product for product in products}
    return [
        StockBalanceRead(
            warehouse_id=balance.warehouse_id,
            product_id=balance.product_id,
            quantity=balance.quantity,
            product_name=products_by_id[balance.product_id].name,
            product_sku=products_by_id[balance.product_id].sku,
        )
        for balance in balances
    ]


@router.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_movement_route(
    payload: StockMovementCreate,
    request: Request,
    current_user: User = Depends(require_permission("inventory:adjust")),
    db: Session = Depends(get_db),
) -> StockMovement:
    return create_movement(db, current_user, payload, request=request)


@router.get("/movements", response_model=list[StockMovementRead])
def get_movements(
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    limit: int = 50,
    current_user: User = Depends(require_permission("inventory:read")),
    db: Session = Depends(get_db),
) -> list[StockMovement]:
    stmt = (
        select(StockMovement)
        .where(StockMovement.company_id == current_user.company_id)
        .order_by(StockMovement.created_at.desc())
        .limit(min(max(limit, 1), 100))
    )
    if warehouse_id is not None:
        stmt = stmt.where(StockMovement.warehouse_id == warehouse_id)
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    return list(db.scalars(stmt).all())


@router.post("/transfers", response_model=StockTransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer_route(
    payload: StockTransferCreate,
    request: Request,
    current_user: User = Depends(require_permission("inventory:transfer")),
    db: Session = Depends(get_db),
) -> StockTransferRead:
    return create_transfer(db, current_user, payload, request=request)
