"""
Shared pytest fixtures for the ShieldGuard test suite.
======================================================
Design goal: the security tests must run anywhere — a laptop with no network,
a CI runner with no secrets, a marker's machine — and must never touch the
production Supabase project.

Two things make that possible:

1. Environment defaults are injected before `main` is imported, so
   `core.config.Settings` validates successfully without real credentials.
2. The database layer is replaced with an in-memory fake. Every function in
   `backend/database.py` that the API calls has a stub here with the same
   signature and return shape, so the routes exercise their real logic while
   the storage underneath is deterministic.

The fake deliberately mirrors the real schema (`users`, `login_attempts`) so
a change to the production queries that breaks the contract shows up here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for path in (str(_ROOT), str(_BACKEND)):
    if path not in sys.path:
        sys.path.insert(0, path)


# ── Environment must be set before backend modules import ──────────────────
# core.config validates at import time and refuses to start on an unsafe
# configuration, which is the behaviour we want in production and which the
# test suite therefore has to satisfy honestly.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "JWT_SECRET",
    "test-only-secret-not-used-anywhere-real-0123456789abcdef",
)
os.environ.setdefault("SUPABASE_URL", "https://test.invalid")
os.environ.setdefault("SUPABASE_KEY", "test-key-not-real")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("PENIPU_API_KEY", "")


TEST_USER = "test_user"
TEST_PASSWORD = "TestPassw0rd!2026"
ADMIN_USER = "test_admin"


@pytest.fixture(scope="session")
def bcrypt_hash():
    from auth import hash_password

    return hash_password(TEST_PASSWORD)


class FakeDatabase:
    """In-memory stand-in for backend/database.py.

    The methods are async because main.py imports the `a*` async wrappers from
    database.py (which offload the blocking Supabase client to a thread). The
    fake matches that contract, so the tests exercise the same await points the
    production routes do.

    Mirrors the real table shapes so a contract change is visible here.
    """

    def __init__(self, password_hash: bytes):
        self.users = {
            TEST_USER: {
                "username": TEST_USER,
                "password_hash": password_hash.decode(),
                "role": "user",
                "last_login": None,
            },
            ADMIN_USER: {
                "username": ADMIN_USER,
                "password_hash": password_hash.decode(),
                "role": "admin",
                "last_login": None,
            },
        }
        self.login_attempts: list[dict] = []
        self.audit_log: list[dict] = []
        self.rate_events: list[str] = []
        self.fail_next = False          # force a DatabaseUnavailable

    # -- helpers the routes call -------------------------------------------
    def _maybe_fail(self):
        if self.fail_next:
            from core.observability import DatabaseUnavailable

            raise DatabaseUnavailable("Database is temporarily unreachable.", cause="test")

    async def get_user(self, username):
        self._maybe_fail()
        return self.users.get(username)

    async def create_user(self, username, password_hash):
        self._maybe_fail()
        if username in self.users:
            raise ValueError("duplicate")
        self.users[username] = {
            "username": username,
            "password_hash": password_hash.decode(),
            "role": "user",
            "last_login": None,
        }

    async def record_login_attempt(self, username, success):
        self._maybe_fail()
        self.login_attempts.append({"username": username, "success": success})

    async def is_locked_out(self, username):
        self._maybe_fail()
        failures = [a for a in self.login_attempts if a["username"] == username and not a["success"]]
        return (len(failures) >= 5, 15 if len(failures) >= 5 else 0)

    async def count_recent_failures(self, username):
        self._maybe_fail()
        return len([a for a in self.login_attempts if a["username"] == username and not a["success"]])

    async def log_analysis(self, **kwargs):
        self._maybe_fail()
        self.audit_log.append(kwargs)

    async def get_user_history(self, username, limit=10):
        self._maybe_fail()
        return [r for r in self.audit_log if r.get("username") == username][:limit]

    async def get_recent_analytics(self, limit=500):
        self._maybe_fail()
        return self.audit_log[:limit]

    async def count_users(self):
        self._maybe_fail()
        return len(self.users)

    async def check_rate_limit(self, username):
        self._maybe_fail()
        used = len([e for e in self.rate_events if e == username])
        return (used < 30, used)

    async def record_rate_event(self, username):
        self._maybe_fail()
        self.rate_events.append(username)

    async def health_check(self):
        return {"ok": True, "latency_ms": 1.0, "detail": "fake", "breaker": "closed", "key_role": "test"}


@pytest.fixture
def fake_db(bcrypt_hash, monkeypatch):
    """Install the fake database into both main and database modules."""
    import database as database_module
    import main as main_module

    db = FakeDatabase(bcrypt_hash)

    for name in (
        "get_user", "create_user", "record_login_attempt", "is_locked_out",
        "count_recent_failures", "log_analysis", "get_user_history",
        "get_recent_analytics", "count_users", "check_rate_limit",
        "record_rate_event",
    ):
        monkeypatch.setattr(main_module, name, getattr(db, name), raising=False)
        monkeypatch.setattr(database_module, name, getattr(db, name), raising=False)

    monkeypatch.setattr(main_module, "db_health_check", db.health_check, raising=False)
    return db


@pytest.fixture
def client(fake_db, monkeypatch):
    """FastAPI TestClient with models stubbed and rate limiters reset.

    The ML model is not loaded: these tests assert security behaviour, not
    classification quality, and loading a 2 MB pickle per test is wasteful.
    """
    from fastapi.testclient import TestClient
    import main as main_module
    from core import security as security_module

    # Each test starts from a clean limiter and revocation state, otherwise
    # ordering between tests changes results.
    security_module.login_limiter.reset()
    security_module.register_limiter.reset()
    security_module._revoked.clear()

    app = main_module.app

    # Provide the state the routes read, without running the real lifespan
    # (which loads a 2 MB model and builds a ChromaDB index).
    app.state.models = {"SVM": object()}
    app.state.nn_model = None
    app.state.vectorizer = None
    app.state.chroma_count = 0
    app.state.groq_available = False

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    """Bearer header for a normal (non-admin) account."""
    res = client.post("/api/auth/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.fixture
def admin_headers(client):
    """Bearer header for an admin account."""
    res = client.post("/api/auth/login", json={"username": ADMIN_USER, "password": TEST_PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}
