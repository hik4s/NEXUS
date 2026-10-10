from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyRead

router = APIRouter(prefix="/companies")


@router.get("/me", response_model=CompanyRead)
def get_my_company(
    current_user: User = Depends(require_permission("company:read")),
    db: Session = Depends(get_db),
) -> Company:
    company = db.get(Company, current_user.company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: UUID,
    current_user: User = Depends(require_permission("company:read")),
    db: Session = Depends(get_db),
) -> Company:
    if company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
