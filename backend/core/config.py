"""
core/config.py — centralised, validated application settings.
=============================================================
Every environment variable the backend reads is declared here, in one place,
with explicit validation. Previously settings were scattered across main.py,
database.py, llm_config.py and penipu_client.py, and one of them (JWT_SECRET)
silently fell back to a publicly-known default.

Security note (FYP Ch.4):
    JWT_SECRET has NO fallback. If it is missing or left at a known default,
    the application refuses to start. A signing key that falls back to a
    literal published in a public repository is equivalent to no
    authentication at all — anyone can mint an admin token.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")


class ConfigError(RuntimeError):
    """Raised at import time when configuration is missing or unsafe."""


# Values that must never be accepted as a real signing key.
_FORBIDDEN_JWT_SECRETS = {
    "",
    "change-me-in-production",
    "changeme",
    "secret",
    "test",
    "dev",
}

_MIN_JWT_SECRET_LEN = 32


def _split_csv(raw: str) -> list[str]:
    """Split a comma-separated env var, trimming whitespace and dropping blanks.

    The previous CORS parsing did a bare ``.split(",")`` with no ``.strip()``,
    so ``"a.com, b.com"`` silently produced the origin ``" b.com"``, which
    never matches and is invisible in logs.
    """
    return [part.strip() for part in raw.split(",") if part.strip()]


class Settings:
    """Validated application settings. Instantiated once as ``settings``."""

    def __init__(self) -> None:
        # ── Environment ───────────────────────────────────────────
        self.ENV: str = os.environ.get("APP_ENV", "development").strip().lower()
        self.IS_PRODUCTION: bool = self.ENV == "production"
        self.IS_TESTING: bool = self.ENV == "test"

        # ── JWT (fail-fast; no insecure fallback) ────────────────
        self.JWT_SECRET: str = os.environ.get("JWT_SECRET", "").strip()
        self.JWT_ALGORITHM: str = "HS256"
        self.JWT_ACCESS_EXPIRE_MINUTES: int = _int_env("JWT_ACCESS_EXPIRE_MINUTES", 120)
        self.JWT_REFRESH_EXPIRE_DAYS: int = _int_env("JWT_REFRESH_EXPIRE_DAYS", 7)

        # ── Supabase ─────────────────────────────────────────────
        self.SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").strip()
        self.SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "").strip()
        self.SUPABASE_TIMEOUT_SECONDS: float = _float_env("SUPABASE_TIMEOUT_SECONDS", 8.0)
        # Circuit breaker: after N consecutive failures, fail fast for M seconds
        # instead of making every request wait for the full timeout.
        self.DB_BREAKER_THRESHOLD: int = _int_env("DB_BREAKER_THRESHOLD", 3)
        self.DB_BREAKER_COOLDOWN_SECONDS: float = _float_env("DB_BREAKER_COOLDOWN_SECONDS", 30.0)

        # ── Third-party APIs (optional; absence degrades gracefully) ──
        self.GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "").strip()
        self.GROQ_TIMEOUT_SECONDS: float = _float_env("GROQ_TIMEOUT_SECONDS", 45.0)
        self.PENIPU_API_KEY: str = os.environ.get("PENIPU_API_KEY", "").strip()

        # ── Paths ────────────────────────────────────────────────
        models_dir = Path(os.environ.get("MODELS_DIR", "../models"))
        if not models_dir.is_absolute():
            models_dir = (_BACKEND_DIR / models_dir).resolve()
        self.MODELS_DIR: Path = models_dir

        # ── CORS ─────────────────────────────────────────────────
        self.CORS_ORIGINS: list[str] = _split_csv(
            os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        )

        # ── Limits ───────────────────────────────────────────────
        self.MAX_UPLOAD_BYTES: int = _int_env("MAX_UPLOAD_MB", 25) * 1024 * 1024
        self.LOGIN_RATE_LIMIT_PER_IP: int = _int_env("LOGIN_RATE_LIMIT_PER_IP", 10)
        self.LOGIN_RATE_WINDOW_SECONDS: int = _int_env("LOGIN_RATE_WINDOW_SECONDS", 300)
        self.REGISTER_RATE_LIMIT_PER_IP: int = _int_env("REGISTER_RATE_LIMIT_PER_IP", 5)
        self.REGISTER_RATE_WINDOW_SECONDS: int = _int_env("REGISTER_RATE_WINDOW_SECONDS", 3600)

        # ── API docs exposure ────────────────────────────────────
        # Interactive docs enumerate every endpoint and schema. Useful in
        # development, unnecessary attack surface in production.
        self.EXPOSE_DOCS: bool = _bool_env("EXPOSE_DOCS", default=not self.IS_PRODUCTION)

        self._validate()

    # ------------------------------------------------------------------
    def _validate(self) -> None:
        problems: list[str] = []

        if self.JWT_SECRET.lower() in _FORBIDDEN_JWT_SECRETS:
            problems.append(
                "JWT_SECRET is missing or set to a known placeholder. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        elif len(self.JWT_SECRET) < _MIN_JWT_SECRET_LEN:
            problems.append(
                f"JWT_SECRET is only {len(self.JWT_SECRET)} characters; "
                f"at least {_MIN_JWT_SECRET_LEN} are required."
            )

        if not self.SUPABASE_URL:
            problems.append("SUPABASE_URL is not set.")
        if not self.SUPABASE_KEY:
            problems.append("SUPABASE_KEY is not set.")

        if not self.CORS_ORIGINS:
            problems.append("CORS_ORIGINS resolved to an empty list.")

        if problems:
            raise ConfigError(
                "ShieldGuard cannot start — configuration problems:\n  - "
                + "\n  - ".join(problems)
                + "\n\nSee backend/.env.example for the full list of required variables."
            )

    # ------------------------------------------------------------------
    @property
    def supabase_key_role(self) -> str:
        """Best-effort read of the Supabase key's role claim ('anon' / 'service_role').

        Used by the health endpoint to warn when the backend is running with an
        ``anon`` key against RLS-protected tables — a configuration that makes
        SELECTs silently return empty and INSERTs raise.
        Never returns the key itself.
        """
        import base64
        import json

        try:
            payload_b64 = self.SUPABASE_KEY.split(".")[1]
            payload_b64 += "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return str(payload.get("role", "unknown"))
        except Exception:
            return "unknown"

    def redacted(self) -> dict:
        """Settings snapshot safe to log or expose to an admin — no secret values."""
        return {
            "env": self.ENV,
            "cors_origins": self.CORS_ORIGINS,
            "models_dir": str(self.MODELS_DIR),
            "supabase_url": self.SUPABASE_URL,
            "supabase_key_role": self.supabase_key_role,
            "groq_configured": bool(self.GROQ_API_KEY),
            "penipu_configured": bool(self.PENIPU_API_KEY),
            "access_token_minutes": self.JWT_ACCESS_EXPIRE_MINUTES,
            "refresh_token_days": self.JWT_REFRESH_EXPIRE_DAYS,
            "max_upload_mb": self.MAX_UPLOAD_BYTES // (1024 * 1024),
            "docs_exposed": self.EXPOSE_DOCS,
        }


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def generate_secret() -> str:
    """Helper for operators: print a strong JWT secret."""
    return secrets.token_urlsafe(48)


settings = Settings()
