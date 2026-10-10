from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


PurchaseOrderStatus = Literal[
    "draft",
    "submitted",
    "approved",
    "partially_received",
    "received",
    "cancelled",
]


class SupplierCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    legal_name: str | None = Field(default=None, max_length=220)
    tax_id: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    payment_terms_days: int = Field(default=0, ge=0, le=3650)
    notes: str | None = Field(default=None, max_length=3000)


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    legal_name: str | None
    tax_id: str | None
    email: EmailStr | None
    phone: str | None
    payment_terms_days: int
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SupplierProductUpsert(BaseModel):
    product_id: UUID
    last_unit_cost: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=2)
    minimum_order_quantity: int = Field(default=1, gt=0, le=1_000_000)
    lead_time_days: int = Field(default=0, ge=0, le=3650)
    is_preferred: bool = False


class SupplierProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_id: UUID
    product_id: UUID
    last_unit_cost: Decimal
    minimum_order_quantity: int
    lead_time_days: int
    is_preferred: bool
    last_received_at: datetime | None


class PurchaseOrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=1_000_000)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    warehouse_id: UUID
    expected_date: date | None = None
    discount: Decimal = Field(default=0, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=5000)
    items: list[PurchaseOrderItemCreate] = Field(min_length=1, max_length=200)


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal
    line_total: Decimal


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    supplier_id: UUID
    warehouse_id: UUID
    buyer_user_id: UUID
    order_number: str
    status: PurchaseOrderStatus
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    expected_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemRead] = Field(default_factory=list)


class PurchaseReceiptItemCreate(BaseModel):
    purchase_order_item_id: UUID
    quantity: int = Field(gt=0, le=1_000_000)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class PurchaseReceiptCreate(BaseModel):
    items: list[PurchaseReceiptItemCreate] = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)


class PurchaseReceiptItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    purchase_order_item_id: UUID
    product_id: UUID
    quantity_received: int
    unit_cost: Decimal
    line_total: Decimal


class PurchaseReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    purchase_order_id: UUID
    warehouse_id: UUID
    received_by_user_id: UUID
    receipt_number: str
    received_at: datetime
    notes: str | None
    items: list[PurchaseReceiptItemRead] = Field(default_factory=list)
