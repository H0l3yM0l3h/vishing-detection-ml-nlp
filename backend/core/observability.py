"""
core/observability.py — structured logging, request IDs, and error handling.
============================================================================
Why this module exists
----------------------
The original backend had no logging configuration, no exception handlers and
no request correlation. When the Supabase project became unreachable, every
login raised an uncaught exception and FastAPI returned Starlette's bare
plain-text ``500 Internal Server Error`` — with nothing written anywhere that
said *why*. The endpoint was structurally incapable of reporting its own
failure.

Three things fix that permanently:

1. ``RequestContextMiddleware`` stamps every request with an ID and logs its
   outcome, so a user-visible error can be traced to a specific log line.
2. ``register_exception_handlers`` converts unhandled exceptions into a JSON
   envelope carrying that request ID — and logs the full traceback server-side
   while telling the client nothing about the internals.
3. ``DatabaseUnavailable`` is mapped to **503**, not 500. A paused database is
   a dependency outage, not a bug in the request, and the status code should
   say so.

Security note (FYP Ch.4): error responses deliberately carry no exception
text. The previous code returned ``str(e)`` to the client in five places,
including raw httpx errors that embed the full upstream request URL and its
query string.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Correlates log lines with the response a user actually saw.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class DatabaseUnavailable(Exception):
    """The datastore could not be reached or refused the operation.

    Raised by the database layer so routes never have to distinguish a paused
    project from a network blip from an RLS refusal — all of them mean
    "the request cannot be served right now", which is a 503.
    """

    def __init__(self, message: str = "Database temporarily unavailable", *, cause: str = ""):
        super().__init__(message)
        self.message = message
        self.cause = cause


class _JsonFormatter(logging.Formatter):
    """One JSON object per line — greppable locally, parseable in HF Space logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Install the JSON formatter on the root logger. Idempotent."""
    root = logging.getLogger()
    root.setLevel(level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    # uvicorn's own access log duplicates what RequestContextMiddleware emits.
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("shieldguard")


log = logging.getLogger("shieldguard")


def log_event(level: int, event: str, **fields) -> None:
    """Log a structured event: ``log_event(logging.WARNING, "db.slow", ms=812)``."""
    log.log(level, event, extra={"extra_fields": fields})


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request ID, time the request, and log its outcome."""

    # Paths that would otherwise flood the log — the frontend polls health
    # every 30 seconds per open tab.
    _QUIET_PATHS = {"/api/health", "/api/health_detailed"}

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log.exception(
                "request.unhandled",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    }
                },
            )
            request_id_ctx.reset(token)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        quiet = request.url.path in self._QUIET_PATHS and response.status_code < 400
        if not quiet:
            log_event(
                logging.WARNING if response.status_code >= 400 else logging.INFO,
                "request.complete",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )
        request_id_ctx.reset(token)
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers so no code path can return a bare, unlogged 500."""

    @app.exception_handler(DatabaseUnavailable)
    async def _database_unavailable(request: Request, exc: DatabaseUnavailable):
        log_event(
            logging.ERROR,
            "db.unavailable",
            path=request.url.path,
            cause=exc.cause or str(exc),
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": exc.message,
                "code": "database_unavailable",
                "request_id": request_id_ctx.get(),
            },
            headers={"Retry-After": "30"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException):
        # Deliberate, already-safe messages raised by our own routes.
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request_id_ctx.get()},
            headers=getattr(exc, "headers", None) or {},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        # Field names and positions only — never the submitted values, which
        # for this API include passwords and call transcripts.
        fields = [".".join(str(p) for p in err.get("loc", [])) for err in exc.errors()]
        log_event(logging.INFO, "request.invalid", path=request.url.path, fields=fields)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "fields": fields,
                "request_id": request_id_ctx.get(),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception(
            "request.error",
            extra={"extra_fields": {"path": request.url.path, "type": type(exc).__name__}},
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred. Quote the request ID when reporting this.",
                "request_id": request_id_ctx.get(),
            },
        )
