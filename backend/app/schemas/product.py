from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    sku: str = Field(min_length=1, max_length=80)
    price: Decimal = Field(default=0, ge=0)
    cost: Decimal = Field(default=0, ge=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    sku: str
    price: Decimal
    cost: Decimal
