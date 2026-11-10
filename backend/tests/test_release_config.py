"""Published portfolio boundaries and explicit, non-secret release targeting."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.security_config import validate_security_configuration
from app.db.session import engine


@pytest.fixture
def production(monkeypatch):
    values = dict(APP_ENV='production', APP_PROFILE='portfolio',
        SECRET_KEY='test-only-production-config-secret-over-32-characters',
        DATABASE_URL='postgresql+psycopg://demo:test@ep-demo.neon.tech/nexus?sslmode=require',
        PUBLIC_REGISTRATION_ENABLED=False, REDIS_ENABLED=False,
        ENABLE_DOCS_IN_PRODUCTION=False,
        CORS_ORIGINS='https://nexus-ui.example.com', TRUSTED_HOSTS='nexus-api.example.com')
    for name, value in values.items():
        monkeypatch.setattr(settings, name, value)


@pytest.mark.parametrize('url', [
    'postgresql+psycopg://demo:test@ep-demo.neon.tech/nexus',
    'postgresql+psycopg://demo:test@ep-demo.neon.tech/nexus?sslmode=disable',
    'postgresql+psycopg://demo:test@ep-demo.neon.tech/nexus?sslmode=prefer',
])
def test_published_database_requires_tls(production, monkeypatch, url):
    monkeypatch.setattr(settings, 'DATABASE_URL', url)
    with pytest.raises(RuntimeError, match='TLS'):
        validate_security_configuration()


@pytest.mark.parametrize('origins', ['', '*', 'http://nexus-ui.example.com',
    'https://nexus-ui.example.com/path', 'https://user:password@nexus-ui.example.com'])
def test_published_cors_requires_explicit_https_origins(production, monkeypatch, origins):
    monkeypatch.setattr(settings, 'CORS_ORIGINS', origins)
    with pytest.raises(RuntimeError, match='CORS_ORIGINS'):
        validate_security_configuration()


def test_published_hosts_cannot_accept_every_host(production, monkeypatch):
    monkeypatch.setattr(settings, 'TRUSTED_HOSTS', '*')
    with pytest.raises(RuntimeError, match='TRUSTED_HOSTS'):
        validate_security_configuration()


def test_valid_published_config(production):
    validate_security_configuration()


def load_release():
    path = Path(__file__).resolve().parents[2] / 'scripts' / 'migrate_release.py'
    spec = importlib.util.spec_from_file_location('nexus_migrate_release', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('changes', [
    {'APP_ENV': 'development'}, {'NEXUS_RELEASE_DATABASE_URL': ''},
    {'NEXUS_RELEASE_DATABASE_URL': 'sqlite:///private.db'},
    {'NEXUS_RELEASE_DATABASE_URL': 'postgresql+psycopg://demo:private@ep-demo-pooler.neon.tech/nexus?sslmode=require'},
    {'NEXUS_RELEASE_DATABASE_URL': 'postgresql+psycopg://demo:private@other.neon.tech/nexus?sslmode=require'},
    {'NEXUS_RELEASE_DATABASE_URL': 'postgresql+psycopg://demo:private@ep-demo.neon.tech/other?sslmode=require'},
    {'NEXUS_RELEASE_DATABASE_URL': 'postgresql+psycopg://demo:private@ep-demo.neon.tech/nexus'},
])
def test_release_refuses_wrong_target_before_connecting(changes):
    release = load_release()
    env = {'APP_ENV': 'production', 'NEXUS_RELEASE_DATABASE_URL':
        'postgresql+psycopg://demo:private@ep-demo.neon.tech/nexus?sslmode=require'}
    env.update(changes)
    with pytest.raises(ValueError) as error:
        release.validate_target(env, 'ep-demo.neon.tech', 'nexus', True)
    assert 'private' not in str(error.value)


def test_release_requires_confirmation_and_accepts_direct_tls_target():
    release = load_release()
    env = {'APP_ENV': 'production', 'NEXUS_RELEASE_DATABASE_URL':
        'postgresql+psycopg://demo:private@ep-demo.neon.tech/nexus?sslmode=require'}
    with pytest.raises(ValueError, match='confirm'):
        release.validate_target(env, 'ep-demo.neon.tech', 'nexus', False)
    assert release.validate_target(env, 'ep-demo.neon.tech', 'nexus', True).database == 'nexus'


def test_release_accepts_provider_url_and_selects_psycopg_explicitly():
    env = {'APP_ENV': 'production', 'NEXUS_RELEASE_DATABASE_URL':
        'postgresql://demo:private@ep-demo.neon.tech/nexus?sslmode=require'}
    assert load_release().validate_target(env, 'ep-demo.neon.tech', 'nexus', True).drivername == 'postgresql+psycopg'


@pytest.mark.parametrize('parameter', ['host=other.neon.tech', 'hostaddr=10.0.0.1',
    'dbname=other', 'database=other', 'service=other', 'options=-csearch_path=other',
    'user=other', 'password=other', 'port=5433'])
def test_release_rejects_libpq_target_overrides(parameter):
    env = {'APP_ENV': 'production', 'NEXUS_RELEASE_DATABASE_URL':
        f'postgresql://demo:private@ep-demo.neon.tech/nexus?sslmode=require&{parameter}'}
    with pytest.raises(ValueError, match='parameters'):
        load_release().validate_target(env, 'ep-demo.neon.tech', 'nexus', True)


@pytest.mark.skipif(engine.dialect.name != 'postgresql', reason='Release DDL needs PostgreSQL')
def test_release_bootstraps_empty_database_and_repeats_without_data_loss():
    import psycopg
    from psycopg import sql
    from sqlalchemy import create_engine, inspect, text

    database = f'nexus_release_test_{uuid4().hex}'
    admin_url = engine.url.set(database='postgres', drivername='postgresql')
    target = engine.url.set(database=database)
    script = Path(__file__).resolve().parents[2] / 'scripts' / 'migrate_release.py'
    with psycopg.connect(admin_url.render_as_string(hide_password=False), autocommit=True) as admin:
        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
        target_engine = create_engine(target)
        try:
            env = {**os.environ, 'APP_ENV': 'test', 'NEXUS_RELEASE_DATABASE_URL':
                target.render_as_string(hide_password=False)}
            args = [sys.executable, str(script), '--confirm-release', '--expected-host', target.host,
                '--expected-database', database]
            for attempt in range(2):
                result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=60)
                assert result.returncode == 0, result.stderr
                assert '"status": "migrated"' in result.stdout
                assert target.password not in result.stdout + result.stderr
                with target_engine.begin() as connection:
                    assert 'order_import_batches' in inspect(connection).get_table_names()
                    if attempt == 0:
                        connection.execute(text("INSERT INTO companies (id, name, slug) VALUES (:id, 'Release probe', 'release-probe')"),
                            {'id': uuid4()})
                    assert connection.scalar(text("SELECT count(*) FROM companies WHERE slug='release-probe'")) == 1
        finally:
            target_engine.dispose()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
