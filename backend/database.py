"""
database.py — Supabase backend for ShieldGuard (FastAPI version)
================================================================
Every Supabase query below is IDENTICAL to the previous version. The tables,
columns, filters and timestamp format are unchanged, so an existing project
keeps working with no migration and no data loss.

What changed is everything *around* the queries:

1. **Timeouts.** The client now carries an explicit PostgREST timeout. Without
   one, a paused project made every call hang for the full default before
   failing.
2. **A circuit breaker.** After N consecutive failures the layer fails fast for
   a cooldown period instead of making every subsequent request pay the
   timeout. A dead dependency should degrade in milliseconds, not seconds.
3. **A single failure type.** Any transport error, timeout, or PostgREST
   refusal (including a row-level-security denial) is re-raised as
   ``DatabaseUnavailable``, which the API layer maps to 503.

Why this matters (FYP Ch.5): the login endpoint previously made four
unguarded database calls. When the Supabase project auto-paused, the first of
them raised, FastAPI returned a bare ``500 Internal Server Error``, and
nothing was logged. The outage was indistinguishable from a code defect.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from supabase import Client, ClientOptions, create_client

from core.config import settings
from core.observability import DatabaseUnavailable, log_event

MAX_ATTEMPTS          = 5
LOCKOUT_MINUTES       = 15
MAX_ANALYSES_PER_HOUR = 30


# -----------------------------------------------
# CIRCUIT BREAKER
# -----------------------------------------------

class _CircuitBreaker:
    """Fail fast while a dependency is known to be down.

    States: closed (normal) → open (short-circuit) → closed on first success
    after the cooldown elapses.
    """

    def __init__(self, threshold: int, cooldown: float):
        self.threshold = threshold
        self.cooldown = cooldown
        self._failures = 0
        self._opened_at = 0.0
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._failures < self.threshold:
                return False
            if time.monotonic() - self._opened_at >= self.cooldown:
                # Cooldown elapsed — allow one probe through.
                self._failures = self.threshold - 1
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            if self._failures:
                log_event(logging.INFO, "db.recovered", after_failures=self._failures)
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures == self.threshold:
                self._opened_at = time.monotonic()
                log_event(
                    logging.ERROR,
                    "db.circuit_open",
                    failures=self._failures,
                    cooldown_seconds=self.cooldown,
                )

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = 0.0

    def status(self) -> str:
        return "open" if self.is_open else "closed"


_breaker = _CircuitBreaker(settings.DB_BREAKER_THRESHOLD, settings.DB_BREAKER_COOLDOWN_SECONDS)


# Constraint violations and other request-level refusals mean "this particular
# operation is invalid", not "the database is down". Counting them as
# infrastructure failures lets an ordinary user action open a breaker shared by
# every endpoint.
_BUSINESS_ERROR_MARKERS = (
    "duplicate key",
    "already exists",
    "unique constraint",
    "violates unique",
    "23505",           # PostgreSQL unique_violation
    "23503",           # foreign_key_violation
    "23514",           # check_violation
)


def _is_infrastructure_failure(exc: Exception) -> bool:
    """True when an exception indicates the datastore itself is unhealthy.

    Errors caused by the *content* of a request (a duplicate username, a
    constraint violation) are the caller's problem and must not degrade
    availability for everyone else.
    """
    text = f"{type(exc).__name__} {exc}".lower()
    if any(marker in text for marker in _BUSINESS_ERROR_MARKERS):
        return False
    return True


def resilient(operation: str):
    """Wrap a Supabase call: short-circuit, time, classify, log, re-raise as 503."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if _breaker.is_open:
                raise DatabaseUnavailable(
                    "Database is temporarily unreachable. Please try again shortly.",
                    cause=f"circuit_open:{operation}",
                )
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                # Only infrastructure failures should count toward the breaker.
                #
                # Previously ANY exception tripped it, including expected
                # business-logic errors. create_user raises on a UNIQUE
                # violation when a username is taken, so three racing
                # duplicate registrations could open a breaker that is shared
                # by every database-backed endpoint — turning an ordinary
                # "username already exists" into a 30-second outage of login,
                # analysis and history for every user of the system.
                if _is_infrastructure_failure(exc):
                    _breaker.record_failure()
                elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                log_event(
                    logging.ERROR,
                    "db.call_failed",
                    operation=operation,
                    duration_ms=elapsed_ms,
                    error_type=type(exc).__name__,
                    # repr is kept server-side only; it never reaches the client.
                    error=repr(exc)[:300],
                )
                raise DatabaseUnavailable(
                    "Database is temporarily unreachable. Please try again shortly.",
                    cause=f"{operation}:{type(exc).__name__}",
                ) from exc

            _breaker.record_success()
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            if elapsed_ms > 1000:
                log_event(logging.WARNING, "db.slow", operation=operation, duration_ms=elapsed_ms)
            return result

        return wrapper

    return decorator


# -----------------------------------------------
# CLIENT
# -----------------------------------------------

