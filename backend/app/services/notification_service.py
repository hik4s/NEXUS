from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.async_jobs import Notification


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_notification(
    db: Session,
    *,
    company_id: UUID,
    user_id: UUID,
    title: str,
    body: str,
    notification_type: str = "system",
    severity: str = "info",
    action_url: str | None = None,
) -> Notification:
    model = Notification(
        company_id=company_id,
        user_id=user_id,
        title=title,
        body=body,
        notification_type=notification_type,
        severity=severity,
        action_url=action_url,
    )
    db.add(model)
    db.flush()
    return model


def list_notifications(db: Session, company_id: UUID, user_id: UUID, unread_only: bool = False) -> list[Notification]:
    stmt = select(Notification).where(Notification.company_id == company_id, Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    stmt = stmt.order_by(Notification.created_at.desc())
    return list(db.scalars(stmt).all())


def mark_notification_read(db: Session, company_id: UUID, user_id: UUID, notification_id: UUID) -> Notification:
    model = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.company_id == company_id, Notification.user_id == user_id))
    if model is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    model.read_at = model.read_at or utcnow()
    db.commit()
    db.refresh(model)
    return model
