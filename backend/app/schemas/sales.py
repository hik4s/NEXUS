from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


OrderStatus = Literal["draft", "confirmed", "cancelled"]


class SalesOrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, le=1_000_000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    line_discount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)


class SalesOrderCreate(BaseModel):
    customer_id: UUID | None = None
    order_discount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=5000)
    items: list[SalesOrderItemCreate] = Field(min_length=1, max_length=200)


class SalesOrderStatusUpdate(BaseModel):
    status: OrderStatus
    warehouse_id: UUID | None = None
    payment_terms_days: int = Field(default=0, ge=0, le=3650)


class SalesOrderFulfillmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    warehouse_id: UUID
    status: str


class SalesOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    line_discount: Decimal
    gross_total: Decimal
    total: Decimal


class SalesOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    customer_id: UUID | None
    seller_user_id: UUID
    order_number: str
    status: OrderStatus
    subtotal: Decimal
    item_discount_total: Decimal
    order_discount: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime
    items: list[SalesOrderItemRead] = Field(default_factory=list)
    fulfillment: SalesOrderFulfillmentRead | None = None
