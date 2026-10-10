from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.async_jobs import JobSchedule
from app.services.job_service import enqueue_job


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_scheduler_tick(db: Session, now: datetime | None = None) -> list[str]:
    now = now or utcnow()
    schedules = list(
        db.scalars(
            select(JobSchedule)
            .where(JobSchedule.active.is_(True), JobSchedule.next_run_at <= now)
            .order_by(JobSchedule.next_run_at.asc())
        ).all()
    )
    job_ids: list[str] = []
    for schedule in schedules:
        idempotency_key = f"schedule:{schedule.id}:{schedule.next_run_at.isoformat()}"
        job = enqueue_job(
            db,
            company_id=schedule.company_id,
            kind=schedule.kind,
            payload=schedule.payload or {},
            max_attempts=3,
            idempotency_key=idempotency_key,
            enqueue_external=False,
        )
        job_ids.append(str(job.id))
        schedule.last_enqueued_at = now
        schedule.next_run_at = schedule.next_run_at + timedelta(seconds=schedule.interval_seconds)
    db.commit()
    return job_ids
