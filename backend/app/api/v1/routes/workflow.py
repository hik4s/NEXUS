from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.user import User
from app.models.workflow import WorkflowApproval
from app.schemas.workflow import ApprovalCreate, ApprovalDecision, ApprovalRead, AttachmentCreate, AttachmentRead, CommentCreate, CommentRead, EscalationCreate, EscalationRead, TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate
from app.services.workflow_service import add_attachment, add_comment, add_escalation, create_task, decide_approval, get_task, list_tasks, request_approval, update_task, update_task_status

router = APIRouter(prefix="/workflow")


def _approval(db: Session, company_id: UUID, approval_id: UUID) -> WorkflowApproval:
    approval = db.scalar(select(WorkflowApproval).where(WorkflowApproval.id == approval_id, WorkflowApproval.company_id == company_id))
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.get("/tasks", response_model=list[TaskRead])
def get_tasks(status_filter: str | None = None, current_user: User = Depends(require_permission("workflow:read")), db: Session = Depends(get_db)):
    return list_tasks(db, current_user.company_id, status_filter)


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def post_task(payload: TaskCreate, request: Request, current_user: User = Depends(require_permission("workflow:write")), db: Session = Depends(get_db)):
    return create_task(db, current_user, payload, request=request)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task_route(task_id: UUID, current_user: User = Depends(require_permission("workflow:read")), db: Session = Depends(get_db)):
    return get_task(db, current_user.company_id, task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def patch_task(task_id: UUID, payload: TaskUpdate, request: Request, current_user: User = Depends(require_permission("workflow:write")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return update_task(db, current_user, task, payload, request=request)


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
def patch_task_status(task_id: UUID, payload: TaskStatusUpdate, request: Request, current_user: User = Depends(require_permission("workflow:write")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return update_task_status(db, current_user, task, payload.status, request=request)


@router.post("/tasks/{task_id}/approvals", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
def post_approval(task_id: UUID, payload: ApprovalCreate, request: Request, current_user: User = Depends(require_permission("workflow:write")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return request_approval(db, current_user, task, payload, request=request)


@router.patch("/approvals/{approval_id}", response_model=ApprovalRead)
def patch_approval(approval_id: UUID, payload: ApprovalDecision, request: Request, current_user: User = Depends(require_permission("workflow:approve")), db: Session = Depends(get_db)):
    approval = _approval(db, current_user.company_id, approval_id)
    return decide_approval(db, current_user, approval, payload, request=request)


@router.post("/tasks/{task_id}/escalations", response_model=EscalationRead, status_code=status.HTTP_201_CREATED)
def post_escalation(task_id: UUID, payload: EscalationCreate, request: Request, current_user: User = Depends(require_permission("workflow:escalate")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return add_escalation(db, current_user, task, payload, request=request)


@router.post("/tasks/{task_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def post_comment(task_id: UUID, payload: CommentCreate, request: Request, current_user: User = Depends(require_permission("workflow:comment")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return add_comment(db, current_user, task, payload, request=request)


@router.post("/tasks/{task_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def post_attachment(task_id: UUID, payload: AttachmentCreate, request: Request, current_user: User = Depends(require_permission("workflow:write")), db: Session = Depends(get_db)):
    task = get_task(db, current_user.company_id, task_id)
    return add_attachment(db, current_user, task, payload, request=request)
