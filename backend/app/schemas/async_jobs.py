from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    kind: str = Field(min_length=2, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    delay_seconds: int = Field(default=0, ge=0, le=86400)
    max_attempts: int = Field(default=3, ge=1, le=20)
    idempotency_key: str | None = Field(default=None, max_length=160)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    kind: str
    payload: dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    available_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    result: dict[str, Any] | None
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime


class JobScheduleCreate(BaseModel):
    kind: str = Field(min_length=2, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    interval_seconds: int = Field(ge=1, le=31536000)
    next_run_at: datetime | None = None


class JobScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID | None
    kind: str
    payload: dict[str, Any]
    interval_seconds: int
    next_run_at: datetime
    active: bool
    last_enqueued_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    user_id: UUID
    title: str
    body: str
    notification_type: str
    severity: str
    read_at: datetime | None
    action_url: str | None
    created_at: datetime
    updated_at: datetime
