from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AccountType = Literal["cash", "bank", "card", "other"]
FinancialStatus = Literal["pending", "partially_paid", "paid", "overdue", "cancelled"]
TransactionType = Literal["income", "expense"]


class FinancialAccountCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    account_type: AccountType = "cash"
    opening_balance: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=2)


class FinancialAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    account_type: AccountType
    opening_balance: Decimal
    current_balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ReceivableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    customer_id: UUID | None
    sales_order_id: UUID | None
    description: str
    amount: Decimal
    paid_amount: Decimal
    due_date: date
    status: FinancialStatus
    created_at: datetime
    updated_at: datetime


class PayableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    supplier_id: UUID | None
    purchase_order_id: UUID | None
    purchase_receipt_id: UUID | None
    description: str
    amount: Decimal
    paid_amount: Decimal
    due_date: date
    status: FinancialStatus
    created_at: datetime
    updated_at: datetime


class PaymentCreate(BaseModel):
    account_id: UUID
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    payment_date: date = Field(default_factory=date.today)
    notes: str | None = Field(default=None, max_length=500)


class FinancialTransactionCreate(BaseModel):
    account_id: UUID
    transaction_type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    transaction_date: date = Field(default_factory=date.today)
    category: str | None = Field(default=None, max_length=100)
    description: str = Field(min_length=2, max_length=240)


class FinancialTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    account_id: UUID
    receivable_id: UUID | None
    payable_id: UUID | None
    transaction_type: TransactionType
    amount: Decimal
    transaction_date: date
    category: str | None
    description: str
    reference_type: str | None
    reference_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


class FinancialSummaryRead(BaseModel):
    total_cash: Decimal
    accounts_receivable_open: Decimal
    accounts_payable_open: Decimal
    overdue_receivable: Decimal
    overdue_payable: Decimal
