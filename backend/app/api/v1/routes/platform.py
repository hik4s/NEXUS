from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.identity.dependencies import get_current_user, require_permission
from app.models.platform import ApiKey, WebhookDelivery, WebhookEndpoint
from app.models.user import User
from app.platform.service import (
    authenticate_api_key,
    create_api_key,
    create_webhook_endpoint,
    deactivate_webhook_endpoint,
    list_api_keys,
    list_deliveries,
    list_webhook_endpoints,
    retry_delivery,
    revoke_api_key,
    enqueue_webhook_event,
)
from app.schemas.platform import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyRead,
    WebhookDeliveryRead,
    WebhookEndpointCreate,
    WebhookEndpointCreateResponse,
    WebhookEndpointRead,
    WebhookTestEvent,
)

router = APIRouter(prefix="/platform")


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key_route(
    payload: ApiKeyCreate,
    request: Request,
    current_user: User = Depends(require_permission("platform:api_keys")),
    db: Session = Depends(get_db),
):
    return create_api_key(db, current_user, payload, request=request)


@router.get("/api-keys", response_model=list[ApiKeyRead])
def list_api_keys_route(
    current_user: User = Depends(require_permission("platform:api_keys")),
    db: Session = Depends(get_db),
) -> list[ApiKey]:
    return list_api_keys(db, current_user.company_id)


@router.delete("/api-keys/{key_id}", response_model=ApiKeyRead)
def revoke_api_key_route(
    key_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("platform:api_keys")),
    db: Session = Depends(get_db),
) -> ApiKey:
    return revoke_api_key(db, current_user, key_id, request=request)


@router.get("/api-keys/validate")
def validate_api_key_route(
    x_api_key: str = Header(..., alias="X-API-Key"),
    scope: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    api_key = authenticate_api_key(db, x_api_key, required_scope=scope)
    return {
        "valid": True,
        "company_id": str(api_key.company_id),
        "scopes": api_key.scopes or [],
        "key_prefix": api_key.key_prefix,
    }


@router.post("/webhooks", response_model=WebhookEndpointCreateResponse, status_code=status.HTTP_201_CREATED)
def create_webhook_route(
    payload: WebhookEndpointCreate,
    request: Request,
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
):
    return create_webhook_endpoint(db, current_user, payload, request=request)


@router.get("/webhooks", response_model=list[WebhookEndpointRead])
def list_webhooks_route(
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
) -> list[WebhookEndpoint]:
    return list_webhook_endpoints(db, current_user.company_id)


@router.delete("/webhooks/{endpoint_id}", response_model=WebhookEndpointRead)
def deactivate_webhook_route(
    endpoint_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
) -> WebhookEndpoint:
    return deactivate_webhook_endpoint(db, current_user, endpoint_id, request=request)


@router.get("/webhooks/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryRead])
def list_webhook_deliveries_route(
    endpoint_id: UUID,
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
) -> list[WebhookDelivery]:
    return list_deliveries(db, current_user.company_id, endpoint_id)


@router.post("/webhook-deliveries/{delivery_id}/retry", response_model=WebhookDeliveryRead)
def retry_webhook_delivery_route(
    delivery_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
) -> WebhookDelivery:
    return retry_delivery(db, current_user, delivery_id, request=request)



@router.post("/webhooks/{endpoint_id}/test-event", response_model=list[WebhookDeliveryRead])
def test_webhook_event_route(
    endpoint_id: UUID,
    payload: WebhookTestEvent,
    request: Request,
    current_user: User = Depends(require_permission("platform:webhooks")),
    db: Session = Depends(get_db),
) -> list[WebhookDelivery]:
    endpoint = db.get(WebhookEndpoint, endpoint_id)
    if endpoint is None or endpoint.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    if payload.event_name not in (endpoint.subscribed_events or []):
        raise HTTPException(status_code=409, detail="Endpoint is not subscribed to this event")
    payload_body = dict(payload.payload)
    deliveries = enqueue_webhook_event(db, current_user.company_id, payload.event_name, payload_body)
    db.commit()
    for delivery in deliveries:
        db.refresh(delivery)
    return deliveries
