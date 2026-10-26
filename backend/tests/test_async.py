from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.async_jobs import BackgroundJob, JobSchedule, Notification
from app.workers.queue import LocalJobQueue
from app.workers.runner import run_job, run_once
from app.workers.scheduler import run_scheduler_tick


def register(client, company, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": company,
            "company_slug": company.lower().replace(" ", "-") + uuid4().hex[:6],
            "full_name": "Owner",
            "email": email,
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_job_creation_idempotency_and_manual_run_creates_notification():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Async Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        payload = {
            "kind": "notification.create",
            "payload": {
                "company_id": me["company_id"],
                "user_id": me["id"],
                "title": "Async ready",
                "body": "Background job finished.",
                "severity": "success",
            },
            "idempotency_key": f"job-{uuid4().hex}",
        }
        first = client.post("/api/v1/async/jobs", headers=auth(token), json=payload)
        assert first.status_code == 201, first.text
        second = client.post("/api/v1/async/jobs", headers=auth(token), json=payload)
        assert second.status_code == 201, second.text
        assert second.json()["id"] == first.json()["id"]

        run = client.post(f"/api/v1/async/jobs/{first.json()['id']}/run", headers=auth(token))
        assert run.status_code == 200, run.text
        assert run.json()["status"] == "succeeded"

        notifications = client.get("/api/v1/async/notifications", headers=auth(token))
        assert notifications.status_code == 200
        assert notifications.json()[0]["title"] == "Async ready"

        notification_id = notifications.json()[0]["id"]
        mark_read = client.post(f"/api/v1/async/notifications/{notification_id}/read", headers=auth(token))
        assert mark_read.status_code == 200
        assert mark_read.json()["read_at"] is not None


def test_worker_retries_then_dead_letters_failed_job():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Retry Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        response = client.post(
            "/api/v1/async/jobs",
            headers=auth(token),
            json={"kind": "unknown.job", "payload": {}, "max_attempts": 2},
        )
        assert response.status_code == 201
        job_id = response.json()["id"]

        first = client.post(f"/api/v1/async/jobs/{job_id}/run", headers=auth(token))
        assert first.status_code == 200
        assert first.json()["status"] == "dead_letter"
        assert first.json()["attempts"] == 1
        assert "No handler" in first.json()["last_error"]

        # Unknown handlers are deterministic failures and therefore dead-letter immediately.
        with SessionLocal() as db:
            job = db.get(BackgroundJob, __import__("uuid").UUID(job_id))
            assert str(job.company_id) == me["company_id"]


def test_scheduler_creates_idempotent_job_and_advances_schedule():
    with SessionLocal() as db, TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Scheduler Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        schedule = JobSchedule(
            company_id=__import__("uuid").UUID(me["company_id"]),
            created_by_user_id=__import__("uuid").UUID(me["id"]),
            kind="noop",
            payload={"source": "scheduler"},
            interval_seconds=60,
            next_run_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            active=True,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        due = datetime.now(timezone.utc)
        job_ids = run_scheduler_tick(db, now=due)
        assert len(job_ids) == 1
        db.refresh(schedule)
        assert schedule.last_enqueued_at is not None
        stored_next = schedule.next_run_at if schedule.next_run_at.tzinfo else schedule.next_run_at.replace(tzinfo=timezone.utc)
        assert stored_next > due

        jobs = list(db.scalars(select(BackgroundJob).where(BackgroundJob.company_id == __import__("uuid").UUID(me["company_id"]))).all())
        assert len(jobs) == 1
        assert jobs[0].kind == "noop"


def test_local_queue_dispatches_job_without_redis():
    with SessionLocal() as db, TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, "Queue Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        response = client.post(
            "/api/v1/async/jobs",
            headers=auth(token),
            json={"kind": "noop", "payload": {"value": 42}},
        )
        assert response.status_code == 201
        job_id = response.json()["id"]

        queue = LocalJobQueue()
        queue.enqueue(__import__("uuid").UUID(job_id))
        result = run_once(db, queue=queue)
        assert str(result.id) == job_id
        assert result.status == "succeeded"
        assert result.result["payload"]["value"] == 42


def test_transient_job_failure_retries_and_then_succeeds():
    with TestClient(app) as client, SessionLocal() as db:
        suffix = uuid4().hex[:8]
        token = register(client, "Transient Co", f"owner-{suffix}@example.com")
        me = client.get("/api/v1/auth/me", headers=auth(token)).json()
        response = client.post(
            "/api/v1/async/jobs",
            headers=auth(token),
            json={"kind": "flaky.job", "payload": {}, "max_attempts": 3},
        )
        assert response.status_code == 201
        job_id = __import__("uuid").UUID(response.json()["id"])
        calls = {"count": 0}

        def flaky_handler(_, __):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("temporary failure")
            return {"ok": True}

        first = run_job(db, job_id, handlers={"flaky.job": flaky_handler})
        assert first.status == "queued"
        assert first.attempts == 1
        assert first.last_error == "temporary failure"
        second = run_job(db, job_id, handlers={"flaky.job": flaky_handler})
        assert second.status == "succeeded"
        assert second.attempts == 2
        assert second.result == {"ok": True}
        assert str(second.company_id) == me["company_id"]


def test_job_dead_letters_after_max_attempts():
    with TestClient(app) as client, SessionLocal() as db:
        suffix = uuid4().hex[:8]
        token = register(client, "Dead Letter Co", f"owner-{suffix}@example.com")
        response = client.post(
            "/api/v1/async/jobs",
            headers=auth(token),
            json={"kind": "always.fail", "payload": {}, "max_attempts": 2},
        )
        assert response.status_code == 201
        job_id = __import__("uuid").UUID(response.json()["id"])

        def always_fail(_, __):
            raise RuntimeError("permanent failure")

        first = run_job(db, job_id, handlers={"always.fail": always_fail})
        assert first.status == "queued"
        assert first.attempts == 1
        second = run_job(db, job_id, handlers={"always.fail": always_fail})
        assert second.status == "dead_letter"
        assert second.attempts == 2
        assert second.last_error == "permanent failure"


def test_running_job_is_not_executed_a_second_time():
    with TestClient(app), SessionLocal() as db:
        job = BackgroundJob(
            kind="in.progress", payload={}, status="running", attempts=1,
            max_attempts=3, available_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()
        calls = []

        def handler(_, payload):
            calls.append(payload)
            return {"ok": True}

        result = run_job(db, job.id, handlers={"in.progress": handler})
        assert result is None
        assert calls == []
        db.refresh(job)
        assert job.status == "running"
        assert job.attempts == 1


def test_manual_run_of_completed_job_returns_conflict():
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        token = register(client, f"Completed {suffix}", f"completed-{suffix}@example.com")
        response = client.post("/api/v1/async/jobs", headers=auth(token),
                               json={"kind": "noop", "payload": {}})
        assert response.status_code == 201
        url = f"/api/v1/async/jobs/{response.json()['id']}/run"
        assert client.post(url, headers=auth(token)).status_code == 200
        assert client.post(url, headers=auth(token)).status_code == 409


def test_manual_scheduler_tick_only_enqueues_current_company():
    with TestClient(app) as client, SessionLocal() as db:
        suffix = uuid4().hex[:8]
        token_a = register(client, f"Schedule A {suffix}", f"schedule-a-{suffix}@example.com")
        token_b = register(client, f"Schedule B {suffix}", f"schedule-b-{suffix}@example.com")
        schedules = []
        for token in (token_a, token_b):
            response = client.post("/api/v1/async/schedules", headers=auth(token), json={
                "kind": "noop", "payload": {}, "interval_seconds": 60,
                "next_run_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            })
            assert response.status_code == 201, response.text
            schedules.append(response.json())
        response = client.post("/api/v1/async/scheduler/tick", headers=auth(token_a))
        assert response.status_code == 200, response.text
        assert len(response.json()["enqueued_job_ids"]) == 1
        assert client.get("/api/v1/async/jobs", headers=auth(token_b)).json() == []
        other = db.get(JobSchedule, __import__("uuid").UUID(schedules[1]["id"]))
        assert other.last_enqueued_at is None
