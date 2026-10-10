from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DeliveryStatus = Literal["pending", "assigned", "in_transit", "delivered", "failed", "cancelled"]
RouteStatus = Literal["planned", "in_progress", "completed", "cancelled"]


class DriverCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    license_number: str = Field(min_length=3, max_length=40)
    user_id: UUID | None = None


class DriverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    user_id: UUID | None
    full_name: str
    phone: str | None
    license_number: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=5, max_length=20)
    vehicle_type: str = Field(default="van", min_length=2, max_length=40)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    capacity_kg: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    plate: str
    vehicle_type: str
    brand: str | None
    model: str | None
    capacity_kg: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DeliveryCreate(BaseModel):
    sales_order_id: UUID
    recipient_name: str = Field(min_length=2, max_length=160)
    recipient_phone: str | None = Field(default=None, max_length=40)
    postal_code: str | None = Field(default=None, max_length=20)
    street: str = Field(min_length=2, max_length=180)
    number: str = Field(min_length=1, max_length=30)
    complement: str | None = Field(default=None, max_length=120)
    neighborhood: str | None = Field(default=None, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=80)
    scheduled_at: datetime | None = None


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    proof_type: str | None = Field(default=None, max_length=30)
    proof_reference: str | None = Field(default=None, max_length=4000)
    failure_reason: str | None = Field(default=None, max_length=2000)
    description: str | None = Field(default=None, max_length=2000)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)


class DeliveryAssign(BaseModel):
    driver_id: UUID
    vehicle_id: UUID


class TrackingEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    description: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    occurred_at: datetime
    created_by_user_id: UUID


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    sales_order_id: UUID
    warehouse_id: UUID
    driver_id: UUID | None
    vehicle_id: UUID | None
    route_id: UUID | None
    tracking_code: str
    status: DeliveryStatus
    recipient_name: str
    recipient_phone: str | None
    postal_code: str | None
    street: str
    number: str
    complement: str | None
    neighborhood: str | None
    city: str
    state: str
    scheduled_at: datetime | None
    dispatched_at: datetime | None
    delivered_at: datetime | None
    failure_reason: str | None
    proof_type: str | None
    proof_reference: str | None
    created_at: datetime
    updated_at: datetime


class RouteCreate(BaseModel):
    warehouse_id: UUID
    driver_id: UUID
    vehicle_id: UUID
    route_date: date
    notes: str | None = Field(default=None, max_length=2000)


class RouteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    warehouse_id: UUID
    driver_id: UUID
    vehicle_id: UUID
    route_number: str
    route_date: date
    status: RouteStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RouteStatusUpdate(BaseModel):
    status: RouteStatus


class RouteStopCreate(BaseModel):
    delivery_id: UUID
    sequence: int = Field(ge=1, le=1000)


class RouteStopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    route_id: UUID
    delivery_id: UUID
    sequence: int
    status: str
    created_at: datetime
