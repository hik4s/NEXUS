from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


CustomerStatus = Literal["active", "inactive"]
LeadStatus = Literal["new", "qualified", "proposal", "won", "lost"]
InteractionType = Literal["note", "call", "email", "meeting", "message"]
InteractionChannel = Literal["internal", "phone", "email", "whatsapp", "other"]


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_id: str | None = Field(default=None, max_length=40)
    status: CustomerStatus = "active"
    source: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    tax_id: str | None = Field(default=None, max_length=40)
    status: CustomerStatus | None = None
    source: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    email: EmailStr | None
    phone: str | None
    tax_id: str | None
    status: CustomerStatus
    source: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    customer_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=80)
    status: LeadStatus = "new"
    expected_value: Decimal = Field(default=0, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    customer_id: UUID | None = None
    assigned_to_user_id: UUID | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=80)
    status: LeadStatus | None = None
    expected_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = None


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    customer_id: UUID | None
    assigned_to_user_id: UUID | None
    name: str
    email: EmailStr | None
    phone: str | None
    source: str | None
    status: LeadStatus
    expected_value: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class InteractionCreate(BaseModel):
    customer_id: UUID | None = None
    lead_id: UUID | None = None
    type: InteractionType = "note"
    channel: InteractionChannel = "internal"
    subject: str | None = Field(default=None, max_length=180)
    content: str = Field(min_length=1, max_length=10000)
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def require_target(self) -> "InteractionCreate":
        if self.customer_id is None and self.lead_id is None:
            raise ValueError("customer_id or lead_id is required")
        if self.customer_id is not None and self.lead_id is not None:
            raise ValueError("Provide only one interaction target")
        return self


class InteractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    customer_id: UUID | None
    lead_id: UUID | None
    actor_user_id: UUID
    type: InteractionType
    channel: InteractionChannel
    subject: str | None
    content: str
    occurred_at: datetime
    created_at: datetime
