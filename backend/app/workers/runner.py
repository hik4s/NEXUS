from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.async_jobs import BackgroundJob
from app.workers.handlers import HANDLERS
from app.workers.queue import LocalJobQueue, RedisJobQueue, get_redis_queue


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _backoff_seconds(attempts: int) -> int:
    return min(300, 2 ** max(attempts - 1, 0))


def _claim_job(db: Session, job_id: UUID | None = None) -> BackgroundJob | None:
    stmt = select(BackgroundJob).where(BackgroundJob.status == "queued", BackgroundJob.available_at <= utcnow()).order_by(BackgroundJob.created_at.asc()).limit(1)
    if job_id is not None:
        stmt = select(BackgroundJob).where(BackgroundJob.id == job_id)
    job = db.scalar(stmt)
    if job is None or job.status != "queued":
        return None
    # Only one worker may transition a queued job, even if several read it.
    claimed = db.execute(
        update(BackgroundJob)
        .where(BackgroundJob.id == job.id, BackgroundJob.status == "queued")
        .values(status="running", attempts=BackgroundJob.attempts + 1,
                started_at=utcnow(), last_error=None)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        db.rollback()
        return None
    db.commit()
    db.refresh(job)
    return job


def run_job(db: Session, job_id: UUID, handlers: dict[str, Any] | None = None) -> BackgroundJob | None:
    job = _claim_job(db, job_id)
    if job is None:
        return None
    handler_map = handlers or HANDLERS
    handler = handler_map.get(job.kind)
    if handler is None:
        job.status = "dead_letter"
        job.last_error = f"No handler registered for job kind: {job.kind}"
        job.completed_at = utcnow()
        db.commit()
        db.refresh(job)
        return job

    try:
        result = handler(db, job.payload or {})
        job.status = "succeeded"
        job.result = result or {}
        job.completed_at = utcnow()
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(BackgroundJob, job.id)
        if job is None:
            return None
        if job.attempts >= job.max_attempts:
            job.status = "dead_letter"
            job.last_error = str(exc)
            job.completed_at = utcnow()
        else:
            job.status = "queued"
            job.last_error = str(exc)
            job.available_at = utcnow() + timedelta(seconds=_backoff_seconds(job.attempts))
        db.commit()
    db.refresh(job)
    return job


def run_once(db: Session, queue: RedisJobQueue | LocalJobQueue | None = None, handlers: dict[str, Any] | None = None) -> BackgroundJob | None:
    job_id: UUID | None = None
    if queue is not None:
        if isinstance(queue, RedisJobQueue):
            job_id = queue.dequeue(timeout=1)
        else:
            job_id = queue.dequeue()
    if job_id is None:
        job = db.scalar(
            select(BackgroundJob)
            .where(BackgroundJob.status == "queued", BackgroundJob.available_at <= utcnow())
            .order_by(BackgroundJob.created_at.asc())
            .limit(1)
        )
        job_id = job.id if job else None
    if job_id is None:
        return None
    return run_job(db, job_id, handlers=handlers)


def redis_or_local_queue() -> RedisJobQueue | LocalJobQueue:
    return get_redis_queue() or LocalJobQueue()
