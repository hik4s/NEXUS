
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.finance import AccountsPayable, AccountsReceivable, FinancialAccount
from app.models.inventory import StockBalance
from app.models.order import SalesOrder
from app.models.procurement import SupplierProduct
from app.models.product import Product


def _money(value: Decimal | int | float | None) -> float:
    return round(float(value or 0), 2)


def sales_summary(db: Session, company_id: UUID, days: int = 30) -> dict:
    since = date.today() - timedelta(days=days)
    revenue = db.scalar(
        select(func.coalesce(func.sum(SalesOrder.total), 0)).where(
            SalesOrder.company_id == company_id,
            SalesOrder.status == "confirmed",
            SalesOrder.created_at >= since,
        )
    ) or Decimal("0")
    orders = db.scalar(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.company_id == company_id,
            SalesOrder.status == "confirmed",
            SalesOrder.created_at >= since,
        )
    ) or 0
    average_ticket = revenue / orders if orders else Decimal("0")
    return {"period_days": days, "revenue": _money(revenue), "orders": int(orders), "average_ticket": _money(average_ticket)}


def inventory_summary(db: Session, company_id: UUID) -> dict:
    rows = db.execute(
        select(
            Product.id,
            Product.name,
            Product.sku,
            Product.cost,
            func.coalesce(func.sum(StockBalance.quantity), 0).label("quantity"),
        )
        .join(StockBalance, StockBalance.product_id == Product.id, isouter=True)
        .where(Product.company_id == company_id)
        .group_by(Product.id)
        .order_by(Product.name)
    ).all()
    total_units = sum(int(r.quantity or 0) for r in rows)
    inventory_value = sum((Decimal(r.cost or 0) * int(r.quantity or 0) for r in rows), Decimal("0"))
    critical = [
        {"product_id": str(r.id), "name": r.name, "sku": r.sku, "quantity": int(r.quantity or 0)}
        for r in rows if int(r.quantity or 0) <= 0
    ]
    return {"product_count": len(rows), "total_units": total_units, "inventory_value": _money(inventory_value), "critical_items": critical[:20]}


def cash_summary(db: Session, company_id: UUID) -> dict:
    cash = db.scalar(
        select(func.coalesce(func.sum(FinancialAccount.current_balance), 0)).where(
            FinancialAccount.company_id == company_id, FinancialAccount.is_active.is_(True)
        )
    ) or Decimal("0")
    open_receivables = db.scalars(select(AccountsReceivable).where(AccountsReceivable.company_id == company_id)).all()
    open_payables = db.scalars(select(AccountsPayable).where(AccountsPayable.company_id == company_id)).all()
    receivable_open = sum((i.amount - i.paid_amount for i in open_receivables if i.status not in {"paid", "cancelled"}), Decimal("0"))
    payable_open = sum((i.amount - i.paid_amount for i in open_payables if i.status not in {"paid", "cancelled"}), Decimal("0"))
    return {"cash": _money(cash), "open_receivables": _money(receivable_open), "open_payables": _money(payable_open), "net_exposure": _money(cash + receivable_open - payable_open)}


def overdue_receivables(db: Session, company_id: UUID) -> dict:
    items = list(db.scalars(select(AccountsReceivable).where(AccountsReceivable.company_id == company_id)).all())
    overdue = [i for i in items if i.status == "overdue" or (i.due_date < date.today() and i.paid_amount < i.amount)]
    amount = sum((i.amount - i.paid_amount for i in overdue), Decimal("0"))
    return {"count": len(overdue), "amount": _money(amount), "items": [{"id": str(i.id), "description": i.description, "due_date": i.due_date.isoformat(), "remaining": _money(i.amount - i.paid_amount)} for i in overdue[:20]]}


def supplier_price_overview(db: Session, company_id: UUID) -> dict:
    rows = db.execute(
        select(SupplierProduct.product_id, Product.name, Product.sku, func.min(SupplierProduct.last_unit_cost), func.max(SupplierProduct.last_unit_cost))
        .join(Product, Product.id == SupplierProduct.product_id)
        .where(SupplierProduct.company_id == company_id)
        .group_by(SupplierProduct.product_id, Product.name, Product.sku)
        .order_by(Product.name)
    ).all()
    return {"items": [{"product_id": str(r[0]), "name": r[1], "sku": r[2], "min_cost": _money(r[3]), "max_cost": _money(r[4])} for r in rows[:50]]}