@functools.lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Cached Supabase client with an explicit timeout.

    Constructing a client performs no network I/O — which is precisely why the
    old ``/api/health`` check, which only called this function, reported
    ``supabase: true`` while the database was completely unreachable.
    Use :func:`health_check` for a real answer.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
        options=ClientOptions(
            postgrest_client_timeout=settings.SUPABASE_TIMEOUT_SECONDS,
            storage_client_timeout=settings.SUPABASE_TIMEOUT_SECONDS,
        ),
    )


def init_db():
    """No-op — tables are created via supabase_schema.sql."""
    pass


def health_check() -> dict:
    """Actually query the database and report what happened.

    Returns ``{"ok", "latency_ms", "detail", "breaker", "key_role"}``.
    Never raises: the health endpoint must stay up when the database is down.
    """
    started = time.perf_counter()
    result = {
        "ok": False,
        "latency_ms": None,
        "detail": "",
        "breaker": _breaker.status(),
        "key_role": settings.supabase_key_role,
    }

    if _breaker.is_open:
        result["detail"] = "circuit breaker open — recent calls failed"
        return result

    try:
        sb = get_supabase()
        sb.table("users").select("username").limit(1).execute()
        result["ok"] = True
        result["detail"] = "reachable"
        _breaker.record_success()
    except Exception as exc:
        _breaker.record_failure()
        result["detail"] = f"unreachable ({type(exc).__name__})"
        log_event(logging.ERROR, "db.health_failed", error=repr(exc)[:300])

    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)

    # An anon key against RLS-protected tables makes SELECTs silently return
    # empty and INSERTs raise. Surface it rather than let it look healthy.
    if result["ok"] and result["key_role"] == "anon":
        result["detail"] = "reachable (warning: using anon key — RLS may block writes)"

    return result


def snapshot_counts() -> dict:
    """Row counts for the four tables, for before/after change verification.

    Used to prove that a schema or key change did not lose data. Returns
    ``-1`` for any table that could not be read rather than raising.
    """
    counts: dict[str, int] = {}
    for table in ("users", "login_attempts", "audit_log", "rate_limit"):
        try:
            resp = get_supabase().table(table).select("*", count="exact").limit(1).execute()
            counts[table] = resp.count if resp.count is not None else -1
        except Exception:
            counts[table] = -1
    return counts


# -----------------------------------------------
# USER MANAGEMENT
# -----------------------------------------------

@resilient("get_user")
def get_user(username: str):
    sb   = get_supabase()
    resp = (
        sb.table("users")
          .select("username, password_hash, role, last_login")
          .eq("username", username)
          .limit(1)
          .execute()
    )
    return resp.data[0] if resp.data else None


@resilient("create_user")
def create_user(username: str, password_hash: bytes):
    """Raises exception if username already exists (UNIQUE constraint)."""
    sb = get_supabase()
    sb.table("users").insert({
        "username":      username,
        "password_hash": password_hash.decode("utf-8"),
        "role":          "user",
        "created_at":    _now(),
    }).execute()


# -----------------------------------------------
# LOGIN ATTEMPTS — brute-force protection
# -----------------------------------------------

@resilient("record_login_attempt")
def record_login_attempt(username: str, success: bool):
    sb = get_supabase()
    sb.table("login_attempts").insert({
        "username":     username,
        "success":      success,
        "attempted_at": _now(),
    }).execute()

    if success:
        sb.table("users") \
          .update({"last_login": _now()}) \
          .eq("username", username) \
          .execute()


@resilient("is_locked_out")
def is_locked_out(username: str) -> tuple:
    """Returns (locked: bool, minutes_remaining: int)."""
    if not username:
        return False, 0

    sb     = get_supabase()
    cutoff = _ago(minutes=LOCKOUT_MINUTES)

    resp = (
        sb.table("login_attempts")
          .select("attempted_at", count="exact")
          .eq("username", username)
          .eq("success", False)
          .gte("attempted_at", cutoff)
          .execute()
    )
    count = _count(resp)

    if count < MAX_ATTEMPTS:
        return False, 0

    # Find oldest failure in window to calculate unlock time
    oldest = (
        sb.table("login_attempts")
          .select("attempted_at")
          .eq("username", username)
          .eq("success", False)
          .gte("attempted_at", cutoff)
          .order("attempted_at", desc=False)
          .limit(1)
          .execute()
    )
    if oldest.data:
        try:
            ts         = oldest.data[0]["attempted_at"].replace("Z", "+00:00")
            unlock_dt  = datetime.fromisoformat(ts) + timedelta(minutes=LOCKOUT_MINUTES)
            remaining  = max(0, int((unlock_dt - datetime.now(timezone.utc)).total_seconds() / 60))
            return True, remaining
        except (ValueError, KeyError, TypeError):
            # An unexpected timestamp format must not turn a lockout into a
            # 500; fall back to the full window.
            log_event(logging.WARNING, "db.timestamp_parse_failed", table="login_attempts")
            return True, LOCKOUT_MINUTES

    return True, LOCKOUT_MINUTES


