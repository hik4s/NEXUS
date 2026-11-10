"""Run one explicitly targeted release migration with a direct PostgreSQL connection.

Secrets come from environment only. No migration runs at API startup.
"""
import argparse
import json
import os
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[1]
LOCK_ID = 1337280711


def validate_target(env, expected_host, expected_database, confirmed):
    if not confirmed:
        raise ValueError('--confirm-release is required')
    if env.get('APP_ENV') not in {'production', 'test'}:
        raise ValueError('APP_ENV must explicitly be production or test')
    raw = env.get('NEXUS_RELEASE_DATABASE_URL', '')
    try:
        url = make_url(raw)
    except Exception:
        raise ValueError('NEXUS_RELEASE_DATABASE_URL must be a direct PostgreSQL URL') from None
    if url.drivername == 'postgresql':
        url = url.set(drivername='postgresql+psycopg')
    # libpq query parameters can override the authority host/database. Restrict
    # the release URL to TLS options so the confirmed target is the real target.
    if set(url.query) - {'sslmode', 'channel_binding'}:
        raise ValueError('Release URL parameters may contain only TLS settings')
    if (url.drivername != 'postgresql+psycopg' or not url.host or not url.database
            or '-pooler' in url.host or url.host != expected_host or url.database != expected_database):
        raise ValueError('Release target must match the explicit host/database and use a direct psycopg connection')
    if env['APP_ENV'] == 'production' and url.query.get('sslmode') not in {'require', 'verify-ca', 'verify-full'}:
        raise ValueError('TLS is required for production migrations')
    if env['APP_ENV'] == 'test' and url.host not in {'localhost', '127.0.0.1', 'postgres'}:
        raise ValueError('Test release target must be local')
    return url


def migrate(url):
    # Alembic imports app settings lazily, after the direct target is selected.
    os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
    sys.path.insert(0, str(ROOT / 'backend'))
    from alembic import command
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    cfg = Config(str(ROOT / 'backend' / 'alembic.ini'))
    cfg.set_main_option('script_location', str(ROOT / 'backend' / 'alembic'))
    cfg.set_main_option('prepend_sys_path', str(ROOT / 'backend'))
    cfg.attributes['configure_logger'] = False
    engine = create_engine(url, poolclass=NullPool, connect_args={
        'connect_timeout': 10, 'options': '-c statement_timeout=120000 -c lock_timeout=10000'})
    try:
        with engine.connect() as connection:
            if not connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_ID}):
                raise ValueError('Another release migration is already running')
            connection.commit()
            try:
                cfg.attributes['connection'] = connection
                command.upgrade(cfg, 'head')
                command.check(cfg)
                revisions = MigrationContext.configure(connection).get_current_heads()
                if set(revisions) != set(ScriptDirectory.from_config(cfg).get_heads()):
                    raise ValueError('Database revision does not match this release')
                connection.commit()
                return {'status': 'migrated', 'revisions': list(revisions)}
            finally:
                connection.rollback()
                connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_ID})
                connection.commit()
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-host', required=True)
    parser.add_argument('--expected-database', required=True)
    parser.add_argument('--confirm-release', action='store_true')
    args = parser.parse_args()
    try:
        target = validate_target(os.environ, args.expected_host, args.expected_database, args.confirm_release)
        print(json.dumps(migrate(target)))
    except ValueError as error:
        parser.exit(2, f'{error}\n')
    except Exception:
        # Driver exception strings can contain credentials, DSNs and private hosts.
        parser.exit(1, 'Release migration failed; inspect database connectivity and revision compatibility privately.\n')


if __name__ == '__main__':
    main()
