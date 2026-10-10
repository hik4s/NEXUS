from app.db.session import SessionLocal
from app.workers.runner import redis_or_local_queue, run_once


def main() -> None:
    queue = redis_or_local_queue()
    with SessionLocal() as db:
        result = run_once(db, queue=queue)
        print(result.id if result else "NO_JOB")


if __name__ == "__main__":
    main()
