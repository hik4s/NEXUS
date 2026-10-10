from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_supplier_company_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(220), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (
        UniqueConstraint("supplier_id", "product_id", name="uq_supplier_product"),
        CheckConstraint("last_unit_cost >= 0", name="ck_supplier_product_cost_nonnegative"),
        CheckConstraint("minimum_order_quantity > 0", name="ck_supplier_product_min_qty_positive"),
        CheckConstraint("lead_time_days >= 0", name="ck_supplier_product_lead_time_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    last_unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    minimum_order_quantity: Mapped[int] = mapped_column(default=1)
    lead_time_days: Mapped[int] = mapped_column(default=0)
    is_preferred: Mapped[bool] = mapped_column(default=False, index=True)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "order_number", name="uq_purchase_order_company_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    warehouse_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    buyer_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    order_number: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        "PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan"
    )
    supplier = relationship("Supplier")
    warehouse = relationship("Warehouse")
    buyer = relationship("User")
    receipts: Mapped[list["PurchaseReceipt"]] = relationship(
        "PurchaseReceipt", back_populates="purchase_order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    product_name: Mapped[str] = mapped_column(String(180))
    product_sku: Mapped[str] = mapped_column(String(80))
    quantity_ordered: Mapped[int] = mapped_column()
    quantity_received: Mapped[int] = mapped_column(default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    purchase_order_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True
    )
    warehouse_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("warehouses.id", ondelete="RESTRICT"), index=True)
    received_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    receipt_number: Mapped[str] = mapped_column(String(40), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="receipts")
    items: Mapped[list["PurchaseReceiptItem"]] = relationship(
        "PurchaseReceiptItem", back_populates="receipt", cascade="all, delete-orphan"
    )


class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("purchase_receipts.id", ondelete="CASCADE"), index=True
    )
    purchase_order_item_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("purchase_order_items.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    quantity_received: Mapped[int] = mapped_column()
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    receipt: Mapped["PurchaseReceipt"] = relationship("PurchaseReceipt", back_populates="items")
    purchase_order_item = relationship("PurchaseOrderItem")
    product = relationship("Product")
