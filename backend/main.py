"""
main.py — FastAPI backend for ShieldGuard
==========================================
Exposes all ShieldGuard intelligence via REST endpoints.
Core logic is imported unchanged from the copied modules.
"""

import os
import sys
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

# ── Ensure backend/ is on sys.path (allows running from any CWD) ──
_BACKEND_DIR = str(Path(__file__).resolve().parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from jose import jwt, JWTError
from dotenv import load_dotenv

# ── Load .env before anything else ───────────────
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Ensure ffmpeg is on PATH ─────────────────────
_ffmpeg_bin = r"D:\ffmpeg\ffmpeg-8.1-essentials_build\bin"
if os.path.isdir(_ffmpeg_bin) and _ffmpeg_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")
    try:
        from pydub import AudioSegment
        AudioSegment.converter = os.path.join(_ffmpeg_bin, "ffmpeg.exe")
        AudioSegment.ffprobe   = os.path.join(_ffmpeg_bin, "ffprobe.exe")
    except ImportError:
        pass

# ── Local imports ────────────────────────────────
from models_loader import load_all_models, load_whisper
from inference import (
    run_inference, get_explanation, detect_suspicious_phrases,
    build_highlighted_transcript, insufficient_evidence,
    SAMPLE_VISHING, SAMPLE_SAFE,
)
from hybrid_engine import run_hybrid_analysis
from rag_module import ensure_scam_library
from llm_config import check_ollama_available
from auth import (
    validate_password, validate_username, sanitize_input,
    hash_password, verify_password,
)
from database import (
    init_db, get_user, create_user,
    record_login_attempt, is_locked_out, count_recent_failures,
    log_analysis, get_user_history,
    check_rate_limit, record_rate_event,
    MAX_ATTEMPTS, LOCKOUT_MINUTES, MAX_ANALYSES_PER_HOUR,
)


# ═══════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════
JWT_SECRET    = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_H  = 24
MODELS_DIR    = Path(os.environ.get("MODELS_DIR", "../models"))
if not MODELS_DIR.is_absolute():
    MODELS_DIR = (Path(__file__).resolve().parent / MODELS_DIR).resolve()
CORS_ORIGINS  = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


# ═══════════════════════════════════════════════
# LIFESPAN — load models on startup
# ═══════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[ShieldGuard] Loading ML models...")
    vectorizer, ml_models, nn_model = load_all_models(MODELS_DIR)
    app.state.vectorizer = vectorizer
    app.state.models     = ml_models
    app.state.nn_model   = nn_model
    print(f"[ShieldGuard] Loaded {len(ml_models)} classical models + 1 neural network")

    print("[ShieldGuard] Initializing ChromaDB scam library...")
    count = ensure_scam_library()
    app.state.chroma_count = count
    print(f"[ShieldGuard] ChromaDB: {count} entries indexed")

    ollama_ok = check_ollama_available()
    app.state.ollama_available = ollama_ok
    print(f"[ShieldGuard] Ollama: {'Available' if ollama_ok else 'Not reachable'}")

    app.state.whisper_model = None  # lazy-loaded on first transcription

    print("[ShieldGuard] Backend ready!")
    yield
    print("[ShieldGuard] Shutting down.")


# ═══════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════
app = FastAPI(
    title="ShieldGuard API",
    description="Hybrid ML + LLM vishing detection backend",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════
# JWT HELPERS
# ═══════════════════════════════════════════════
def _create_token(username: str, role: str = "user") -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")
    return _decode_token(auth[7:])


# ═══════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class AnalyzeRequest(BaseModel):

# ═══════════════════════════════════════════════
# HEALTH CHECK (public — no auth required)
# ═══════════════════════════════════════════════
@app.get("/api/health")
async def health_check(request: Request):
    """Returns real-time status of all AI components."""
    state = request.app.state
    ml_models   = getattr(state, "models",    None)
    nn_model    = getattr(state, "nn_model",  None)
    chroma      = getattr(state, "chroma_count", 0)
    ollama_ok   = getattr(state, "ollama_available", False)
    whisper_ok  = getattr(state, "whisper_model", None) is not None

    ml_ok = bool(ml_models and len(ml_models) > 0)

    return {
        "status": "online" if ml_ok else "degraded",
        "components": {
            "ml_classifier":  {"ok": ml_ok,    "detail": f"{len(ml_models)} models" if ml_ok else "not loaded"},
            "neural_network": {"ok": bool(nn_model), "detail": "loaded" if nn_model else "not loaded"},
            "rag_chromadb":   {"ok": chroma > 0, "detail": f"{chroma} entries"},
            "llm_ollama":     {"ok": ollama_ok,  "detail": "reachable" if ollama_ok else "not reachable"},
            "whisper_stt":    {"ok": whisper_ok, "detail": "loaded" if whisper_ok else "lazy (loads on first use)"},
        },
        "model_count": len(ml_models) if ml_ok else 0,
        "version": "3.1",
    }


    transcript: str
    model_choice: str = "SVM"
    input_mode: str = "text"
    username: str = ""


# ═══════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    username = sanitize_input(req.username, 32).strip()

    # Check lockout
    locked, remaining = is_locked_out(username)
    if locked:
        return JSONResponse(status_code=423, content={
            "detail": f"Account locked. Try again in {remaining} minutes.",
            "locked": True,
            "minutes_remaining": remaining,
        })

    user = get_user(username)
    if not user or not verify_password(req.password, user["password_hash"]):
        record_login_attempt(username, False)
        failures = count_recent_failures(username)
        remaining_attempts = max(0, MAX_ATTEMPTS - failures)
        return JSONResponse(status_code=401, content={
            "detail": "Invalid username or password",
            "remaining_attempts": remaining_attempts,
        })

    record_login_attempt(username, True)
    token = _create_token(username, user.get("role", "user"))
    return {
        "token": token,
        "username": username,
        "role": user.get("role", "user"),
    }


@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    username = sanitize_input(req.username, 32)

    valid_u, reason_u = validate_username(username)
    if not valid_u:
        raise HTTPException(status_code=400, detail=reason_u)

    valid_p, reason_p = validate_password(req.password)
    if not valid_p:
        raise HTTPException(status_code=400, detail=reason_p)

    if get_user(username):
        raise HTTPException(status_code=409, detail="Username already taken")

    pw_hash = hash_password(req.password)
    try:
        create_user(username, pw_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)[:100]}")

    token = _create_token(username)
    return {
        "token": token,
        "username": username,
        "role": "user",
        "message": "Account created successfully",
    }


@app.post("/api/auth/logout")
async def logout():
    return {"message": "Logged out"}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"username": user["sub"], "role": user.get("role", "user")}


