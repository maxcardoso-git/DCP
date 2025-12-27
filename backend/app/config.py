import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(default="postgresql+asyncpg://dcp:dcp@db:5432/dcp")

    # Server
    app_port: int = Field(default=8000)
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_prefix: str = "/api/v2/dcp"

    # Authentication (legacy bearer token)
    bearer_token: str | None = None

    # TAH Integration
    tah_base_url: str = Field(default="http://72.61.52.70:3050")
    tah_jwks_url: str = Field(default="http://72.61.52.70:3050/.well-known/jwks.json")
    tah_issuer: str = Field(default="http://72.61.52.70:3050")
    app_id: str = Field(default="decision_control_plane")
    tah_enabled: bool = Field(default=True)
    session_expire_hours: int = Field(default=24)
    frontend_url: str = Field(default="http://72.61.52.70:8100")
    cookie_domain: str | None = Field(default=None)  # Set to domain for cross-port sharing

    # Policy Engine
    policy_path: str | None = None

    # Redis (for events and caching)
    redis_url: str | None = None

    # Worker
    worker_interval: int = Field(default=60)  # seconds

    # Observability
    log_level: str = Field(default="INFO")
    metrics_enabled: bool = Field(default=True)

    # Security
    environment: str = Field(default="development")
    rate_limit_per_minute: int = Field(default=100)


def get_settings() -> Settings:
    """Load settings from environment variables."""
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        app_port=int(os.getenv("APP_PORT", Settings.model_fields["app_port"].default)),
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        api_prefix=os.getenv("API_PREFIX", Settings.model_fields["api_prefix"].default),
        bearer_token=os.getenv("BEARER_TOKEN"),
        # TAH Integration
        tah_base_url=os.getenv("TAH_BASE_URL", Settings.model_fields["tah_base_url"].default),
        tah_jwks_url=os.getenv("TAH_JWKS_URL", Settings.model_fields["tah_jwks_url"].default),
        tah_issuer=os.getenv("TAH_ISSUER", Settings.model_fields["tah_issuer"].default),
        app_id=os.getenv("APP_ID", Settings.model_fields["app_id"].default),
        tah_enabled=os.getenv("TAH_ENABLED", "true").lower() == "true",
        session_expire_hours=int(os.getenv("SESSION_EXPIRE_HOURS", "24")),
        frontend_url=os.getenv("FRONTEND_URL", Settings.model_fields["frontend_url"].default),
        cookie_domain=os.getenv("COOKIE_DOMAIN"),
        # Policy Engine
        policy_path=os.getenv("POLICY_PATH"),
        redis_url=os.getenv("REDIS_URL"),
        worker_interval=int(os.getenv("WORKER_INTERVAL", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "development"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
    )
