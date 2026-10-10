from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class IntegrationCreate(BaseModel):
    provider: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=140)
    base_url: HttpUrl | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    provider: str
    name: str
    base_url: str | None
    credential_fingerprint: str | None
    config: dict[str, Any]
    status: str
    last_health_at: datetime | None
    last_error: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class IntegrationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    integration_id: UUID
    level: str
    event: str
    message: str
    details: dict[str, Any] | None
    created_at: datetime


class FileAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    storage_backend: str
    storage_key: str
    content_type: str
    size_bytes: int
    sha256: str
    metadata_json: dict[str, Any]
    created_at: datetime


class ImportRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    entity: str
    mode: str
    status: str
    file_asset_id: UUID
    job_id: UUID | None
    total_rows: int
    valid_rows: int
    imported_rows: int
    skipped_rows: int
    error_rows: int
    errors: list
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
