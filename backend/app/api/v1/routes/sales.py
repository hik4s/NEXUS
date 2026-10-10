from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.order import SalesOrder
from app.models.user import User
from app.schemas.sales import SalesOrderCreate, SalesOrderRead, SalesOrderStatusUpdate
from app.services.sales_service import create_order, get_order, list_orders, update_order_status
from app.platform.service import abort_idempotency, begin_idempotency, complete_idempotency, apply_pagination_headers, paginate_statement
from app.models.order import SalesOrder
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/sales")


@router.post("/orders", response_model=SalesOrderRead, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    payload: SalesOrderCreate,
    request: Request,
    current_user: User = Depends(require_permission("sales:write")),
    db: Session = Depends(get_db),
):
    record, cached = begin_idempotency(db, current_user, request, request.headers.get("Idempotency-Key"), payload.model_dump(mode="json"))
    if cached is not None:
        return cached
    try:
        order = create_order(db, current_user, payload, request=request)
        body = SalesOrderRead.model_validate(order).model_dump(mode="json")
        if record is not None:
            complete_idempotency(db, record, status.HTTP_201_CREATED, body)
        return order
    except Exception:
        if record is not None:
            abort_idempotency(db, record)
        raise


@router.get("/orders", response_model=list[SalesOrderRead])
def list_sales_orders(
    response: Response,
    status_filter: Literal["draft", "confirmed", "cancelled"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|total|status)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(require_permission("sales:read")),
    db: Session = Depends(get_db),
) -> list[SalesOrder]:
    stmt = select(SalesOrder).options(selectinload(SalesOrder.items), selectinload(SalesOrder.fulfillment)).where(SalesOrder.company_id == current_user.company_id)
    if status_filter is not None:
        stmt = stmt.where(SalesOrder.status == status_filter)
    sort_map = {"created_at": SalesOrder.created_at, "total": SalesOrder.total, "status": SalesOrder.status}
    column = sort_map[sort_by]
    stmt = stmt.order_by(column.asc() if sort_order == "asc" else column.desc())
    items, meta = paginate_statement(db, stmt, page=page, page_size=page_size)
    apply_pagination_headers(response, meta)
    # joined relationships are already loaded; unique is required for ORM row de-duplication.
    return items


@router.get("/orders/{order_id}", response_model=SalesOrderRead)
def get_sales_order(
    order_id: UUID,
    current_user: User = Depends(require_permission("sales:read")),
    db: Session = Depends(get_db),
) -> SalesOrder:
    return get_order(db, current_user.company_id, order_id)


@router.patch("/orders/{order_id}/status", response_model=SalesOrderRead)
def change_sales_order_status(
    order_id: UUID,
    payload: SalesOrderStatusUpdate,
    request: Request,
    current_user: User = Depends(require_permission("sales:confirm")),
    db: Session = Depends(get_db),
) -> SalesOrder:
    order = get_order(db, current_user.company_id, order_id)
    return update_order_status(db, current_user, order, payload, request=request)
