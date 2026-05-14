"""Application settings loaded from environment / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Market-data provider
    data_provider: str = "yfinance"

    # User defaults
    base_currency: str = "EUR"
    locale: str = "en"

    # Caching
    cache_dir: Path = Path("./data/cache")
    quote_cache_ttl_seconds: int = 60
    history_cache_ttl_hours: int = 24

    # Logging
    log_level: str = "INFO"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # CORS — Vite dev server by default
    frontend_origin: str = "http://localhost:5173"

    # Supported UI languages — keep in sync with frontend/src/i18n
    supported_languages: list[str] = Field(default_factory=lambda: ["en", "de"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
