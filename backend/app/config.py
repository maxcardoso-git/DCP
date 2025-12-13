import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    database_url: str = Field(default="postgresql+asyncpg://dcp:dcp@db:5432/dcp")
    app_port: int = Field(default=8000)
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])
    api_prefix: str = "/api/v2/dcp"


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        app_port=int(os.getenv("APP_PORT", Settings.model_fields["app_port"].default)),
        allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        api_prefix=os.getenv("API_PREFIX", Settings.model_fields["api_prefix"].default),
    )
