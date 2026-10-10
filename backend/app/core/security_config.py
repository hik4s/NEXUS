from app.core.config import settings

_INSECURE_DEFAULT = "nexus-dev-secret-key-change-before-production-please"


def validate_security_configuration() -> None:
    env = settings.APP_ENV.lower().strip()
    if env in {"production", "prod"}:
        if settings.SECRET_KEY == _INSECURE_DEFAULT or len(settings.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY must be a unique secret of at least 32 characters in production")
        if settings.ENABLE_DOCS_IN_PRODUCTION:
            raise RuntimeError("ENABLE_DOCS_IN_PRODUCTION must remain false unless explicitly reviewed")
        if settings.STORAGE_BACKEND == "s3" and not settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required in production when STORAGE_BACKEND=s3")


def is_secure_configured() -> bool:
    if settings.APP_ENV.lower() in {"production", "prod"}:
        return settings.SECRET_KEY != _INSECURE_DEFAULT and len(settings.SECRET_KEY) >= 32
    return True
