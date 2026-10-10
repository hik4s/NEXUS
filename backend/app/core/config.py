from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_NAME: str = "NEXUS API"
    APP_VERSION: str = "0.18.0"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "nexus-dev-secret-key-change-before-production-please"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_ALGORITHM: str = "HS256"

    DATABASE_URL: str = "sqlite:///./data/nexus.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True
    JOB_DEFAULT_MAX_ATTEMPTS: int = 3
    JOB_WORKER_POLL_SECONDS: float = 2.0

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_DIR: str = "./data/storage"
    S3_BUCKET: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: str | None = None
    IMPORT_MAX_BYTES: int = 20 * 1024 * 1024
    MAX_REQUEST_BODY_BYTES: int = 25 * 1024 * 1024
    PLAYWRIGHT_ALLOWED_HOSTS: str = ""
    PLAYWRIGHT_TIMEOUT_MS: int = 30000

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver"
    ENABLE_DOCS_IN_PRODUCTION: bool = False
    ENABLE_METRICS_ENDPOINT: bool = True

    AI_PROVIDER: str = "mock"
    AI_MODEL: str = "nexus-mock-1"
    AI_BASE_URL: str = ""
    AI_API_KEY: str = ""
    AI_TIMEOUT_SECONDS: float = 20.0
    AI_MAX_RETRIES: int = 2
    AI_MAX_TOOL_CALLS: int = 5
    AI_MAX_OUTPUT_TOKENS: int = 1200
    AI_FALLBACK_TO_MOCK: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    def trusted_hosts(self) -> list[str]:
        return [item.strip() for item in self.TRUSTED_HOSTS.split(",") if item.strip()]


settings = Settings()
