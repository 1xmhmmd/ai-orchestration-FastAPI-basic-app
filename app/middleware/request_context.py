"""
Cross-cutting HTTP middleware.

- `RequestContextMiddleware`: assigns a correlation id to every request
  (reusing an inbound `X-Request-ID` if the caller/load-balancer already
  set one), stores it in a ContextVar for logging, measures latency, and
  echoes it back in the response so clients can reference it in support
  requests.
- `SecurityHeadersMiddleware`: sets a conservative baseline of security
  headers. This is the kind of thing a security engineer checks for in
  review — it costs nothing and closes off several classes of
  browser-based attacks (clickjacking, MIME sniffing, etc.).
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import request_id_ctx_var

logger = logging.getLogger("app.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx_var.set(request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
        return response
