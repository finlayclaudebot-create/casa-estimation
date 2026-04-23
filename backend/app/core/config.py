"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Values are loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "casa-estimation"
    environment: str = Field(default="development")
    api_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://casa:casa@localhost:5432/casa",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    storage_root: Path = Field(default=Path("storage"))
    max_upload_bytes: int = 100 * 1024 * 1024  # 100 MB

    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )

    @property
    def effective_celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def effective_celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
