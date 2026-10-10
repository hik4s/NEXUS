from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.finance import AccountsPayable, AccountsReceivable, FinancialAccount, FinancialTransaction
from app.models.order import SalesOrder
from app.models.procurement import PurchaseReceipt
from app.models.user import User
from app.schemas.finance import FinancialAccountCreate, FinancialTransactionCreate, PaymentCreate


def _account(db: Session, company_id: UUID, account_id: UUID) -> FinancialAccount:
    account = db.scalar(select(FinancialAccount).where(FinancialAccount.id == account_id, FinancialAccount.company_id == company_id))
    if account is None or not account.is_active:
        raise HTTPException(status_code=404, detail="Financial account not found or inactive")
    return account


def _normalize_status(item: AccountsReceivable | AccountsPayable) -> None:
    if item.status in {"paid", "cancelled"}:
        return
    if item.paid_amount >= item.amount:
        item.status = "paid"
    elif item.paid_amount > 0:
        item.status = "partially_paid"
    elif item.due_date < date.today():
        item.status = "overdue"
    else:
        item.status = "pending"


def list_accounts(db: Session, company_id: UUID) -> list[FinancialAccount]:
    return list(db.scalars(select(FinancialAccount).where(FinancialAccount.company_id == company_id).order_by(FinancialAccount.name)).all())


