"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = Field(default="SecureApp", description="Application name")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    environment: Literal["development", "testing", "staging", "production"] = Field(default="development")
    secret_key: str = Field(
        default="change-me-in-production-use-a-long-random-string-here",
        min_length=32,
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1)
    log_level: str = Field(default="info")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field(default="postgresql://localhost:5432/app_db")
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: int = Field(default=30, ge=1)
    db_echo: bool = Field(default=False)

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=20, ge=1)
    cache_ttl: int = Field(default=300, ge=0, description="Default cache TTL in seconds")

    # ── Auth / JWT ────────────────────────────────────────────────────────────
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = Field(default=["http://localhost:3000"])
    allowed_methods: list[str] = Field(default=["GET", "POST", "PUT", "DELETE", "PATCH"])
    allowed_headers: list[str] = Field(default=["*"])

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window: int = Field(default=60, ge=1, description="Window in seconds")

    # ── Observability ─────────────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    enable_metrics: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Ensure DATABASE_URL is never empty."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        """Return True when running tests."""
        return self.environment == "testing"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
