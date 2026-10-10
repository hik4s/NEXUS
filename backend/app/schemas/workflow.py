from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["pending", "in_progress", "blocked", "completed", "cancelled"]
TaskPriority = Literal["low", "normal", "high", "urgent"]
ApprovalStatus = Literal["pending", "approved", "rejected"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    assignee_user_id: UUID | None = None
    priority: TaskPriority = "normal"
    due_at: datetime | None = None
    source_type: str | None = Field(default=None, max_length=60)
    source_id: str | None = Field(default=None, max_length=80)
    sla_minutes: int | None = Field(default=None, gt=0, le=60 * 24 * 30)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    assignee_user_id: UUID | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class SLARead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    target_minutes: int
    deadline_at: datetime
    breached: bool
    breached_at: datetime | None


class ApprovalCreate(BaseModel):
    approver_user_id: UUID


class ApprovalDecision(BaseModel):
    status: Literal["approved", "rejected"]
    decision_note: str | None = Field(default=None, max_length=3000)


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    requested_by_user_id: UUID
    approver_user_id: UUID
    status: ApprovalStatus
    decision_note: str | None
    decided_at: datetime | None
    created_at: datetime


class EscalationCreate(BaseModel):
    to_user_id: UUID
    reason: str = Field(min_length=2, max_length=3000)


class EscalationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    from_user_id: UUID
    to_user_id: UUID
    reason: str
    level: int
    created_at: datetime


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    author_user_id: UUID
    body: str
    created_at: datetime


class AttachmentCreate(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    object_key: str = Field(min_length=1, max_length=500)
    mime_type: str | None = Field(default=None, max_length=120)
    size_bytes: int | None = Field(default=None, ge=0)


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    task_id: UUID
    uploaded_by_user_id: UUID
    file_name: str
    object_key: str
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    created_by_user_id: UUID
    assignee_user_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    source_type: str | None
    source_id: str | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    sla: SLARead | None
    approvals: list[ApprovalRead]
    escalations: list[EscalationRead]
    comments: list[CommentRead]
    attachments: list[AttachmentRead]