@resilient("count_recent_failures")
def count_recent_failures(username: str) -> int:
    sb   = get_supabase()
    resp = (
        sb.table("login_attempts")
          .select("id", count="exact")
          .eq("username", username)
          .eq("success", False)
          .gte("attempted_at", _ago(minutes=LOCKOUT_MINUTES))
          .execute()
    )
    return _count(resp)


# -----------------------------------------------
# AUDIT LOG
# -----------------------------------------------

@resilient("log_analysis")
def log_analysis(username: str, input_length: int, input_mode: str,
                 model_used: str, verdict: str, confidence: float):
    sb = get_supabase()
    sb.table("audit_log").insert({
        "username":     username,
        "input_length": input_length,
        "input_mode":   input_mode,
        "model_used":   model_used,
        "verdict":      verdict,
        "confidence":   round(confidence, 4),
        "analyzed_at":  _now(),
    }).execute()


@resilient("get_user_history")
def get_user_history(username: str, limit: int = 10) -> list:
    sb   = get_supabase()
    resp = (
        sb.table("audit_log")
          .select("verdict, confidence, model_used, input_mode, analyzed_at")
          .eq("username", username)
          .order("analyzed_at", desc=True)
          .limit(limit)
          .execute()
    )
    return resp.data or []


@resilient("get_recent_analytics")
def get_recent_analytics(limit: int = 500) -> list:
    """Rows backing the admin analytics dashboard.

    Extracted from the route handler, which previously built this query inline.
    """
    sb   = get_supabase()
    resp = (
        sb.table("audit_log")
          .select("verdict, confidence, model_used, input_mode, analyzed_at, username")
          .order("analyzed_at", desc=True)
          .limit(limit)
          .execute()
    )
    return resp.data or []


@resilient("count_users")
def count_users() -> int:
    sb   = get_supabase()
    resp = sb.table("users").select("username", count="exact").execute()
    return _count(resp)


# -----------------------------------------------
# RATE LIMITING
# -----------------------------------------------

@resilient("check_rate_limit")
def check_rate_limit(username: str) -> tuple:
    """Returns (allowed: bool, used_count: int)."""
    sb   = get_supabase()
    resp = (
        sb.table("rate_limit")
          .select("id", count="exact")
          .eq("username", username)
          .eq("action", "analyze")
          .gte("occurred_at", _ago(hours=1))
          .execute()
    )
    count = _count(resp)
    return (count < MAX_ANALYSES_PER_HOUR, count)


@resilient("record_rate_event")
def record_rate_event(username: str):
    sb = get_supabase()
    sb.table("rate_limit").insert({
        "username":    username,
        "action":      "analyze",
        "occurred_at": _now(),
    }).execute()


# -----------------------------------------------
# INTERNAL HELPERS
# -----------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(minutes: int = 0, hours: int = 0) -> str:
    delta = timedelta(minutes=minutes, hours=hours)
    return (datetime.now(timezone.utc) - delta).isoformat()


def _count(resp) -> int:
    """Safely extract row count from Supabase response."""
    if resp.count is not None:
        return resp.count
    return len(resp.data) if resp.data else 0


# ═══════════════════════════════════════════════════════════════════
# ASYNC WRAPPERS
# ═══════════════════════════════════════════════════════════════════
# supabase-py is synchronous: it performs blocking network I/O. Calling these
# functions directly from an `async def` route handler blocks the single
# uvicorn event loop for the duration of the call, which means one slow
# Supabase request stalls EVERY concurrent request in the process — health
# checks, other users' analyses, everything.
#
# /api/auth/login alone makes up to four sequential database calls, each with
# an 8 second timeout, so a degraded database could freeze the whole worker
# for half a minute.
#
# These wrappers push the blocking call onto a worker thread. The synchronous
# functions above are unchanged and remain the single place the queries live,
# so the circuit breaker, timeouts and logging all still apply.

async def aget_user(username: str):
    return await asyncio.to_thread(get_user, username)


async def acreate_user(username: str, password_hash: bytes):
    return await asyncio.to_thread(create_user, username, password_hash)


async def arecord_login_attempt(username: str, success: bool):
    return await asyncio.to_thread(record_login_attempt, username, success)


async def ais_locked_out(username: str) -> tuple:
    return await asyncio.to_thread(is_locked_out, username)


async def acount_recent_failures(username: str) -> int:
    return await asyncio.to_thread(count_recent_failures, username)


async def alog_analysis(**kwargs):
    return await asyncio.to_thread(functools.partial(log_analysis, **kwargs))


async def aget_user_history(username: str, limit: int = 10) -> list:
    return await asyncio.to_thread(get_user_history, username, limit)


async def aget_recent_analytics(limit: int = 500) -> list:
    return await asyncio.to_thread(get_recent_analytics, limit)


async def acount_users() -> int:
    return await asyncio.to_thread(count_users)


async def acheck_rate_limit(username: str) -> tuple:
    return await asyncio.to_thread(check_rate_limit, username)


async def arecord_rate_event(username: str):
    return await asyncio.to_thread(record_rate_event, username)


async def ahealth_check() -> dict:
    return await asyncio.to_thread(health_check)
