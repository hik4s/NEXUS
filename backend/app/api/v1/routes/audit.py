from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.platform.service import apply_pagination_headers, paginate_statement

router = APIRouter(prefix="/audit-logs")


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    response: Response,
    current_user: User = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1, le=100),
) -> list[AuditLogRead]:
    logs, meta = paginate_statement(db,
        select(AuditLog)
        .where(AuditLog.company_id == current_user.company_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc()),
        page=page, page_size=page_size or limit,
    )
    apply_pagination_headers(response, meta)
    return [AuditLogRead.model_validate(log) for log in logs]