def create_account(db: Session, actor: User, payload: FinancialAccountCreate, request=None) -> FinancialAccount:
    if db.scalar(select(FinancialAccount).where(FinancialAccount.company_id == actor.company_id, FinancialAccount.name == payload.name.strip())):
        raise HTTPException(status_code=409, detail="Financial account name already exists")
    balance = payload.opening_balance.quantize(Decimal("0.01"))
    account = FinancialAccount(
        company_id=actor.company_id,
        name=payload.name.strip(),
        account_type=payload.account_type,
        opening_balance=balance,
        current_balance=balance,
    )
    db.add(account)
    db.flush()
    record_audit(db, request=request, action="finance.account.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="financial_account", resource_id=account.id, metadata={"name": account.name})
    db.commit()
    db.refresh(account)
    return account


def list_receivables(db: Session, company_id: UUID, status_filter: str | None = None) -> list[AccountsReceivable]:
    items = list(db.scalars(select(AccountsReceivable).where(AccountsReceivable.company_id == company_id).order_by(AccountsReceivable.due_date, AccountsReceivable.created_at)).all())
    for item in items:
        _normalize_status(item)
    if items:
        db.commit()
    if status_filter:
        return [item for item in items if item.status == status_filter]
    return items


def list_payables(db: Session, company_id: UUID, status_filter: str | None = None) -> list[AccountsPayable]:
    items = list(db.scalars(select(AccountsPayable).where(AccountsPayable.company_id == company_id).order_by(AccountsPayable.due_date, AccountsPayable.created_at)).all())
    for item in items:
        _normalize_status(item)
    if items:
        db.commit()
    if status_filter:
        return [item for item in items if item.status == status_filter]
    return items


def list_transactions(db: Session, company_id: UUID) -> list[FinancialTransaction]:
    return list(db.scalars(select(FinancialTransaction).where(FinancialTransaction.company_id == company_id).order_by(FinancialTransaction.transaction_date.desc(), FinancialTransaction.created_at.desc())).all())


def create_transaction(db: Session, actor: User, payload: FinancialTransactionCreate, request=None) -> FinancialTransaction:
    account = _account(db, actor.company_id, payload.account_id)
    if payload.transaction_type == "expense" and account.current_balance < payload.amount:
        raise HTTPException(status_code=409, detail="Insufficient balance for this expense")
    delta = payload.amount if payload.transaction_type == "income" else -payload.amount
    account.current_balance = (account.current_balance + delta).quantize(Decimal("0.01"))
    transaction = FinancialTransaction(
        company_id=actor.company_id,
        account_id=account.id,
        transaction_type=payload.transaction_type,
        amount=payload.amount,
        transaction_date=payload.transaction_date,
        category=payload.category,
        description=payload.description,
        created_by_user_id=actor.id,
    )
    db.add(transaction)
    db.flush()
    record_audit(db, request=request, action="finance.transaction.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="financial_transaction", resource_id=transaction.id, metadata={"type": payload.transaction_type, "amount": str(payload.amount)})
    db.commit()
    db.refresh(transaction)
    return transaction


def ensure_receivable_for_sales_order(db: Session, actor: User, order: SalesOrder, request=None, due_in_days: int = 0) -> AccountsReceivable:
    existing = db.scalar(select(AccountsReceivable).where(AccountsReceivable.company_id == actor.company_id, AccountsReceivable.sales_order_id == order.id))
    if existing is not None:
        return existing
    if order.total <= 0:
        raise HTTPException(status_code=409, detail="Sales order total must be positive to create a receivable")
    receivable = AccountsReceivable(
        company_id=actor.company_id,
        customer_id=order.customer_id,
        sales_order_id=order.id,
        description=f"Sales order {order.order_number}",
        amount=order.total,
        due_date=date.today() + timedelta(days=due_in_days),
        status="pending",
        paid_amount=Decimal("0.00"),
    )
    db.add(receivable)
    db.flush()
    record_audit(db, request=request, action="finance.receivable.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="accounts_receivable", resource_id=receivable.id, metadata={"sales_order_id": str(order.id), "amount": str(order.total)})
    return receivable


def cancel_receivable_for_sales_order(db: Session, actor: User, order: SalesOrder, request=None) -> None:
    receivable = db.scalar(select(AccountsReceivable).where(AccountsReceivable.company_id == actor.company_id, AccountsReceivable.sales_order_id == order.id))
    if receivable is None or receivable.status == "cancelled":
        return
    if receivable.paid_amount > 0:
        raise HTTPException(status_code=409, detail="A sales order with received payments cannot be cancelled")
    receivable.status = "cancelled"
    record_audit(db, request=request, action="finance.receivable.cancelled", company_id=actor.company_id, actor_user_id=actor.id, resource_type="accounts_receivable", resource_id=receivable.id, metadata={"sales_order_id": str(order.id)})


def ensure_payable_for_purchase_receipt(db: Session, actor: User, receipt: PurchaseReceipt, request=None, due_in_days: int = 0) -> AccountsPayable:
    existing = db.scalar(select(AccountsPayable).where(AccountsPayable.company_id == actor.company_id, AccountsPayable.purchase_receipt_id == receipt.id))
    if existing is not None:
        return existing
    total = sum((item.line_total for item in receipt.items), Decimal("0.00"))
    if total <= 0:
        raise HTTPException(status_code=409, detail="Purchase receipt total must be positive to create a payable")
    order = receipt.purchase_order
    payable = AccountsPayable(
        company_id=actor.company_id,
        supplier_id=order.supplier_id,
        purchase_order_id=order.id,
        purchase_receipt_id=receipt.id,
        description=f"Purchase receipt {receipt.receipt_number}",
        amount=total,
        due_date=date.today() + timedelta(days=due_in_days),
        status="pending",
        paid_amount=Decimal("0.00"),
    )
    db.add(payable)
    db.flush()
    record_audit(db, request=request, action="finance.payable.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="accounts_payable", resource_id=payable.id, metadata={"purchase_receipt_id": str(receipt.id), "amount": str(total)})
    return payable


def _get_receivable(db: Session, company_id: UUID, item_id: UUID) -> AccountsReceivable:
    item = db.scalar(select(AccountsReceivable).where(AccountsReceivable.id == item_id, AccountsReceivable.company_id == company_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Receivable not found")
    _normalize_status(item)
    return item


def _get_payable(db: Session, company_id: UUID, item_id: UUID) -> AccountsPayable:
    item = db.scalar(select(AccountsPayable).where(AccountsPayable.id == item_id, AccountsPayable.company_id == company_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Payable not found")
    _normalize_status(item)
    return item


def pay_receivable(db: Session, actor: User, receivable_id: UUID, payload: PaymentCreate, request=None) -> AccountsReceivable:
    receivable = _get_receivable(db, actor.company_id, receivable_id)
    if receivable.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled receivable cannot be paid")
    if receivable.status == "paid":
        raise HTTPException(status_code=409, detail="Receivable is already fully paid")
    remaining = receivable.amount - receivable.paid_amount
    amount = remaining if payload.amount is None else payload.amount
    if amount > remaining:
        raise HTTPException(status_code=409, detail="Payment exceeds receivable remaining balance")
    account = _account(db, actor.company_id, payload.account_id)
    account.current_balance = (account.current_balance + amount).quantize(Decimal("0.01"))
    receivable.paid_amount += amount
    _normalize_status(receivable)
    transaction = FinancialTransaction(company_id=actor.company_id, account_id=account.id, receivable_id=receivable.id, transaction_type="income", amount=amount, transaction_date=payload.payment_date, description=payload.notes or receivable.description, reference_type="accounts_receivable", reference_id=receivable.id, created_by_user_id=actor.id)
    db.add(transaction)
    db.flush()
    record_audit(db, request=request, action="finance.receivable.paid", company_id=actor.company_id, actor_user_id=actor.id, resource_type="accounts_receivable", resource_id=receivable.id, metadata={"amount": str(amount), "status": receivable.status})
    db.commit()
    db.refresh(receivable)
    return receivable


def pay_payable(db: Session, actor: User, payable_id: UUID, payload: PaymentCreate, request=None) -> AccountsPayable:
    payable = _get_payable(db, actor.company_id, payable_id)
    if payable.status == "cancelled":
        raise HTTPException(status_code=409, detail="Cancelled payable cannot be paid")
    if payable.status == "paid":
        raise HTTPException(status_code=409, detail="Payable is already fully paid")
    remaining = payable.amount - payable.paid_amount
    amount = remaining if payload.amount is None else payload.amount
    if amount > remaining:
        raise HTTPException(status_code=409, detail="Payment exceeds payable remaining balance")
    account = _account(db, actor.company_id, payload.account_id)
    if account.current_balance < amount:
        raise HTTPException(status_code=409, detail="Insufficient balance to pay payable")
    account.current_balance = (account.current_balance - amount).quantize(Decimal("0.01"))
    payable.paid_amount += amount
    _normalize_status(payable)
    transaction = FinancialTransaction(company_id=actor.company_id, account_id=account.id, payable_id=payable.id, transaction_type="expense", amount=amount, transaction_date=payload.payment_date, description=payload.notes or payable.description, reference_type="accounts_payable", reference_id=payable.id, created_by_user_id=actor.id)
    db.add(transaction)
    db.flush()
    record_audit(db, request=request, action="finance.payable.paid", company_id=actor.company_id, actor_user_id=actor.id, resource_type="accounts_payable", resource_id=payable.id, metadata={"amount": str(amount), "status": payable.status})
    db.commit()
    db.refresh(payable)
    return payable


def summary(db: Session, company_id: UUID) -> dict[str, Decimal]:
    receivables = list(db.scalars(select(AccountsReceivable).where(AccountsReceivable.company_id == company_id)).all())
    payables = list(db.scalars(select(AccountsPayable).where(AccountsPayable.company_id == company_id)).all())
    for item in receivables + payables:
        _normalize_status(item)
    db.commit()
    accounts_total = db.scalar(select(func.coalesce(func.sum(FinancialAccount.current_balance), 0)).where(FinancialAccount.company_id == company_id, FinancialAccount.is_active == True)) or Decimal("0")
    open_ar = sum((item.amount - item.paid_amount for item in receivables if item.status not in {"paid", "cancelled"}), Decimal("0"))
    open_ap = sum((item.amount - item.paid_amount for item in payables if item.status not in {"paid", "cancelled"}), Decimal("0"))
    overdue_ar = sum((item.amount - item.paid_amount for item in receivables if item.status == "overdue"), Decimal("0"))
    overdue_ap = sum((item.amount - item.paid_amount for item in payables if item.status == "overdue"), Decimal("0"))
    return {"total_cash": accounts_total, "accounts_receivable_open": open_ar, "accounts_payable_open": open_ap, "overdue_receivable": overdue_ar, "overdue_payable": overdue_ap}
