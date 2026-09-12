"""
core/security.py — tokens, authorisation, rate limiting, security headers.
==========================================================================
Controls implemented here (FYP Ch.4 "Security Implementation"):

+---------------------------+--------------------------------------------------+
| Control                   | What it addresses                                |
+---------------------------+--------------------------------------------------+
| Fail-fast signing key     | JWT_SECRET previously fell back to a literal      |
|                           | published in a public repo — anyone could forge   |
|                           | an admin token. Enforced in core.config.          |
| Short-lived access tokens | Was 24h with no revocation. Now 2h + refresh.     |
| jti + revocation list     | /api/auth/logout was a no-op returning a string;  |
|                           | the token stayed valid for the rest of its life.  |
| Role-based authorisation  | `role` was carried in the token and never checked.|
|                           | /api/analytics exposed every user's scan data.    |
| Per-IP rate limiting      | Login had no IP throttle, so username rotation    |
|                           | was unlimited (enumeration) while 5 requests      |
|                           | locked any known account for 15 minutes (DoS).    |
| Security headers          | No CSP, nosniff, frame-ancestors or Referrer-     |
|                           | Policy were set; three ZAP warnings were simply   |
|                           | suppressed in .zap/rules.tsv instead of fixed.    |
+---------------------------+--------------------------------------------------+

Known limitation, stated honestly: the revocation list is in-process. A
container restart clears it, so a revoked token could be reused until it
expires (max 2h). A Supabase-backed store is provided as an optional upgrade
in docs/supabase_schema.sql (`revoked_tokens`); it is not required for the
system to run, so a missing table degrades to in-memory rather than breaking
login.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections import OrderedDict, deque
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.observability import log_event

# Accepts IPv4 and IPv6 shapes only. Length-bounded so an oversized header
# value cannot itself become the memory pressure.
_IP_SHAPED = re.compile(r"^[0-9a-fA-F:.]{3,45}$")

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


# ══════════════════════════════════════════════════════════════
# TOKEN ISSUING / VERIFICATION
# ══════════════════════════════════════════════════════════════

def _encode(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(username: str, role: str = "user") -> tuple[str, str]:
    """Return ``(token, jti)``. Short-lived; carries the authorisation role."""
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    token = _encode(
        {
            "sub": username,
            "role": role,
            "jti": jti,
            "typ": TOKEN_TYPE_ACCESS,
            "iat": now,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES),
        }
    )
    return token, jti


def create_refresh_token(username: str, role: str = "user") -> tuple[str, str]:
    """Return ``(token, jti)``. Long-lived; may only be exchanged, never used
    to authorise a normal request — enforced by the ``typ`` claim check."""
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    token = _encode(
        {
            "sub": username,
            "role": role,
            "jti": jti,
            "typ": TOKEN_TYPE_REFRESH,
            "iat": now,
            "exp": now + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS),
        }
    )
    return token, jti


def decode_token(token: str, *, expected_type: str = TOKEN_TYPE_ACCESS) -> dict:
    """Decode and fully validate a token.

    Checks signature, expiry, token type and revocation. A refresh token
    presented as a bearer credential is rejected: without the ``typ`` check a
    7-day refresh token would authorise ordinary API calls for a week.
    """
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if claims.get("typ") != expected_type:
        raise HTTPException(status_code=401, detail="Invalid token type")

    jti = claims.get("jti")
    if jti and is_revoked(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    return claims


# ══════════════════════════════════════════════════════════════
# REVOCATION (logout actually logs out)
# ══════════════════════════════════════════════════════════════

_revoked: dict[str, float] = {}


def revoke(jti: str, *, ttl_seconds: int | None = None) -> None:
    """Mark a token id as revoked until it would have expired anyway."""
    if not jti:
        return
    ttl = ttl_seconds if ttl_seconds is not None else settings.JWT_REFRESH_EXPIRE_DAYS * 86400
    _revoked[jti] = time.time() + ttl
    _prune_revoked()


def is_revoked(jti: str) -> bool:
    expiry = _revoked.get(jti)
    if expiry is None:
        return False
    if expiry < time.time():
        _revoked.pop(jti, None)
        return False
    return True


def _prune_revoked() -> None:
    """Drop entries that have outlived the token they revoked.

    Without this the dict grows without bound — the same defect the original
    ``_analysis_locks`` had.
    """
    if len(_revoked) < 512:
        return
    now = time.time()
    for jti in [k for k, exp in _revoked.items() if exp < now]:
        _revoked.pop(jti, None)


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION / AUTHORISATION DEPENDENCIES
# ══════════════════════════════════════════════════════════════

async def get_current_user(request: Request) -> dict:
    """Resolve the caller from the Authorization header, or raise 401."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing auth token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(header[7:].strip())


