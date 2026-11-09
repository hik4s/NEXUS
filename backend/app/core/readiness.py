import asyncio
import sys

import psycopg
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine


async def _probe_postgres():
    # A fresh, isolated connection avoids the ORM pool's synchronous pre-ping.
    dsn = engine.url.set(drivername='postgresql').render_as_string(hide_password=False)
    connection = await psycopg.AsyncConnection.connect(dsn, autocommit=True,
        connect_timeout=settings.DB_TIMEOUT_SECONDS)
    try:
        await connection.execute("SELECT set_config('statement_timeout', %s, false)",
            (f'{settings.DB_TIMEOUT_SECONDS * 1000}ms',))
        await connection.execute('SELECT 1')
    finally:
        await connection.close()


def _windows_probe():
    # Psycopg async requires a Selector loop; Uvicorn may use Proactor on Windows.
    async def bounded():
        async with asyncio.timeout(settings.DB_TIMEOUT_SECONDS):
            await _probe_postgres()
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(bounded())


def _probe_sqlite():
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))


async def _probe_database():
    if engine.dialect.name == 'postgresql':
        if sys.platform == 'win32':
            await asyncio.to_thread(_windows_probe)
        else:
            await _probe_postgres()
    else:
        await asyncio.to_thread(_probe_sqlite)


def _consume_result(task):
    if not task.cancelled():
        task.exception()


async def database_readiness() -> dict[str, str]:
    task = asyncio.create_task(_probe_database())
    try:
        # wait() does not extend the response deadline while driver cancellation
        # cleans up the isolated probe after a stalled connection/query.
        done, _ = await asyncio.wait({task}, timeout=settings.DB_TIMEOUT_SECONDS)
        if not done:
            task.cancel()
            task.add_done_callback(_consume_result)
            raise TimeoutError
        task.result()
    except asyncio.CancelledError:
        task.cancel()
        task.add_done_callback(_consume_result)
        raise
    except (TimeoutError, SQLAlchemyError, psycopg.Error):
        raise HTTPException(status_code=503, detail={'code': 'database_unavailable',
            'message': 'Banco de dados temporariamente indisponível.'}) from None
    return {'status': 'ready', 'database': 'ok'}
