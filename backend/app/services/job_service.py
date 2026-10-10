from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.async_jobs import BackgroundJob, JobSchedule
from app.models.user import User
from app.workers.queue import get_redis_queue


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_payload(payload: dict[str, Any]) -> None:
    try:
        json.dumps(payload, default=str)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Job payload must be JSON serializable") from exc


def enqueue_job(
    db: Session,
    *,
    company_id: UUID | None,
    kind: str,
    payload: dict[str, Any],
    created_by_user: User | None = None,
    delay_seconds: int = 0,
    max_attempts: int | None = None,
    idempotency_key: str | None = None,
    enqueue_external: bool = True,
) -> BackgroundJob:
    if not kind.strip():
        raise HTTPException(status_code=422, detail="Job kind is required")
    _validate_payload(payload)
    if max_attempts is None:
        max_attempts = settings.JOB_DEFAULT_MAX_ATTEMPTS
    if not 1 <= max_attempts <= 20:
        raise HTTPException(status_code=422, detail="max_attempts must be between 1 and 20")

    if idempotency_key:
        existing = db.scalar(
            select(BackgroundJob).where(
                BackgroundJob.company_id == company_id,
                BackgroundJob.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.kind != kind or (existing.payload or {}) != payload:
                raise HTTPException(status_code=409, detail="Job idempotency key was already used with a different job")
            return existing

    model = BackgroundJob(
        company_id=company_id,
        created_by_user_id=created_by_user.id if created_by_user else None,
        kind=kind,
        payload=payload,
        status="queued",
        max_attempts=max_attempts,
        available_at=utcnow() + timedelta(seconds=max(delay_seconds, 0)),
        idempotency_key=idempotency_key,
    )
    db.add(model)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(BackgroundJob).where(
                    BackgroundJob.company_id == company_id,
                    BackgroundJob.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return existing
        raise
    db.commit()
    db.refresh(model)

    if enqueue_external and delay_seconds <= 0:
        queue = get_redis_queue()
        if queue:
            try:
                queue.enqueue(model.id)
            except Exception:
                # DB remains the source of truth; the worker can poll it later.
                pass
    return model


def create_schedule(
    db: Session,
    *,
    company_id: UUID | None,
    kind: str,
    payload: dict[str, Any],
    interval_seconds: int,
    next_run_at: datetime | None = None,
    created_by_user: User | None = None,
) -> JobSchedule:
    if interval_seconds < 1:
        raise HTTPException(status_code=422, detail="interval_seconds must be positive")
    _validate_payload(payload)
    schedule = JobSchedule(
        company_id=company_id,
        created_by_user_id=created_by_user.id if created_by_user else None,
        kind=kind,
        payload=payload,
        interval_seconds=interval_seconds,
        next_run_at=next_run_at or utcnow(),
        active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule
