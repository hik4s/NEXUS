from app.db.session import SessionLocal
from app.workers.scheduler import run_scheduler_tick


def main() -> None:
    with SessionLocal() as db:
        ids = run_scheduler_tick(db)
        print("\n".join(ids) if ids else "NO_DUE_SCHEDULES")


if __name__ == "__main__":
    main()
