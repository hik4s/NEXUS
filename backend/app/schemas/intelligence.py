
from datetime import datetime
from uuid import UUID
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict

class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=12000)

class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: str
    content: str | None
    provider: str | None
    model: str | None
    usage_json: dict[str, Any] | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    user_id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]

class ActionProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    conversation_id: UUID | None
    proposed_by_user_id: UUID
    approved_by_user_id: UUID | None
    action_type: str
    title: str
    description: str
    parameters_json: dict[str, Any]
    status: str
    result_json: dict[str, Any] | None
    rejection_reason: str | None
    created_at: datetime
    approved_at: datetime | None
    executed_at: datetime | None

class ActionReject(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)
