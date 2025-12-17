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

    # Authentication
    bearer_token: str | None = None

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
        policy_path=os.getenv("POLICY_PATH"),
        redis_url=os.getenv("REDIS_URL"),
        worker_interval=int(os.getenv("WORKER_INTERVAL", "60")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        metrics_enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "development"),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "100")),
    )
