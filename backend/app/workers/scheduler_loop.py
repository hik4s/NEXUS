from __future__ import annotations

import time

from app.core.config import settings
from app.db.session import SessionLocal
from app.workers.scheduler import run_scheduler_tick


def main() -> None:
    print("NEXUS scheduler started")
    try:
        while True:
            with SessionLocal() as db:
                job_ids = run_scheduler_tick(db)
            if job_ids:
                print(f"scheduled_jobs={len(job_ids)}")
            time.sleep(settings.JOB_WORKER_POLL_SECONDS)
    except KeyboardInterrupt:
        print("NEXUS scheduler stopped")


if __name__ == "__main__":
    main()
