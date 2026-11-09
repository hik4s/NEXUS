from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImportIssue(BaseModel):
    row: int
    field: str | None = None
    code: str
    message: str


class ParsedOrderItem(BaseModel):
    sku: str
    quantity: int


class ParsedOrder(BaseModel):
    external_order_id: str
    items: list[ParsedOrderItem] = Field(default_factory=list)
    source_lines: list[int] = Field(default_factory=list)
    errors: list[ImportIssue] = Field(default_factory=list)


class ParsedOrderFile(BaseModel):
    orders: list[ParsedOrder] = Field(default_factory=list)
    unassigned_errors: list[ImportIssue] = Field(default_factory=list)


class ImportEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    external_order_id: str
    source_lines: list[int]
    normalized_items: list[dict]
    errors: list[ImportIssue]
    warnings: list[ImportIssue]
    status: str
    sales_order_id: UUID | None


class ImportBatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    sha256: str
    status: str
    created_at: datetime


class ImportBatchRead(ImportBatchSummary):
    unassigned_errors: list[ImportIssue]
    entries: list[ImportEntryRead]


class CommitReviewRequest(BaseModel):
    entry_ids: list[UUID] = Field(min_length=1, max_length=100)


class CommitOrderResult(BaseModel):
    entry_id: UUID
    order_id: UUID
    reused: bool


class CommitReviewResult(BaseModel):
    batch_id: UUID
    orders: list[CommitOrderResult]
