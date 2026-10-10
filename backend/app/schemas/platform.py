from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=list, max_length=50)


class ApiKeyRead(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    revoked_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, model: Any) -> "ApiKeyRead":
        return cls(
            id=model.id,
            name=model.name,
            key_prefix=model.key_prefix,
            scopes=model.scopes or [],
            revoked_at=model.revoked_at,
            last_used_at=model.last_used_at,
            created_at=model.created_at,
        )


class ApiKeyCreateResponse(ApiKeyRead):
    secret: str


class WebhookEndpointCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    url: HttpUrl
    subscribed_events: list[str] = Field(min_length=1, max_length=50)
    max_attempts: int = Field(default=5, ge=1, le=20)


class WebhookEndpointRead(BaseModel):
    id: UUID
    name: str
    url: str
    secret_fingerprint: str
    subscribed_events: list[str]
    max_attempts: int
    active: bool
    created_at: datetime


class WebhookEndpointCreateResponse(WebhookEndpointRead):
    secret: str


class WebhookDeliveryRead(BaseModel):
    id: UUID
    endpoint_id: UUID
    event_name: str
    payload: dict
    signature: str
    status: str
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class WebhookTestEvent(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    payload: dict = Field(default_factory=dict)
