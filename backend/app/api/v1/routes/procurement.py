from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.procurement import PurchaseOrder, PurchaseReceipt, Supplier, SupplierProduct
from app.models.user import User
from app.schemas.procurement import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    PurchaseOrderStatusUpdate,
    PurchaseReceiptCreate,
    PurchaseReceiptRead,
    SupplierCreate,
    SupplierProductRead,
    SupplierProductUpsert,
    SupplierRead,
)
from app.services.procurement_service import (
    create_purchase_order,
    create_supplier,
    get_purchase_order,
    list_purchase_orders,
    list_supplier_products,
    list_suppliers,
    receive_purchase_order,
    update_purchase_order_status,
    upsert_supplier_product,
)

router = APIRouter(prefix="/procurement")


@router.get("/suppliers", response_model=list[SupplierRead])
def get_suppliers(
    current_user: User = Depends(require_permission("procurement:read")),
    db: Session = Depends(get_db),
) -> list[Supplier]:
    return list_suppliers(db, current_user.company_id)


@router.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier_route(
    payload: SupplierCreate,
    request: Request,
    current_user: User = Depends(require_permission("procurement:write")),
    db: Session = Depends(get_db),
) -> Supplier:
    return create_supplier(db, current_user, payload, request=request)


@router.get("/suppliers/{supplier_id}/products", response_model=list[SupplierProductRead])
def get_supplier_products(
    supplier_id: UUID,
    current_user: User = Depends(require_permission("procurement:read")),
    db: Session = Depends(get_db),
) -> list[SupplierProduct]:
    return list_supplier_products(db, current_user.company_id, supplier_id)


@router.put("/suppliers/{supplier_id}/products", response_model=SupplierProductRead)
def upsert_supplier_product_route(
    supplier_id: UUID,
    payload: SupplierProductUpsert,
    request: Request,
    current_user: User = Depends(require_permission("procurement:write")),
    db: Session = Depends(get_db),
) -> SupplierProduct:
    return upsert_supplier_product(db, current_user, supplier_id, payload, request=request)


@router.get("/purchase-orders", response_model=list[PurchaseOrderRead])
def get_purchase_orders(
    status_filter: str | None = None,
    current_user: User = Depends(require_permission("procurement:read")),
    db: Session = Depends(get_db),
) -> list[PurchaseOrder]:
    return list_purchase_orders(db, current_user.company_id, status_filter=status_filter)


@router.post("/purchase-orders", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order_route(
    payload: PurchaseOrderCreate,
    request: Request,
    current_user: User = Depends(require_permission("procurement:write")),
    db: Session = Depends(get_db),
) -> PurchaseOrder:
    return create_purchase_order(db, current_user, payload, request=request)


@router.get("/purchase-orders/{order_id}", response_model=PurchaseOrderRead)
def get_purchase_order_route(
    order_id: UUID,
    current_user: User = Depends(require_permission("procurement:read")),
    db: Session = Depends(get_db),
) -> PurchaseOrder:
    return get_purchase_order(db, current_user.company_id, order_id)


@router.patch("/purchase-orders/{order_id}/status", response_model=PurchaseOrderRead)
def update_purchase_order_status_route(
    order_id: UUID,
    payload: PurchaseOrderStatusUpdate,
    request: Request,
    current_user: User = Depends(require_permission("procurement:approve")),
    db: Session = Depends(get_db),
) -> PurchaseOrder:
    order = get_purchase_order(db, current_user.company_id, order_id)
    return update_purchase_order_status(db, current_user, order, payload, request=request)


@router.post("/purchase-orders/{order_id}/receipts", response_model=PurchaseReceiptRead, status_code=status.HTTP_201_CREATED)
def receive_purchase_order_route(
    order_id: UUID,
    payload: PurchaseReceiptCreate,
    request: Request,
    current_user: User = Depends(require_permission("procurement:receive")),
    db: Session = Depends(get_db),
) -> PurchaseReceipt:
    order = get_purchase_order(db, current_user.company_id, order_id)
    return receive_purchase_order(db, current_user, order, payload, request=request)
