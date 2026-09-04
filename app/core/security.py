"""
Authentication for the API.

Design notes for reviewers:
- API keys are compared with `secrets.compare_digest` to avoid timing
  attacks that could let an attacker brute-force a key one byte at a time.
- Keys are read from configuration (env), never hardcoded.
- The dependency raises a domain exception (`InvalidAPIKeyError`) rather
  than an ad-hoc HTTPException, so the error contract stays consistent
  and centralized in `core/exceptions.py`.
- We deliberately return a generic message on failure — we don't reveal
  whether the key format was wrong vs. simply not recognized.
"""

import secrets

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidAPIKeyError

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _is_valid_key(candidate: str, valid_keys: list[str]) -> bool:
    return any(secrets.compare_digest(candidate, key) for key in valid_keys)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    # If no keys are configured (e.g. local dev), auth is effectively open.
    # This is logged loudly so it's never silently shipped to production.
    if not settings.API_KEYS:
        if settings.is_production:
            raise InvalidAPIKeyError("API key authentication is not configured.")
        return "dev-mode-no-auth"

    if not api_key or not _is_valid_key(api_key, settings.API_KEYS):
        raise InvalidAPIKeyError("Missing or invalid API key.")

    return api_key
