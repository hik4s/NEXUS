from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead

router = APIRouter(prefix="/audit-logs")


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    current_user: User = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[AuditLogRead]:
    logs = db.scalars(
        select(AuditLog)
        .where(AuditLog.company_id == current_user.company_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    ).all()
    return [AuditLogRead.model_validate(log) for log in logs]
