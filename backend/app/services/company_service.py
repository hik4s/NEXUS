from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.schemas.company import CompanyCreate


def create_company(db: Session, payload: CompanyCreate) -> Company:
    if db.scalar(select(Company).where(Company.slug == payload.slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company slug already exists")

    if db.scalar(select(Company).where(Company.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company name already exists")

    company = Company(name=payload.name, slug=payload.slug)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company
