from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.async_jobs import BackgroundJob, JobSchedule, Notification
from app.models.user import User
from app.schemas.async_jobs import JobCreate, JobRead, JobScheduleCreate, JobScheduleRead, NotificationRead
from app.services.job_service import create_schedule, enqueue_job
from app.services.notification_service import list_notifications, mark_notification_read
from app.workers.queue import get_redis_queue
from app.workers.runner import run_job
from app.workers.scheduler import run_scheduler_tick

router = APIRouter(prefix="/async")


@router.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def post_job(
    payload: JobCreate,
    request: Request,
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    return enqueue_job(
        db,
        company_id=current_user.company_id,
        kind=payload.kind,
        payload=payload.payload,
        created_by_user=current_user,
        delay_seconds=payload.delay_seconds,
        max_attempts=payload.max_attempts,
        idempotency_key=payload.idempotency_key,
    )


@router.get("/jobs", response_model=list[JobRead])
def get_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    stmt = select(BackgroundJob).where(BackgroundJob.company_id == current_user.company_id).order_by(BackgroundJob.created_at.desc())
    if status_filter:
        stmt = stmt.where(BackgroundJob.status == status_filter)
    return list(db.scalars(stmt).all())


@router.post("/jobs/{job_id}/run", response_model=JobRead)
def run_job_route(
    job_id: UUID,
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    job = db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id, BackgroundJob.company_id == current_user.company_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return run_job(db, job.id)


@router.post("/schedules", response_model=JobScheduleRead, status_code=status.HTTP_201_CREATED)
def post_schedule(
    payload: JobScheduleCreate,
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    return create_schedule(
        db,
        company_id=current_user.company_id,
        kind=payload.kind,
        payload=payload.payload,
        interval_seconds=payload.interval_seconds,
        next_run_at=payload.next_run_at,
        created_by_user=current_user,
    )


@router.get("/schedules", response_model=list[JobScheduleRead])
def get_schedules(
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(JobSchedule).where(JobSchedule.company_id == current_user.company_id).order_by(JobSchedule.created_at.desc())).all())


@router.post("/scheduler/tick")
def tick_scheduler(
    current_user: User = Depends(require_permission("platform:jobs")),
    db: Session = Depends(get_db),
):
    job_ids = run_scheduler_tick(db)
    return {"enqueued_job_ids": job_ids}


@router.get("/notifications", response_model=list[NotificationRead])
def get_notifications(
    unread_only: bool = Query(default=False),
    current_user: User = Depends(require_permission("notifications:read")),
    db: Session = Depends(get_db),
):
    return list_notifications(db, current_user.company_id, current_user.id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: UUID,
    current_user: User = Depends(require_permission("notifications:read")),
    db: Session = Depends(get_db),
):
    return mark_notification_read(db, current_user.company_id, current_user.id, notification_id)


@router.get("/redis/status")
def redis_status(
    current_user: User = Depends(require_permission("platform:jobs")),
):
    queue = get_redis_queue()
    return {"enabled": True, "available": queue is not None}
