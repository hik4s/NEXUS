from __future__ import annotations

from datetime import datetime, timezone
import json
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.integrations import IntegrationConnection, IntegrationLog
from app.models.user import User
from app.platform.security import encrypt_secret, secret_fingerprint
from app.schemas.integrations import IntegrationCreate


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _credentials_json(credentials: dict | None) -> str | None:
    if not credentials:
        return None
    return json.dumps(credentials, separators=(",", ":"), sort_keys=True)


def get_integration(db: Session, company_id: UUID, integration_id: UUID) -> IntegrationConnection | None:
    return db.scalar(select(IntegrationConnection).where(IntegrationConnection.id == integration_id, IntegrationConnection.company_id == company_id))


def create_integration(db: Session, actor: User, payload: IntegrationCreate, request=None) -> IntegrationConnection:
    credentials_blob = _credentials_json(payload.credentials)
    model = IntegrationConnection(
        company_id=actor.company_id,
        created_by_user_id=actor.id,
        provider=payload.provider,
        name=payload.name,
        base_url=str(payload.base_url) if payload.base_url else None,
        encrypted_credentials=encrypt_secret(credentials_blob) if credentials_blob else None,
        credential_fingerprint=secret_fingerprint(credentials_blob) if credentials_blob else None,
        config=payload.config,
        status="configured",
        active=True,
    )
    db.add(model)
    db.flush()
    record_audit(db, request=request, action="integration.created", company_id=actor.company_id, actor_user_id=actor.id, resource_type="integration", resource_id=model.id, metadata={"provider": model.provider, "name": model.name})
    db.commit(); db.refresh(model)
    return model


def list_integrations(db: Session, company_id: UUID) -> list[IntegrationConnection]:
    return list(db.scalars(select(IntegrationConnection).where(IntegrationConnection.company_id == company_id).order_by(IntegrationConnection.created_at.desc())).all())


def log_integration(db: Session, integration: IntegrationConnection, level: str, event: str, message: str, details: dict | None = None) -> IntegrationLog:
    log = IntegrationLog(company_id=integration.company_id, integration_id=integration.id, level=level, event=event, message=message, details=details)
    db.add(log)
    db.flush()
    return log


def health_check(db: Session, actor: User, integration_id: UUID, request=None) -> IntegrationConnection:
    model = get_integration(db, actor.company_id, integration_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    if not model.active:
        raise HTTPException(status_code=409, detail="Integration is inactive")
    model.last_health_at = utcnow()
    model.last_error = None
    if model.base_url:
        try:
            response = httpx.get(model.base_url, timeout=10.0, follow_redirects=True)
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}")
            model.status = "healthy"
            log_integration(db, model, "info", "health_check", "Integration responded successfully", {"status_code": response.status_code})
        except Exception as exc:
            model.status = "error"
            model.last_error = str(exc)[:1000]
            log_integration(db, model, "error", "health_check_failed", "Integration health check failed", {"error": str(exc)[:1000]})
    else:
        model.status = "configured"
        log_integration(db, model, "info", "health_check", "No base URL configured; configuration validated")
    record_audit(db, request=request, action="integration.health_check", company_id=actor.company_id, actor_user_id=actor.id, resource_type="integration", resource_id=model.id, metadata={"status": model.status})
    db.commit(); db.refresh(model)
    return model
