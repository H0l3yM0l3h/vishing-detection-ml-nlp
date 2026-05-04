"""
llm_config.py — Groq Cloud LLM configuration for ShieldGuard Phase 2
=====================================================================
Provides LLM inference via Groq API (cloud-hosted, ultra-fast).

Default model: llama-3.3-70b-versatile  (70B params, free tier)

[v3.4 — 2026-05-05] Migrated from local Ollama to Groq Cloud API.
  - 70B model replaces 3B → significantly smarter analysis
  - Sub-second inference latency via Groq LPU hardware
  - No local GPU or Ollama server required
"""

import os
from groq import Groq
from dotenv import load_dotenv
from pathlib import Path

# Load .env
load_dotenv(Path(__file__).resolve().parent / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# ── Model presets ────────────────────────────────
# max_tokens caps the max output tokens; shorter = faster response
MODEL_PRESETS = {
    "llama-3.3-70b-versatile":  {"max_tokens": 512, "temperature": 0.1},
    "llama-3.1-8b-instant":     {"max_tokens": 512, "temperature": 0.1},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"max_tokens": 512, "temperature": 0.1},
}

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# ── Lazy singleton ───────────────────────────────
_groq_client = None


def _get_groq_client() -> Groq | None:
    """Return a Groq client, or None if no API key is configured."""
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            return None
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def check_groq_available() -> bool:
    """Ping the Groq API. Returns True if reachable and authenticated."""
    try:
        client = _get_groq_client()
        if client is None:
            return False
        # Lightweight call to verify connectivity + auth
        client.models.list()
        return True
    except Exception:
        return False


# ── Legacy compatibility aliases ─────────────────
# These allow existing imports to work without changes elsewhere
def check_ollama_available() -> bool:
    """Legacy alias → now checks Groq API instead of Ollama."""
    return check_groq_available()


def get_available_models() -> list[str]:
    """Return list of available Groq model IDs."""
    try:
        client = _get_groq_client()
        if client is None:
            return []
        models = client.models.list()
        return [m.id for m in models.data]
    except Exception:
        return []


def get_llm(model: str = DEFAULT_MODEL):
    """
    Return the Groq client for direct usage.

    Parameters
    ----------
    model : str
        Groq model ID (e.g. 'llama-3.3-70b-versatile').

    Returns
    -------
    Groq client instance, or None if API key is missing.
    """
    return _get_groq_client()
