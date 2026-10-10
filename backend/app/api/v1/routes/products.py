from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.company import Company
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead
from app.services.product_service import create_product
from app.platform.service import apply_pagination_headers, paginate_statement

router = APIRouter(prefix="/companies/{company_id}/products")


def ensure_company_access(company_id: UUID, current_user: User) -> None:
    if company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create(
    company_id: UUID,
    payload: ProductCreate,
    request: Request,
    current_user: User = Depends(require_permission("products:write")),
    db: Session = Depends(get_db),
) -> Product:
    ensure_company_access(company_id, current_user)
    product = create_product(db, company_id, payload)
    from app.audit.service import record_audit
    record_audit(
        db,
        request=request,
        action="product.created",
        company_id=current_user.company_id,
        actor_user_id=current_user.id,
        resource_type="product",
        resource_id=product.id,
        metadata={"sku": product.sku, "name": product.name},
    )
    db.commit()
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    company_id: UUID,
    response: Response,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="name", pattern="^(name|sku|price)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    current_user: User = Depends(require_permission("products:read")),
    db: Session = Depends(get_db),
) -> list[Product]:
    ensure_company_access(company_id, current_user)
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    sort_map = {"name": Product.name, "sku": Product.sku, "price": Product.price}
    column = sort_map[sort_by]
    statement = select(Product).where(Product.company_id == company_id).order_by(column.asc() if sort_order == "asc" else column.desc())
    items, meta = paginate_statement(db, statement, page=page, page_size=page_size)
    apply_pagination_headers(response, meta)
    return items
