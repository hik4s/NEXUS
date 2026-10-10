from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.finance import AccountsPayable, AccountsReceivable, FinancialAccount, FinancialTransaction
from app.models.user import User
from app.schemas.finance import FinancialAccountCreate, FinancialAccountRead, FinancialSummaryRead, FinancialTransactionCreate, FinancialTransactionRead, PayableRead, PaymentCreate, ReceivableRead
from app.services.finance_service import create_account, create_transaction, list_accounts, list_payables, list_receivables, list_transactions, pay_payable, pay_receivable, summary

router = APIRouter(prefix="/finance")


@router.get("/accounts", response_model=list[FinancialAccountRead])
def get_accounts(current_user: User = Depends(require_permission("finance:read")), db: Session = Depends(get_db)) -> list[FinancialAccount]:
    return list_accounts(db, current_user.company_id)


@router.post("/accounts", response_model=FinancialAccountRead, status_code=status.HTTP_201_CREATED)
def create_financial_account(payload: FinancialAccountCreate, request: Request, current_user: User = Depends(require_permission("finance:write")), db: Session = Depends(get_db)) -> FinancialAccount:
    return create_account(db, current_user, payload, request=request)


@router.get("/receivables", response_model=list[ReceivableRead])
def get_receivables(status_filter: str | None = None, current_user: User = Depends(require_permission("finance:read")), db: Session = Depends(get_db)) -> list[AccountsReceivable]:
    return list_receivables(db, current_user.company_id, status_filter)


@router.post("/receivables/{receivable_id}/pay", response_model=ReceivableRead)
def pay_receivable_route(receivable_id: UUID, payload: PaymentCreate, request: Request, current_user: User = Depends(require_permission("finance:pay")), db: Session = Depends(get_db)) -> AccountsReceivable:
    return pay_receivable(db, current_user, receivable_id, payload, request=request)


@router.get("/payables", response_model=list[PayableRead])
def get_payables(status_filter: str | None = None, current_user: User = Depends(require_permission("finance:read")), db: Session = Depends(get_db)) -> list[AccountsPayable]:
    return list_payables(db, current_user.company_id, status_filter)


@router.post("/payables/{payable_id}/pay", response_model=PayableRead)
def pay_payable_route(payable_id: UUID, payload: PaymentCreate, request: Request, current_user: User = Depends(require_permission("finance:pay")), db: Session = Depends(get_db)) -> AccountsPayable:
    return pay_payable(db, current_user, payable_id, payload, request=request)


@router.get("/transactions", response_model=list[FinancialTransactionRead])
def get_transactions(current_user: User = Depends(require_permission("finance:read")), db: Session = Depends(get_db)) -> list[FinancialTransaction]:
    return list_transactions(db, current_user.company_id)


@router.post("/transactions", response_model=FinancialTransactionRead, status_code=status.HTTP_201_CREATED)
def create_financial_transaction(payload: FinancialTransactionCreate, request: Request, current_user: User = Depends(require_permission("finance:write")), db: Session = Depends(get_db)) -> FinancialTransaction:
    return create_transaction(db, current_user, payload, request=request)


@router.get("/summary", response_model=FinancialSummaryRead)
def get_financial_summary(current_user: User = Depends(require_permission("finance:read")), db: Session = Depends(get_db)) -> dict[str, object]:
    return summary(db, current_user.company_id)