# ═══════════════════════════════════════════════
# ANALYSIS ENDPOINT
# ═══════════════════════════════════════════════
@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, request: Request, user: dict = Depends(get_current_user)):
    username = user["sub"]

    # Rate limit
    allowed, used = check_rate_limit(username)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({MAX_ANALYSES_PER_HOUR}/hour)")

    # Sanitize
    transcript = sanitize_input(req.transcript)
    model_choice = req.model_choice
    if model_choice not in ["SVM", "Logistic Regression", "Random Forest", "Neural Network"]:
        model_choice = "SVM"

    # Get models from app state
    models   = request.app.state.models
    nn_model = request.app.state.nn_model

    # ── STEP 1: ML Inference ──
    ml_label, ml_score = run_inference(transcript, model_choice, models, nn_model)

    # ── Evidence check ──
    insuf, insuf_reason = insufficient_evidence(transcript, ml_score)

    # ── Suspicious phrases ──
    phrases = detect_suspicious_phrases(transcript)
    highlighted = build_highlighted_transcript(transcript, phrases)

    # ── XAI ──
    top_keywords = get_explanation(model_choice, transcript, models)

    # ── Build ML-only result ──
    result = {
        "verdict": ml_label if not insuf else "INCONCLUSIVE",
        "confidence": round(ml_score, 4),
        "source": "ml_only",
        "ml_label": ml_label,
        "ml_model": model_choice,
        "insufficient_evidence": insuf,
        "insufficient_reason": insuf_reason if insuf else None,
        "suspicious_phrases": phrases,
        "highlighted_transcript": highlighted,
        "top_keywords": [[k, round(w, 4)] for k, w in top_keywords],
        "explanation": None,
        "scam_type": None,
        "tactics": [],
        "similar_cases": [],
        "action_steps": [],
        "divergence_flag": False,
    }

    # ── STEP 2: Hybrid Analysis (if ML score >= threshold) ──
    if not insuf:
        try:
            hybrid = run_hybrid_analysis(
                transcript=transcript,
                model_choice=model_choice,
                ml_label=ml_label,
                ml_score=ml_score,
                top_keywords=top_keywords,
                suspicious_phrases=phrases,
            )
            if hybrid.get("source") == "hybrid":
                result["verdict"]        = hybrid.get("verdict", ml_label)
                result["source"]         = "hybrid"
                result["explanation"]    = hybrid.get("explanation")
                result["scam_type"]      = hybrid.get("scam_type")
                result["tactics"]        = hybrid.get("tactic", [])
                result["similar_cases"]  = hybrid.get("similar_cases", [])
                result["action_steps"]   = hybrid.get("action_steps", [])
                result["divergence_flag"] = hybrid.get("divergence_flag", False)

                if result["divergence_flag"]:
                    result["verdict"] = "SUSPICIOUS — UNCONFIRMED"
        except Exception as e:
            print(f"[Analyze] Hybrid analysis error: {e}")
            # Fall back to ML-only — result already populated

    # ── Log to Supabase ──
    try:
        record_rate_event(username)
        log_analysis(
            username=username,
            input_length=len(transcript),
            input_mode=req.input_mode,
            model_used=model_choice,
            verdict=result["verdict"],
            confidence=result["confidence"],
        )
    except Exception as e:
        print(f"[Analyze] Audit log error: {e}")

    return result


