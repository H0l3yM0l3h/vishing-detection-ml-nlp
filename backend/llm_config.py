"""
llm_config.py — Ollama LLM configuration for ShieldGuard Phase 2
=================================================================
Provides a LangChain-compatible LLM backed by a local Ollama server.

Default model: llama3.2:3b  (lightweight, ~2GB, runs on any machine)
"""

import requests
from langchain_ollama import OllamaLLM

OLLAMA_BASE_URL = "http://localhost:11434"

# ── Model presets ────────────────────────────────
MODEL_PRESETS = {
    "llama3.2:3b":  {"num_ctx": 4096,  "temperature": 0.1},
    "qwen2.5:32b":  {"num_ctx": 4096,  "temperature": 0.1},
    "llama3.3:70b": {"num_ctx": 4096,  "temperature": 0.1},
}

DEFAULT_MODEL = "llama3.2:3b"


def check_ollama_available() -> bool:
    """Ping the Ollama server. Returns True if reachable."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def get_available_models() -> list[str]:
    """Return list of model names currently pulled in Ollama."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def get_llm(model: str = DEFAULT_MODEL):
    """
    Return a LangChain-compatible Ollama LLM instance.

    Parameters
    ----------
    model : str
        Ollama model tag (e.g. 'llama3.2:3b').

    Returns
    -------
    Ollama LLM instance, or None if Ollama is unreachable.
    """
    if not check_ollama_available():
        return None

    preset = MODEL_PRESETS.get(model, {"num_ctx": 4096, "temperature": 0.1})

    return OllamaLLM(
        model=model,
        base_url=OLLAMA_BASE_URL,
        temperature=preset["temperature"],
        num_ctx=preset["num_ctx"],
    )
