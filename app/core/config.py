"""
Application configuration.

Uses pydantic-settings so every value can be overridden via environment
variables or a `.env` file without touching source code. Never hardcode
secrets (API keys, tokens) anywhere else in the codebase — always route
them through here so they stay centralized, typed, and easy to audit.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field
from pydantic.functional_validators import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv_to_list(v: object) -> object:
    """Parse comma-separated env strings into a list.

    `NoDecode` tells pydantic-settings not to try JSON-decoding this env
    var first (its default behaviour for list-typed fields), which would
    otherwise reject a plain comma-separated value like `key1,key2` in a
    `.env` file.
    """
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v


CsvList = Annotated[list[str], NoDecode, BeforeValidator(_csv_to_list)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- General
    APP_NAME: str = "Multi-Agent Orchestration API"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # -- Security 
    # API key(s) allowed to call protected endpoints. Comma-separated in env.
    API_KEYS: CsvList = Field(default_factory=list)
    CORS_ORIGINS: CsvList = Field(default_factory=lambda: ["http://localhost:3000"])
    RATE_LIMIT_PER_MINUTE: int = 30

    # -- LLM provider 
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 3
    LLM_MAX_OUTPUT_TOKENS: int = 1024

    # -- Caching (Redis) 
    REDIS_URL: str | None = None
    CACHE_TTL_SECONDS: int = 3600

    # --Orchestration 
    MAX_AGENT_STEPS: int = 5
    MAX_INPUT_CHARS: int = 8000  # guards against prompt-injection / cost blowups

    # -- Logging 
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so the environment is parsed exactly once."""
    return Settings()