# ═══════════════════════════════════════════════
# TRANSCRIBE ENDPOINT
# ═══════════════════════════════════════════════
@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    # Validate file type
    allowed = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}")

    # Check size (25MB)
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 25MB)")

    # Load whisper lazily
    if app.state.whisper_model is None:
        try:
            app.state.whisper_model = load_whisper()
        except Exception:
            raise HTTPException(status_code=500, detail="Whisper not installed")

    # Transcribe — exact same logic as streamlit_app.py
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content)
            tmp = f.name
        result = app.state.whisper_model.transcribe(tmp, fp16=False)
        return {"transcript": result["text"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)[:200]}")
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


# ═══════════════════════════════════════════════
# HISTORY ENDPOINT
# ═══════════════════════════════════════════════
@app.get("/api/history")
async def history(limit: int = 10, user: dict = Depends(get_current_user)):
    username = user["sub"]
    rows = get_user_history(username, limit=min(limit, 50))
    return {"history": rows}


# ═══════════════════════════════════════════════
# HEALTH ENDPOINT
# ═══════════════════════════════════════════════
@app.get("/api/health")
async def health(request: Request):
    ollama_ok = check_ollama_available()
    request.app.state.ollama_available = ollama_ok

    supabase_ok = True
    try:
        from database import get_supabase
        get_supabase()
    except Exception:
        supabase_ok = False

    return {
        "ml_models": hasattr(request.app.state, "models") and bool(request.app.state.models),
        "ollama": ollama_ok,
        "chromadb": getattr(request.app.state, "chroma_count", 0),
        "supabase": supabase_ok,
    }


# ═══════════════════════════════════════════════
# SAMPLES ENDPOINT (for frontend sample buttons)
# ═══════════════════════════════════════════════
@app.get("/api/samples")
async def samples():
    return {
        "vishing": SAMPLE_VISHING,
        "safe": SAMPLE_SAFE,
    }


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
