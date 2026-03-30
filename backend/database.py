"""
database.py — Supabase backend for ShieldGuard (FastAPI version)
================================================================
Uses environment variables instead of st.secrets.
All Supabase queries are IDENTICAL to the Streamlit version.
"""

import os
import functools
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

MAX_ATTEMPTS          = 5
LOCKOUT_MINUTES       = 15
MAX_ANALYSES_PER_HOUR = 30


# -----------------------------------------------
# CLIENT
# -----------------------------------------------

@functools.lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def init_db():
    """No-op — tables are created via supabase_schema.sql."""
    pass


# -----------------------------------------------
# USER MANAGEMENT
# -----------------------------------------------

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
        ts         = oldest.data[0]["attempted_at"].replace("Z", "+00:00")
        unlock_dt  = datetime.fromisoformat(ts) + timedelta(minutes=LOCKOUT_MINUTES)
        remaining  = max(0, int((unlock_dt - datetime.now(timezone.utc)).total_seconds() / 60))
        return True, remaining

    return True, LOCKOUT_MINUTES


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


# -----------------------------------------------
# RATE LIMITING
# -----------------------------------------------

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
