from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_financial_account_company_name"),
        CheckConstraint("opening_balance >= 0", name="ck_financial_account_opening_nonnegative"),
        CheckConstraint("current_balance >= 0", name="ck_financial_account_balance_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(140), index=True)
    account_type: Mapped[str] = mapped_column(String(30), default="cash", index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AccountsReceivable(Base):
    __tablename__ = "accounts_receivable"
    __table_args__ = (
        UniqueConstraint("company_id", "sales_order_id", name="uq_ar_company_sales_order"),
        CheckConstraint("amount > 0", name="ck_ar_amount_positive"),
        CheckConstraint("paid_amount >= 0", name="ck_ar_paid_nonnegative"),
        CheckConstraint("paid_amount <= amount", name="ck_ar_paid_lte_amount"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sales_order_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(String(220))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AccountsPayable(Base):
    __tablename__ = "accounts_payable"
    __table_args__ = (
        UniqueConstraint("company_id", "purchase_receipt_id", name="uq_ap_company_purchase_receipt"),
        CheckConstraint("amount > 0", name="ck_ap_amount_positive"),
        CheckConstraint("paid_amount >= 0", name="ck_ap_paid_nonnegative"),
        CheckConstraint("paid_amount <= amount", name="ck_ap_paid_lte_amount"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    supplier_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    purchase_order_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    purchase_receipt_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("purchase_receipts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(String(220))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("financial_accounts.id", ondelete="RESTRICT"), index=True
    )
    receivable_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts_receivable.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payable_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts_payable.id", ondelete="SET NULL"), nullable=True, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    transaction_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[str] = mapped_column(String(240))
    reference_type: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    reference_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
