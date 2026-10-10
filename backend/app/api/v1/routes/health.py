from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import metrics
from app.db.session import engine

router = APIRouter(prefix="/health")


@router.get("", summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness check")
def readiness_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    redis_status = "disabled"
    if settings.REDIS_ENABLED:
        try:
            import redis
            client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "unavailable"
    return {"status": "ready", "database": "ok", "redis": redis_status}


@router.get("/metrics", include_in_schema=False)
def metrics_endpoint() -> Response:
    if not settings.ENABLE_METRICS_ENDPOINT:
        return Response(status_code=404)
    return Response(content=metrics.prometheus(), media_type="text/plain; version=0.0.4")
