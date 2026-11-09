from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session

from app.api.v1.router import create_api_router
from app.core.config import settings
from app.core.middleware import SecurityAndObservabilityMiddleware
from app.core.upload_limits import BoundedUploadMiddleware
from app.services.order_import_parser import MAX_BYTES
from app.core.observability import configure_logging
from app.core.security_config import validate_security_configuration
from app.core.readiness import database_readiness
from app.db.session import engine
from app.models import Base
from app.rbac.service import ensure_rbac_seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    validate_security_configuration()
    if settings.DATABASE_URL.startswith('sqlite'):
        Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        ensure_rbac_seed(db)
    yield


def create_app() -> FastAPI:
    app_kwargs = {
        'title': settings.APP_NAME,
        'version': settings.APP_VERSION,
        'description': 'NEXUS — AI-Powered Business Operating System',
        'lifespan': lifespan,
    }
    if settings.APP_ENV.lower() in {'production', 'prod'} and not settings.ENABLE_DOCS_IN_PRODUCTION:
        app_kwargs.update({'docs_url': None, 'redoc_url': None, 'openapi_url': None})
    application = FastAPI(**app_kwargs)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts())
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins(), allow_credentials=True,
        allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Authorization', 'Content-Type', 'X-API-Key', 'Idempotency-Key', 'X-Request-ID'],
        expose_headers=['X-Page', 'X-Page-Size', 'X-Total-Count', 'X-Total-Pages'],
    )
    application.add_middleware(BoundedUploadMiddleware,
        path=f'{settings.API_V1_PREFIX}/order-imports', max_body_bytes=MAX_BYTES + 64 * 1024)
    application.add_middleware(SecurityAndObservabilityMiddleware)
    application.include_router(create_api_router(settings.APP_PROFILE), prefix=settings.API_V1_PREFIX)

    @application.get('/', tags=['meta'])
    def root() -> dict[str, str]:
        return {'name': settings.APP_NAME, 'version': settings.APP_VERSION, 'docs': '/docs'}

    application.add_api_route('/readiness', database_readiness, methods=['GET'], tags=['meta'])
    return application


app = create_app()
