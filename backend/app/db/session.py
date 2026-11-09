from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    sqlite_path = settings.DATABASE_URL.removeprefix("sqlite:///")
    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

database_url = make_url(settings.DATABASE_URL)
connect_args = {}
if database_url.get_backend_name() == 'sqlite':
    connect_args = {'check_same_thread': False, 'timeout': settings.DB_TIMEOUT_SECONDS}
elif database_url.get_backend_name() == 'postgresql':
    connect_args = {'connect_timeout': settings.DB_TIMEOUT_SECONDS}
engine_options = {'pool_pre_ping': True, 'connect_args': connect_args}
if not (database_url.get_backend_name() == 'sqlite' and database_url.database in {None, '', ':memory:'}):
    engine_options['pool_timeout'] = settings.DB_TIMEOUT_SECONDS
engine = create_engine(settings.DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
