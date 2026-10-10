from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    assignee_user_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal", index=True)
    source_type: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_user_id])
    assignee = relationship("User", foreign_keys=[assignee_user_id])
    sla = relationship("WorkflowSLA", back_populates="task", uselist=False, cascade="all, delete-orphan")
    approvals = relationship("WorkflowApproval", back_populates="task", cascade="all, delete-orphan", order_by="WorkflowApproval.created_at.desc()")
    escalations = relationship("WorkflowEscalation", back_populates="task", cascade="all, delete-orphan", order_by="WorkflowEscalation.created_at.desc()")
    comments = relationship("WorkflowComment", back_populates="task", cascade="all, delete-orphan", order_by="WorkflowComment.created_at.asc()")
    attachments = relationship("WorkflowAttachment", back_populates="task", cascade="all, delete-orphan", order_by="WorkflowAttachment.created_at.desc()")


class WorkflowSLA(Base):
    __tablename__ = "workflow_slas"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow_tasks.id", ondelete="CASCADE"), unique=True, index=True)
    target_minutes: Mapped[int] = mapped_column(Integer)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    breached: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    breached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("WorkflowTask", back_populates="sla")


class WorkflowApproval(Base):
    __tablename__ = "workflow_approvals"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow_tasks.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    approver_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("WorkflowTask", back_populates="approvals")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    approver = relationship("User", foreign_keys=[approver_user_id])


class WorkflowEscalation(Base):
    __tablename__ = "workflow_escalations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow_tasks.id", ondelete="CASCADE"), index=True)
    from_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    to_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("WorkflowTask", back_populates="escalations")
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])


class WorkflowComment(Base):
    __tablename__ = "workflow_comments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow_tasks.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("WorkflowTask", back_populates="comments")
    author = relationship("User")


class WorkflowAttachment(Base):
    __tablename__ = "workflow_attachments"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("workflow_tasks.id", ondelete="CASCADE"), index=True)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    object_key: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task = relationship("WorkflowTask", back_populates="attachments")
    uploaded_by = relationship("User")
