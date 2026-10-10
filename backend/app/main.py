from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import SecurityAndObservabilityMiddleware
from app.core.observability import configure_logging
from app.core.security_config import validate_security_configuration
from app.db.session import engine
from app.models import Base
from app.rbac.service import ensure_rbac_seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    validate_security_configuration()
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_rbac_seed(db)
    yield


app_kwargs = {
    "title": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "description": "NEXUS — AI-Powered Business Operating System",
    "lifespan": lifespan,
}
if settings.APP_ENV.lower() in {"production", "prod"} and not settings.ENABLE_DOCS_IN_PRODUCTION:
    app_kwargs.update({"docs_url": None, "redoc_url": None, "openapi_url": None})

app = FastAPI(**app_kwargs)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts())
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "Idempotency-Key", "X-Request-ID"],
)
app.add_middleware(SecurityAndObservabilityMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION, "docs": "/docs"}


@app.get("/readiness", tags=["meta"])
def readiness() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
