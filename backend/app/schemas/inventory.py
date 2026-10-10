from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


MovementType = Literal["receipt", "issue", "adjustment_in", "adjustment_out"]


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=40)


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StockMovementCreate(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    movement_type: MovementType
    quantity: int = Field(gt=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=1000)


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    warehouse_id: UUID
    product_id: UUID
    movement_type: str
    quantity: int
    balance_after: int
    reference_type: str | None
    reference_id: UUID | None
    notes: str | None
    created_by_user_id: UUID
    created_at: datetime


class StockBalanceRead(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    quantity: int
    product_name: str
    product_sku: str


class StockTransferCreate(BaseModel):
    source_warehouse_id: UUID
    destination_warehouse_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=1000)


class StockTransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    source_warehouse_id: UUID
    destination_warehouse_id: UUID
    product_id: UUID
    quantity: int
    status: str
    notes: str | None
    created_by_user_id: UUID
    created_at: datetime
