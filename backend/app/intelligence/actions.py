
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.models.intelligence import ActionProposal
from app.models.user import User
from app.schemas.workflow import TaskCreate
from app.services.workflow_service import create_task
from app.rbac.service import user_has_permission


def get_proposal(db: Session, company_id: UUID, proposal_id: UUID) -> ActionProposal:
    item = db.scalar(select(ActionProposal).where(ActionProposal.id == proposal_id, ActionProposal.company_id == company_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Action proposal not found")
    return item


def approve_proposal(db: Session, actor: User, proposal: ActionProposal, request=None):
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="Proposal is no longer pending")
    proposal.status = "approved"
    proposal.approved_by_user_id = actor.id
    proposal.approved_at = datetime.now(timezone.utc)
    record_audit(db, request=request, action="intelligence.action.approved", company_id=actor.company_id, actor_user_id=actor.id, resource_type="action_proposal", resource_id=proposal.id)
    db.commit(); db.refresh(proposal)
    return proposal


def reject_proposal(db: Session, actor: User, proposal: ActionProposal, reason: str, request=None):
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="Proposal is no longer pending")
    proposal.status = "rejected"
    proposal.rejection_reason = reason
    proposal.approved_by_user_id = actor.id
    proposal.approved_at = datetime.now(timezone.utc)
    record_audit(db, request=request, action="intelligence.action.rejected", company_id=actor.company_id, actor_user_id=actor.id, resource_type="action_proposal", resource_id=proposal.id)
    db.commit(); db.refresh(proposal)
    return proposal


def execute_proposal(db: Session, actor: User, proposal: ActionProposal, request=None):
    if proposal.status != "approved":
        raise HTTPException(status_code=409, detail="Proposal must be approved before execution")
    if not user_has_permission(db, actor.id, "workflow:write"):
        raise HTTPException(status_code=403, detail="Workflow write permission required for execution")
    if proposal.action_type == "workflow.create_task":
        params = proposal.parameters_json or {}
        payload = TaskCreate(title=params["title"], description=params.get("description"), priority=params.get("priority", "normal"), source_type="ai_action", source_id=str(proposal.id))
        task = create_task(db, actor, payload, request=request)
        result = {"task_id": str(task.id), "status": task.status}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action type: {proposal.action_type}")
    proposal.status = "executed"
    proposal.executed_at = datetime.now(timezone.utc)
    proposal.result_json = result
    record_audit(db, request=request, action="intelligence.action.executed", company_id=actor.company_id, actor_user_id=actor.id, resource_type="action_proposal", resource_id=proposal.id, metadata=result)
    db.commit(); db.refresh(proposal)
    return proposal
