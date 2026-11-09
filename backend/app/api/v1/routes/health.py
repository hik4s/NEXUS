from fastapi import APIRouter, Response

from app.core.config import settings
from app.core.observability import metrics
from app.core.readiness import database_readiness

router = APIRouter(prefix="/health")


@router.get("", summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness check")
async def readiness_check() -> dict[str, str]:
    result = await database_readiness()
    if settings.APP_PROFILE == 'portfolio':
        return result
    redis_status = "disabled"
    if settings.REDIS_ENABLED:
        try:
            import redis
            client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.ping()
            redis_status = "ok"
        except Exception:
            redis_status = "unavailable"
    return {**result, "redis": redis_status}


@router.get("/metrics", include_in_schema=False)
def metrics_endpoint() -> Response:
    if not settings.ENABLE_METRICS_ENDPOINT:
        return Response(status_code=404)
    return Response(content=metrics.prometheus(), media_type="text/plain; version=0.0.4")
