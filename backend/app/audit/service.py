from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    request: Request | None,
    action: str,
    company_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: UUID | str | None = None,
    status: str = "success",
    metadata: dict | None = None,
) -> AuditLog:
    client_host = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None
    if request is not None:
        metadata = {**(metadata or {}), "request_id": getattr(request.state, "request_id", None)}
    log = AuditLog(
        company_id=company_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        status=status,
        ip_address=client_host,
        user_agent=user_agent,
        metadata_json=metadata,
    )
    db.add(log)
    return log
