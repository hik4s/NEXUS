from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.models.user import User
from app.models.workflow import WorkflowApproval, WorkflowAttachment, WorkflowComment, WorkflowEscalation, WorkflowSLA, WorkflowTask
from app.rbac.service import user_has_permission
from app.schemas.workflow import ApprovalCreate, ApprovalDecision, AttachmentCreate, CommentCreate, EscalationCreate, TaskCreate, TaskUpdate

TASK_TRANSITIONS = {
    "pending": {"in_progress", "cancelled", "blocked"},
    "in_progress": {"blocked", "completed", "cancelled", "pending"},
    "blocked": {"in_progress", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _user(db: Session, company_id: UUID, user_id: UUID) -> User:
    user = db.scalar(select(User).where(User.id == user_id, User.company_id == company_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_task(db: Session, company_id: UUID, task_id: UUID) -> WorkflowTask:
    task = db.scalar(
        select(WorkflowTask)
        .options(
            selectinload(WorkflowTask.sla),
            selectinload(WorkflowTask.approvals),
            selectinload(WorkflowTask.escalations),
            selectinload(WorkflowTask.comments),
            selectinload(WorkflowTask.attachments),
        )
        .where(WorkflowTask.id == task_id, WorkflowTask.company_id == company_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def list_tasks(db: Session, company_id: UUID, status_filter: str | None = None) -> list[WorkflowTask]:
    stmt = (
        select(WorkflowTask)
        .options(selectinload(WorkflowTask.sla),
            selectinload(WorkflowTask.approvals),
            selectinload(WorkflowTask.escalations),
            selectinload(WorkflowTask.comments),
            selectinload(WorkflowTask.attachments))
        .where(WorkflowTask.company_id == company_id)
        .order_by(WorkflowTask.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(WorkflowTask.status == status_filter)
    return list(db.scalars(stmt).all())


def create_task(db: Session, actor: User, payload: TaskCreate, request=None) -> WorkflowTask:
    if payload.assignee_user_id:
        _user(db, actor.company_id, payload.assignee_user_id)
    task = WorkflowTask(
        company_id=actor.company_id,
        created_by_user_id=actor.id,
        assignee_user_id=payload.assignee_user_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_at=payload.due_at,
        source_type=payload.source_type,
        source_id=payload.source_id,
    )
    db.add(task)
    db.flush()
    if payload.sla_minutes is not None:
        deadline = datetime.now(timezone.utc) + timedelta(minutes=payload.sla_minutes)
        db.add(WorkflowSLA(company_id=actor.company_id, task_id=task.id, target_minutes=payload.sla_minutes, deadline_at=deadline))
    record_audit(db, request=request, action="workflow.task.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_task", resource_id=task.id, metadata={"status": task.status, "priority": task.priority})
    db.commit()
    return get_task(db, actor.company_id, task.id)


def update_task(db: Session, actor: User, task: WorkflowTask, payload: TaskUpdate, request=None) -> WorkflowTask:
    if payload.assignee_user_id is not None:
        _user(db, actor.company_id, payload.assignee_user_id)
        task.assignee_user_id = payload.assignee_user_id
    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.due_at is not None:
        task.due_at = payload.due_at
    db.flush()
    record_audit(db, request=request, action="workflow.task.updated", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_task", resource_id=task.id, metadata={"assignee_user_id": str(task.assignee_user_id) if task.assignee_user_id else None})
    db.commit()
    return get_task(db, actor.company_id, task.id)


def update_task_status(db: Session, actor: User, task: WorkflowTask, new_status: str, request=None) -> WorkflowTask:
    if new_status not in TASK_TRANSITIONS.get(task.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition task from {task.status} to {new_status}")
    task.status = new_status
    db.flush()
    record_audit(db, request=request, action="workflow.task.status_changed", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_task", resource_id=task.id, metadata={"status": new_status})
    db.commit()
    return get_task(db, actor.company_id, task.id)


def request_approval(db: Session, actor: User, task: WorkflowTask, payload: ApprovalCreate, request=None) -> WorkflowApproval:
    approver = _user(db, actor.company_id, payload.approver_user_id)
    if approver.id == actor.id:
        raise HTTPException(status_code=400, detail="A user cannot approve their own request")
    if db.scalar(select(WorkflowApproval).where(WorkflowApproval.task_id == task.id, WorkflowApproval.status == "pending")):
        raise HTTPException(status_code=409, detail="Task already has a pending approval")
    approval = WorkflowApproval(company_id=actor.company_id, task_id=task.id, requested_by_user_id=actor.id, approver_user_id=approver.id)
    db.add(approval); db.flush()
    record_audit(db, request=request, action="workflow.approval.requested", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_approval", resource_id=approval.id, metadata={"task_id": str(task.id), "approver_user_id": str(approver.id)})
    db.commit(); db.refresh(approval); return approval


def decide_approval(db: Session, actor: User, approval: WorkflowApproval, payload: ApprovalDecision, request=None) -> WorkflowApproval:
    if approval.approver_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Only the assigned approver can decide this approval")
    if approval.status != "pending":
        raise HTTPException(status_code=409, detail="Approval has already been decided")
    approval.status = payload.status
    approval.decision_note = payload.decision_note
    approval.decided_at = datetime.now(timezone.utc)
    db.flush()
    record_audit(db, request=request, action="workflow.approval.decided", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_approval", resource_id=approval.id, metadata={"status": approval.status, "task_id": str(approval.task_id)})
    db.commit(); db.refresh(approval); return approval


def add_escalation(db: Session, actor: User, task: WorkflowTask, payload: EscalationCreate, request=None) -> WorkflowEscalation:
    if not user_has_permission(db, actor.id, "workflow:escalate"):
        raise HTTPException(status_code=403, detail="Workflow escalation permission required")
    to_user = _user(db, actor.company_id, payload.to_user_id)
    if to_user.id == actor.id:
        raise HTTPException(status_code=400, detail="Task cannot be escalated to the same user")
    current_level = db.scalar(select(WorkflowEscalation.level).where(WorkflowEscalation.task_id == task.id).order_by(WorkflowEscalation.level.desc()).limit(1)) or 0
    escalation = WorkflowEscalation(company_id=actor.company_id, task_id=task.id, from_user_id=actor.id, to_user_id=to_user.id, reason=payload.reason, level=current_level + 1)
    db.add(escalation); task.assignee_user_id = to_user.id; db.flush()
    record_audit(db, request=request, action="workflow.task.escalated", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_task", resource_id=task.id, metadata={"to_user_id": str(to_user.id), "level": escalation.level})
    db.commit(); db.refresh(escalation); return escalation


def add_comment(db: Session, actor: User, task: WorkflowTask, payload: CommentCreate, request=None) -> WorkflowComment:
    comment = WorkflowComment(company_id=actor.company_id, task_id=task.id, author_user_id=actor.id, body=payload.body)
    db.add(comment); db.flush()
    record_audit(db, request=request, action="workflow.comment.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_comment", resource_id=comment.id)
    db.commit(); db.refresh(comment); return comment


def add_attachment(db: Session, actor: User, task: WorkflowTask, payload: AttachmentCreate, request=None) -> WorkflowAttachment:
    attachment = WorkflowAttachment(company_id=actor.company_id, task_id=task.id, uploaded_by_user_id=actor.id, file_name=payload.file_name, object_key=payload.object_key, mime_type=payload.mime_type, size_bytes=payload.size_bytes)
    db.add(attachment); db.flush()
    record_audit(db, request=request, action="workflow.attachment.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="workflow_attachment", resource_id=attachment.id, metadata={"file_name": attachment.file_name})
    db.commit(); db.refresh(attachment); return attachment
