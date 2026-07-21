"""
backend/middleware/logging.py
-------------------------------
Structured JSON request logging (structlog), stdlib-logging output.

Every request logs one JSON line to stdout with:
    request_id, method, path, status, latency_ms, user_id, client_ip

Maturity: Working Prototype (Phase 1 / A4)
"""

from __future__ import annotations
import logging
import sys
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.auth.service import get_current_user_from_token


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger("sessionguard.request")


def _user_id_from_request(request: Request) -> int | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    current = get_current_user_from_token(authorization)
    return current.get("user_id") if current else None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            log.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                latency_ms=latency_ms,
                user_id=_user_id_from_request(request),
                client_ip=getattr(getattr(request, "client", None), "host", "unknown"),
            )
            raise

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            latency_ms=latency_ms,
            user_id=_user_id_from_request(request),
            client_ip=getattr(getattr(request, "client", None), "host", "unknown"),
        )
        return response
