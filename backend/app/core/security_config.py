from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

from app.core.config import settings

_INSECURE_DEFAULT = "nexus-dev-secret-key-change-before-production-please"


def validate_security_configuration() -> None:
    env = settings.APP_ENV.lower().strip()
    if env in {"production", "prod"}:
        if settings.SECRET_KEY == _INSECURE_DEFAULT or len(settings.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY must be a unique secret of at least 32 characters in production")
        if settings.ENABLE_DOCS_IN_PRODUCTION:
            raise RuntimeError("ENABLE_DOCS_IN_PRODUCTION must remain false unless explicitly reviewed")
        if settings.APP_PROFILE == 'portfolio':
            if settings.PUBLIC_REGISTRATION_ENABLED:
                raise RuntimeError('PUBLIC_REGISTRATION_ENABLED must be false for the public portfolio deployment')
            if not settings.DATABASE_URL.startswith('postgresql+psycopg://'):
                raise RuntimeError('The production portfolio requires PostgreSQL with psycopg')
            if make_url(settings.DATABASE_URL).query.get('sslmode') not in {'require', 'verify-ca', 'verify-full'}:
                raise RuntimeError('TLS is required for the production portfolio database')
            origins = settings.cors_origins()
            for origin in origins:
                parsed = urlsplit(origin)
                if (parsed.scheme != 'https' or not parsed.hostname or '*' in origin
                        or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment):
                    raise RuntimeError('CORS_ORIGINS must contain explicit HTTPS origins')
            if not origins:
                raise RuntimeError('CORS_ORIGINS must contain explicit HTTPS origins')
            if not settings.trusted_hosts() or any('*' in host for host in settings.trusted_hosts()):
                raise RuntimeError('TRUSTED_HOSTS must contain explicit host names')
        if settings.APP_PROFILE == 'full' and settings.STORAGE_BACKEND == "s3" and not settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required in production when STORAGE_BACKEND=s3")


def is_secure_configured() -> bool:
    if settings.APP_ENV.lower() in {"production", "prod"}:
        return settings.SECRET_KEY != _INSECURE_DEFAULT and len(settings.SECRET_KEY) >= 32
    return True
