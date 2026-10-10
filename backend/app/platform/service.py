import hashlib
import json
import math
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.models.platform import ApiKey, IdempotencyRecord, WebhookDelivery, WebhookEndpoint
from app.models.user import User
from app.platform.security import (
    decrypt_secret,
    encrypt_secret,
    generate_api_secret,
    generate_webhook_secret,
    hash_secret,
    secret_fingerprint,
    utcnow,
    webhook_signature,
)
from app.schemas.platform import ApiKeyCreate, ApiKeyRead, ApiKeyCreateResponse, WebhookEndpointCreate, WebhookEndpointCreateResponse, WebhookEndpointRead


MAX_IDEMPOTENCY_KEY_LENGTH = 100


def paginate_statement(
    db: Session,
    statement,
    *,
    page: int,
    page_size: int,
) -> tuple[list[Any], dict[str, int]]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = int(db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0)
    total_pages = math.ceil(total / page_size) if total else 0
    items = list(db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all())
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def apply_pagination_headers(response, meta: dict[str, int]) -> None:
    response.headers["X-Page"] = str(meta["page"])
    response.headers["X-Page-Size"] = str(meta["page_size"])
    response.headers["X-Total-Count"] = str(meta["total"])
    response.headers["X-Total-Pages"] = str(meta["total_pages"])


def normalize_scopes(scopes: Sequence[str]) -> list[str]:
    normalized = sorted({scope.strip() for scope in scopes if scope.strip()})
    for scope in normalized:
        if len(scope) > 120 or any(char.isspace() for char in scope):
            raise HTTPException(status_code=422, detail=f"Invalid API key scope: {scope}")
    return normalized


def create_api_key(db: Session, actor: User, payload: ApiKeyCreate, request: Request | None = None) -> ApiKeyCreateResponse:
    scopes = normalize_scopes(payload.scopes)
    secret = generate_api_secret()
    model = ApiKey(
        company_id=actor.company_id,
        created_by_user_id=actor.id,
        name=payload.name,
        key_prefix=secret[:16],
        secret_hash=hash_secret(secret),
        scopes=scopes,
    )
    db.add(model)
    record_audit(
        db,
        request=request,
        action="api_key.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="api_key",
        resource_id=model.id,
        metadata={"name": model.name, "scopes": scopes, "key_prefix": model.key_prefix},
    )
    db.commit()
    db.refresh(model)
    return ApiKeyCreateResponse.model_validate({**ApiKeyRead.from_model(model).model_dump(), "secret": secret})


def list_api_keys(db: Session, company_id: UUID) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.company_id == company_id).order_by(ApiKey.created_at.desc())).all())


def revoke_api_key(db: Session, actor: User, key_id: UUID, request: Request | None = None) -> ApiKey:
    model = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.company_id == actor.company_id))
    if model is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if model.revoked_at is None:
        model.revoked_at = utcnow()
        record_audit(
            db,
            request=request,
            action="api_key.revoked",
            company_id=actor.company_id,
            actor_user_id=actor.id,
            resource_type="api_key",
            resource_id=model.id,
        )
        db.commit()
        db.refresh(model)
    return model


def authenticate_api_key(db: Session, raw_key: str, required_scope: str | None = None) -> ApiKey:
    key_hash = hash_secret(raw_key)
    model = db.scalar(select(ApiKey).where(ApiKey.secret_hash == key_hash))
    if model is None or model.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")
    if required_scope and required_scope not in (model.scopes or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key scope denied")
    model.last_used_at = utcnow()
    db.commit()
    return model


def create_webhook_endpoint(
    db: Session,
    actor: User,
    payload: WebhookEndpointCreate,
    request: Request | None = None,
) -> WebhookEndpointCreateResponse:
    events = sorted({event.strip() for event in payload.subscribed_events if event.strip()})
    if not events:
        raise HTTPException(status_code=422, detail="At least one subscribed event is required")
    secret = generate_webhook_secret()
    model = WebhookEndpoint(
        company_id=actor.company_id,
        created_by_user_id=actor.id,
        name=payload.name,
        url=str(payload.url),
        encrypted_secret=encrypt_secret(secret),
        secret_fingerprint=secret_fingerprint(secret),
        subscribed_events=events,
        max_attempts=payload.max_attempts,
        active=True,
    )
    db.add(model)
    record_audit(
        db,
        request=request,
        action="webhook_endpoint.created",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="webhook_endpoint",
        resource_id=model.id,
        metadata={"name": model.name, "events": events, "url": model.url},
    )
    db.commit()
    db.refresh(model)
    return WebhookEndpointCreateResponse(
        id=model.id,
        name=model.name,
        url=model.url,
        secret_fingerprint=model.secret_fingerprint,
        subscribed_events=model.subscribed_events or [],
        max_attempts=model.max_attempts,
        active=model.active,
        created_at=model.created_at,
        secret=secret,
    )


def list_webhook_endpoints(db: Session, company_id: UUID) -> list[WebhookEndpoint]:
    return list(db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.company_id == company_id).order_by(WebhookEndpoint.created_at.desc())).all())


