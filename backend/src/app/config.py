"""Twelve-factor configuration: everything comes from environment variables (or .env in dev)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Literal["local", "test", "staging", "production"] = "local"
    database_url: str = "mysql+asyncmy://app:app@127.0.0.1:3306/app"
    db_pool_size: int = 10

    # Dev uses HS256 with a shared secret. In production, use an OIDC provider (RS256 + JWKS).
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-dev-only-change-me")
    jwt_issuer: str = "https://auth.local"
    jwt_audience: str = "app-api"
    jwt_algorithms: list[str] = Field(default_factory=lambda: ["HS256"])

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    run_outbox_relay: bool = True
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
