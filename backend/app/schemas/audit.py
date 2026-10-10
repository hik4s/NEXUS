from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuditLogRead(BaseModel):
    id: UUID
    company_id: UUID | None
    actor_user_id: UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    status: str
    ip_address: str | None
    user_agent: str | None
    metadata: dict | None = Field(default=None, alias="metadata_json")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}
