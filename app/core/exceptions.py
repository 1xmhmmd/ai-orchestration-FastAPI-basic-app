"""
Domain-specific exceptions and their FastAPI handlers.

Rule of thumb for a senior-level API: never leak internal exception
details (stack traces, library error strings) to the client. Log the
full detail server-side, return a clean, stable, documented error
contract to the caller.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"

    def __init__(self, message: str, *, error_code: str | None = None):
        self.message = message
        if error_code:
            self.error_code = error_code
        super().__init__(message)


class InvalidAPIKeyError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "invalid_api_key"


class RateLimitExceededError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"


class UpstreamLLMError(AppError):
    """Raised when the LLM provider fails after all retries."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "upstream_llm_error"


class AgentExecutionError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "agent_execution_error"


def _error_payload(error_code: str, message: str) -> dict:
    return {"error": {"code": error_code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("Handled AppError: %s (%s)", exc.message, exc.error_code)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(exc.error_code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload("validation_error", "Invalid request payload."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload("http_error", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internals — log full traceback server-side only.
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("internal_error", "An unexpected error occurred."),
        )
