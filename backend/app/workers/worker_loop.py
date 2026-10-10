from __future__ import annotations

import time

from app.core.config import settings
from app.db.session import SessionLocal
from app.workers.runner import redis_or_local_queue, run_once


def main() -> None:
    queue = redis_or_local_queue()
    print("NEXUS worker started")
    try:
        while True:
            with SessionLocal() as db:
                result = run_once(db, queue=queue)
            if result is None:
                time.sleep(settings.JOB_WORKER_POLL_SECONDS)
            else:
                print(f"job={result.id} status={result.status} attempts={result.attempts}")
    except KeyboardInterrupt:
        print("NEXUS worker stopped")


if __name__ == "__main__":
    main()