def deactivate_webhook_endpoint(db: Session, actor: User, endpoint_id: UUID, request: Request | None = None) -> WebhookEndpoint:
    model = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.company_id == actor.company_id))
    if model is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    model.active = False
    record_audit(
        db,
        request=request,
        action="webhook_endpoint.deactivated",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="webhook_endpoint",
        resource_id=model.id,
    )
    db.commit()
    db.refresh(model)
    return model


def enqueue_webhook_event(db: Session, company_id: UUID, event_name: str, payload: dict) -> list[WebhookDelivery]:
    endpoints = list(
        db.scalars(
            select(WebhookEndpoint).where(
                WebhookEndpoint.company_id == company_id,
                WebhookEndpoint.active.is_(True),
            )
        ).all()
    )
    deliveries: list[WebhookDelivery] = []
    for endpoint in endpoints:
        if event_name not in (endpoint.subscribed_events or []):
            continue
        secret = decrypt_secret(endpoint.encrypted_secret)
        delivery = WebhookDelivery(
            company_id=company_id,
            endpoint_id=endpoint.id,
            event_name=event_name,
            payload=payload,
            signature=webhook_signature(secret, payload),
            status="pending",
            attempts=0,
        )
        db.add(delivery)
        deliveries.append(delivery)
    if deliveries:
        db.flush()
    return deliveries


def list_deliveries(db: Session, company_id: UUID, endpoint_id: UUID) -> list[WebhookDelivery]:
    endpoint = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.company_id == company_id))
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return list(
        db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.company_id == company_id, WebhookDelivery.endpoint_id == endpoint_id)
            .order_by(WebhookDelivery.created_at.desc())
        ).all()
    )


def retry_delivery(db: Session, actor: User, delivery_id: UUID, request: Request | None = None) -> WebhookDelivery:
    delivery = db.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.company_id == actor.company_id,
        )
    )
    if delivery is None:
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    endpoint = db.get(WebhookEndpoint, delivery.endpoint_id)
    if endpoint is None or endpoint.company_id != actor.company_id:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    if delivery.status == "delivered":
        raise HTTPException(status_code=409, detail="Webhook delivery already completed")
    delivery.attempts += 1
    if delivery.attempts >= endpoint.max_attempts:
        delivery.status = "dead_letter"
        delivery.last_error = "Maximum delivery attempts reached; waiting for manual intervention."
    else:
        delivery.status = "pending"
        delivery.last_error = None
    record_audit(
        db,
        request=request,
        action="webhook_delivery.retry_requested",
        company_id=actor.company_id,
        actor_user_id=actor.id,
        resource_type="webhook_delivery",
        resource_id=delivery.id,
        metadata={"attempts": delivery.attempts, "status": delivery.status},
    )
    db.commit()
    db.refresh(delivery)
    return delivery


def _payload_hash(method: str, path: str, payload: Any) -> str:
    canonical = json.dumps({"method": method.upper(), "path": path, "payload": payload}, separators=(",", ":"), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def begin_idempotency(
    db: Session,
    actor: User,
    request: Request,
    key: str | None,
    payload: Any,
) -> tuple[IdempotencyRecord | None, JSONResponse | None]:
    if not key:
        return None, None
    if len(key) > MAX_IDEMPOTENCY_KEY_LENGTH or not key.strip():
        raise HTTPException(status_code=422, detail="Invalid Idempotency-Key")
    request_hash = _payload_hash(request.method, request.url.path, payload)
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.company_id == actor.company_id,
            IdempotencyRecord.idempotency_key == key,
        )
    )
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=409, detail="Idempotency key was already used with a different request")
        if existing.state == "processing":
            raise HTTPException(status_code=409, detail="A request with this Idempotency-Key is still processing")
        return None, JSONResponse(status_code=existing.response_status or 200, content=existing.response_body)

    record = IdempotencyRecord(
        company_id=actor.company_id,
        actor_user_id=actor.id,
        idempotency_key=key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
        state="processing",
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.company_id == actor.company_id,
                IdempotencyRecord.idempotency_key == key,
            )
        )
        if existing and existing.request_hash == request_hash and existing.state == "completed":
            return None, JSONResponse(status_code=existing.response_status or 200, content=existing.response_body)
        raise HTTPException(status_code=409, detail="A request with this Idempotency-Key is already processing")
    return record, None


def complete_idempotency(db: Session, record: IdempotencyRecord, status_code: int, body: dict | list) -> None:
    record.state = "completed"
    record.response_status = status_code
    record.response_body = body
    record.completed_at = datetime.now(timezone.utc)
    db.commit()


def abort_idempotency(db: Session, record: IdempotencyRecord) -> None:
    db.delete(record)
    db.commit()