def require_role(*allowed_roles: str):
    """Dependency factory enforcing role membership.

    ``/api/analytics`` aggregates every user's scan history and returns a
    username leaderboard. It was reachable by any authenticated account.
    """

    async def _guard(user: dict = Depends(get_current_user)) -> dict:
        role = user.get("role", "user")
        if role not in allowed_roles:
            log_event(
                logging.WARNING,
                "authz.denied",
                username=user.get("sub"),
                role=role,
                required=list(allowed_roles),
            )
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        return user

    return _guard


# ══════════════════════════════════════════════════════════════
# RATE LIMITING
# ══════════════════════════════════════════════════════════════

def client_ip(request: Request) -> str:
    """Best-effort client address.

    The backend runs behind the Hugging Face Space proxy, so the socket peer is
    always the proxy and ``X-Forwarded-For`` must be consulted. That header is
    client-controlled and therefore spoofable; this limiter is a speed bump
    against naive automation, not a defence against a determined attacker with
    a proxy pool. The per-account lockout in the database is the control that
    actually protects a specific account.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        candidate = forwarded.split(",")[0].strip()
        # The header is client-controlled, so its VALUE cannot be trusted — but
        # its SHAPE must still be constrained. Without this, an attacker sending
        # a fresh arbitrary value per request creates one limiter key per
        # request, growing the tracking dict without bound and turning a
        # throttle into a memory-exhaustion vector.
        if _IP_SHAPED.match(candidate):
            return candidate
        return "malformed-xff"
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """In-process sliding-window limiter keyed by an arbitrary string."""

    # Hard ceiling on tracked keys. Reached only under attack; a legitimate
    # deployment sees far fewer distinct clients per window.
    MAX_KEYS = 4096

    def __init__(self, limit: int, window_seconds: int, name: str = "limiter"):
        self.limit = limit
        self.window = window_seconds
        self.name = name
        # OrderedDict gives LRU eviction; a plain dict could only drop stale
        # entries, which is useless when an attacker keeps every key fresh.
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def check(self, key: str) -> tuple[bool, int]:
        """Record a hit. Returns ``(allowed, retry_after_seconds)``."""
        now = time.monotonic()
        bucket = self._hits.get(key)
        if bucket is None:
            bucket = deque()
            self._hits[key] = bucket
        self._hits.move_to_end(key)
        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.limit:
            retry_after = int(bucket[0] + self.window - now) + 1
            return False, max(retry_after, 1)

        bucket.append(now)
        self._prune(cutoff)
        return True, 0

    def _prune(self, cutoff: float) -> None:
        """Bound the keyspace.

        First drop entries whose window has fully elapsed. If the table is
        still at the ceiling — which happens when an attacker rotates the key
        fast enough that every entry is fresh — evict least-recently-used
        entries until it fits. Bounded memory matters more here than perfect
        accounting for an attacker who is already being throttled.
        """
        if len(self._hits) < self.MAX_KEYS:
            return
        for key in [k for k, v in list(self._hits.items()) if not v or v[-1] < cutoff]:
            self._hits.pop(key, None)
        while len(self._hits) >= self.MAX_KEYS:
            self._hits.popitem(last=False)

    def reset(self) -> None:
        self._hits.clear()


login_limiter = SlidingWindowLimiter(
    settings.LOGIN_RATE_LIMIT_PER_IP, settings.LOGIN_RATE_WINDOW_SECONDS, "login"
)
register_limiter = SlidingWindowLimiter(
    settings.REGISTER_RATE_LIMIT_PER_IP, settings.REGISTER_RATE_WINDOW_SECONDS, "register"
)


def enforce_limit(limiter: SlidingWindowLimiter, request: Request) -> None:
    """Raise 429 when the caller's IP has exceeded the window."""
    allowed, retry_after = limiter.check(client_ip(request))
    if not allowed:
        log_event(logging.WARNING, "ratelimit.blocked", limiter=limiter.name, path=request.url.path)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait before trying again.",
            headers={"Retry-After": str(retry_after)},
        )


# ══════════════════════════════════════════════════════════════
# SECURITY HEADERS
# ══════════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach defensive response headers to every response.

    The API serves JSON rather than HTML, so the CSP is maximally strict:
    nothing may be loaded or framed. This is what makes the header meaningful
    on the ``/docs`` route and on any error page a browser might render.
    """

    def __init__(self, app, *, hsts: bool = False):
        super().__init__(app)
        self.hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), camera=(), microphone=(), payment=()"
        )
        response.headers.setdefault("Cache-Control", "no-store")
        if self.hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
