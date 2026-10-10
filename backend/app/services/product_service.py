from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.product import Product
from app.schemas.product import ProductCreate


def create_product(db: Session, company_id: UUID, payload: ProductCreate) -> Product:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    duplicate = db.scalar(
        select(Product).where(Product.company_id == company_id, Product.sku == payload.sku)
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists for this company")

    product = Product(company_id=company_id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
