"""Application settings loaded via pydantic-settings.

This module defines a Settings class and a cached accessor that
loads configuration from environment variables and a .env file
located at the project root.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Compute the project root (repo root), e.g.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """App configuration.

    Values are sourced from (in order of precedence):
    1) Environment variables
    2) .env file(s) — see model_config.env_file
    3) Defaults defined on the fields
    """

    app_name: str = Field(
        default="vibe",
        description="Vibe coding supervisor without battaries",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode (more verbose logs, etc.)",
    )
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = Field(
        default="INFO",
        description="Logging level.",
    )
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(
        # Read .env from the project root
        env_file=(PROJECT_ROOT / ".env",),
        env_file_encoding="utf-8",
        # No prefix; environment variables may be written as APP_NAME, DEBUG, etc.
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


# Convenient module-level instance
settings: Settings = get_settings()
