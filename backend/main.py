"""
main.py — FastAPI backend for ShieldGuard
==========================================
Exposes all ShieldGuard intelligence via REST endpoints.
Core logic is imported unchanged from the copied modules.

[v3.4 — 2026-05-05] LLM: Ollama → Groq API, Whisper: local → Groq API
"""

import os
import sys
import logging
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
from dotenv import load_dotenv

# ── Load .env before anything else ───────────────
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Ensure ffmpeg is available ─────────────────────
# On Windows (local dev), check specific path. On Linux (Docker), it's in system PATH.
_windows_ffmpeg = r"D:\ffmpeg\ffmpeg-8.1-essentials_build\bin"
if os.name == 'nt' and os.path.isdir(_windows_ffmpeg) and _windows_ffmpeg not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _windows_ffmpeg + os.pathsep + os.environ.get("PATH", "")

try:
    from pydub import AudioSegment
    if os.name == 'nt' and os.path.isdir(_windows_ffmpeg):
        AudioSegment.converter = os.path.join(_windows_ffmpeg, "ffmpeg.exe")
        AudioSegment.ffprobe   = os.path.join(_windows_ffmpeg, "ffprobe.exe")
except ImportError:
    pass

# ── Local imports ────────────────────────────────
from models_loader import load_all_models
from inference import (
    run_inference, run_inference_detailed, get_explanation, detect_suspicious_phrases,
    build_highlighted_transcript, insufficient_evidence,
    SAMPLE_VISHING, SAMPLE_SAFE,
)
from hybrid_engine import run_hybrid_analysis, VERDICT_SUSPICIOUS
from agents.prompt_guard import detect_injection
from rag_module import ensure_scam_library
from llm_config import check_groq_available, check_ollama_available, _get_groq_client
from auth import (
    validate_password, validate_username, sanitize_input,
    hash_password, verify_password,
)
from database import (
    init_db, get_user, create_user,
    record_login_attempt, is_locked_out, count_recent_failures,
    log_analysis, get_user_history, get_recent_analytics, count_users,
    check_rate_limit, record_rate_event,
    health_check as db_health_check,
    MAX_ATTEMPTS, LOCKOUT_MINUTES, MAX_ANALYSES_PER_HOUR,
)

# ── Core infrastructure (settings, logging, security) ─────────
from core.config import settings
from core.observability import (
    configure_logging, log_event, register_exception_handlers,
    RequestContextMiddleware,
)
from core.security import (
    create_access_token, create_refresh_token, decode_token, revoke,
    get_current_user, require_role, enforce_limit,
    login_limiter, register_limiter,
    SecurityHeadersMiddleware, TOKEN_TYPE_REFRESH,
)


# ═══════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════
# All settings now come from core.config, which validates them at import time
# and refuses to start on an unsafe configuration (notably: JWT_SECRET no
# longer falls back to a value published in this repository).
MODELS_DIR   = settings.MODELS_DIR
CORS_ORIGINS = settings.CORS_ORIGINS

configure_logging("INFO")


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
    print("[ShieldGuard] Loaded production SVM model")

    print("[ShieldGuard] Initializing ChromaDB scam library...")
    count = ensure_scam_library()
    app.state.chroma_count = count
    print(f"[ShieldGuard] ChromaDB: {count} entries indexed")

    groq_ok = check_groq_available()
    app.state.groq_available = groq_ok
    print(f"[ShieldGuard] Groq API: {'Available' if groq_ok else 'Not reachable — check GROQ_API_KEY'}")

    print("[ShieldGuard] Backend ready!")
    yield
    print("[ShieldGuard] Shutting down.")


# ═══════════════════════════════════════════════
# APP
# ═══════════════════════════════════════════════
app = FastAPI(
    title="ShieldGuard API",
    description="Hybrid ML + LLM vishing detection backend",
    version="4.0.0",
    lifespan=lifespan,
    # Interactive docs enumerate every endpoint, schema and example. Useful in
    # development; unnecessary reconnaissance surface in production.
    docs_url="/docs" if settings.EXPOSE_DOCS else None,
    redoc_url="/redoc" if settings.EXPOSE_DOCS else None,
    openapi_url="/openapi.json" if settings.EXPOSE_DOCS else None,
)

# ── Middleware ────────────────────────────────────────────────
# Starlette runs the LAST-added middleware outermost, so the effective order
# for an incoming request is: CORS → RequestContext → SecurityHeaders → route.
# CORS sits outermost so preflight requests are answered before anything else;
# RequestContext wraps the application so every outcome is logged with an ID.
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.IS_PRODUCTION)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

# Converts every unhandled exception into a logged JSON response carrying a
# request ID, and maps DatabaseUnavailable to 503 instead of a bare 500.
register_exception_handlers(app)


# ═══════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class AnalyzeRequest(BaseModel):
    transcript: str
    model_choice: str = "SVM"
    input_mode: str = "text"
    username: str = ""

# ═══════════════════════════════════════════════
# HEALTH CHECK (public — no auth required)
# ═══════════════════════════════════════════════
@app.get("/api/health_detailed")
async def health_check(request: Request):
    """Returns real-time status of all AI components."""
    state = request.app.state
    ml_models   = getattr(state, "models",    None)
    chroma      = getattr(state, "chroma_count", 0)
    groq_ok     = getattr(state, "groq_available", False)

    ml_ok = bool(ml_models and len(ml_models) > 0)
    db = db_health_check()

    components = {
        "ml_classifier":  {"ok": ml_ok,    "detail": "SVM v3 production model" if ml_ok else "not loaded"},
        "rag_chromadb":   {"ok": chroma > 0, "detail": f"{chroma} entries"},
        "llm_groq":       {"ok": groq_ok,   "detail": "reachable" if groq_ok else "not reachable"},
        "whisper_stt":    {"ok": groq_ok,    "detail": "Groq whisper-large-v3-turbo" if groq_ok else "requires Groq API"},
        # The datastore was absent from this map entirely, so the dashboard's
        # status indicator stayed green through a complete database outage.
        "database":       {"ok": db["ok"],  "detail": db["detail"], "latency_ms": db["latency_ms"]},
    }

    # ML is the only hard requirement — the system degrades to ML-only
    # analysis without Groq or RAG. A dead database blocks auth and audit, so
    # it counts toward overall status.
    if ml_ok and db["ok"]:
        status = "online"
    elif ml_ok:
        status = "degraded"
    else:
        status = "offline"

    return {
        "status": status,
        "components": components,
        "model_count": len(ml_models) if ml_ok else 0,
        "version": "4.0",
    }


# ═══════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════
@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    # Per-IP throttle. The per-account lockout below protects a *known*
    # account; without this, an attacker rotating usernames was unthrottled.
    enforce_limit(login_limiter, request)

    username = sanitize_input(req.username, 32).strip()

    # Registration validated the username format but login did not, so
    # arbitrary characters reached the PostgREST filter on this path only.
    valid_u, _ = validate_username(username)
    if not valid_u:
        log_event(logging.INFO, "auth.login_failed", reason="malformed_username")
        return JSONResponse(
            status_code=401, content={"detail": "Invalid username or password"}
        )

    # Check lockout
    locked, remaining = is_locked_out(username)
    if locked:
        log_event(logging.WARNING, "auth.login_locked", username=username)
        return JSONResponse(status_code=423, content={
            "detail": f"Account locked. Try again in {remaining} minutes.",
            "locked": True,
            "minutes_remaining": remaining,
        })

    user = get_user(username)
    if not user or not verify_password(req.password, user["password_hash"]):
        record_login_attempt(username, False)
        log_event(logging.WARNING, "auth.login_failed", reason="bad_credentials")
        # Deliberately uniform, and deliberately WITHOUT a remaining-attempts
        # count: telling an attacker how many tries are left hands them a
        # budget for staying just under the lockout threshold.
        return JSONResponse(status_code=401, content={
            "detail": "Invalid username or password",
        })

    record_login_attempt(username, True)
    role = user.get("role", "user")
    access_token, _ = create_access_token(username, role)
    refresh_token, _ = create_refresh_token(username, role)
    log_event(logging.INFO, "auth.login_success", username=username, role=role)
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        "username": username,
        "role": role,
    }


@app.post("/api/auth/register")
async def register(req: RegisterRequest, request: Request):
    enforce_limit(register_limiter, request)

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
    except HTTPException:
        raise
    except Exception as exc:
        # Never echo the driver's exception text to the client: it can carry
        # table names, constraint names and the upstream request URL.
        log_event(logging.ERROR, "auth.register_failed", error=repr(exc)[:300])
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")

    access_token, _ = create_access_token(username, "user")
    refresh_token, _ = create_refresh_token(username, "user")
    log_event(logging.INFO, "auth.register_success", username=username)
    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "expires_in": settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        "username": username,
        "role": "user",
        "message": "Account created successfully",
    }


@app.post("/api/auth/refresh")
async def refresh(req: RefreshRequest):
    """Exchange a refresh token for a new access token.

    The old refresh token is revoked on use (rotation), so a stolen refresh
    token is single-use and its reuse is detectable.
    """
    claims = decode_token(req.refresh_token, expected_type=TOKEN_TYPE_REFRESH)
    username = claims["sub"]
    role = claims.get("role", "user")

    revoke(claims.get("jti", ""))
    access_token, _ = create_access_token(username, role)
    new_refresh, _ = create_refresh_token(username, role)
    return {
        "token": access_token,
        "refresh_token": new_refresh,
        "expires_in": settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
        "username": username,
        "role": role,
    }


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Revoke the presented token.

    This endpoint previously returned a string and did nothing: the token
    remained valid for the rest of its 24-hour life, so "log out" on a shared
    machine offered no protection at all.
    """
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        try:
            claims = decode_token(header[7:].strip())
            revoke(claims.get("jti", ""))
            log_event(logging.INFO, "auth.logout", username=claims.get("sub"))
        except HTTPException:
            # Already invalid or expired — the desired end state either way.
            pass
    return {"message": "Logged out"}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"username": user["sub"], "role": user.get("role", "user")}


# ═══════════════════════════════════════════════
# ANALYSIS ENDPOINT
# ═══════════════════════════════════════════════
# Per-user lock: prevents multiple concurrent analyses from the same user.
# If the user clicks "Analyze" while one is already running, the second
# request is rejected immediately instead of queueing up Ollama calls.
import asyncio
_analysis_locks: dict[str, asyncio.Lock] = {}

# Cap on retained locks. The dict previously grew by one entry per distinct
# username and was never pruned; combined with open registration that is a
# slow memory-exhaustion path. Idle, unlocked entries are safe to discard —
# a fresh Lock is created on the user's next request.
_MAX_TRACKED_LOCKS = 512


def _get_analysis_lock(username: str) -> asyncio.Lock:
    """Return this user's lock, evicting idle ones when the table grows."""
    lock = _analysis_locks.get(username)
    if lock is None:
        if len(_analysis_locks) >= _MAX_TRACKED_LOCKS:
            for key in [k for k, v in list(_analysis_locks.items()) if not v.locked()]:
                _analysis_locks.pop(key, None)
            log_event(logging.INFO, "analyze.locks_pruned", retained=len(_analysis_locks))
        lock = asyncio.Lock()
        _analysis_locks[username] = lock
    return lock


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, request: Request, user: dict = Depends(get_current_user)):
    username = user["sub"]

    # ── Per-user concurrency guard ──
    lock = _get_analysis_lock(username)
    if lock.locked():
        raise HTTPException(status_code=429, detail="Analysis already in progress. Please wait.")

    async with lock:
        # Rate limit
        allowed, used = check_rate_limit(username)
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded ({MAX_ANALYSES_PER_HOUR}/hour)")

        # Sanitize
        transcript = sanitize_input(req.transcript)
        model_choice = "SVM"

        # Get models from app state
        models   = request.app.state.models
        nn_model = request.app.state.nn_model

        # ── STEP 1: ML Inference ──
        ml_detail = run_inference_detailed(transcript, model_choice, models, nn_model)
        ml_label = ml_detail["label"]
        ml_score = ml_detail["confidence"]
        vishing_probability = ml_detail["vishing_probability"]

        # ── Evidence check ──
        # Use the shared reject gate rather than re-implementing half of it.
        # This route previously applied only the word-count test inline, so the
        # asymmetric 0.80 reject threshold — the Chow (1970) reject-option rule
        # documented in inference.py and cited throughout the report — was
        # never actually applied on the live analysis path. It ran only in
        # /api/benchmark, which is why the benchmark and the scanner could
        # disagree on the same transcript.
        insuf, insuf_reason = insufficient_evidence(
            transcript, ml_score, label=ml_label
        )

        # ── Prompt-injection screening ──
        # A caller who addresses the analysis system rather than the victim is
        # attempting to manipulate the detector. Surface it as evidence rather
        # than stripping it: it is highly diagnostic of fraud.
        injection_findings = detect_injection(transcript)
        if injection_findings:
            log_event(
                logging.WARNING,
                "analyze.prompt_injection",
                username=username,
                types=sorted({f["type"] for f in injection_findings}),
            )

        # ── Suspicious phrases ──
        phrases = detect_suspicious_phrases(transcript)
        highlighted = build_highlighted_transcript(transcript, phrases)

        # ── XAI ──
        top_keywords = get_explanation(model_choice, transcript, models)

        # ── Build ML-only result ──
        result = {
            "verdict": ml_label if not insuf else "INCONCLUSIVE",
            "confidence": round(ml_score, 4),
            "vishing_probability": round(vishing_probability, 4),
            "safe_probability": round(ml_detail["safe_probability"], 4),
            "ml_risk_band": ml_detail["risk_band"],
            "source": "ml_only",
            "ml_label": ml_label,
            "ml_model": model_choice,
            "ml_confidence": round(ml_score, 4),
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
            "ai_status": "not_run",
            "ai_verdict": None,
            "ai_risk_level": None,
            "ai_alignment": None,
            "prompt_injection": {
                "detected": bool(injection_findings),
                "count": len(injection_findings),
                "types": sorted({f["type"] for f in injection_findings}),
                "matches": injection_findings[:5],
            },
        }

        # ── STEP 2: Hybrid Analysis (if ML score >= threshold) ──
        if not insuf:
            try:
                hybrid = await run_hybrid_analysis(
                    transcript=transcript,
                    model_choice=model_choice,
                    ml_label=ml_label,
                    ml_score=ml_score,
                    top_keywords=top_keywords,
                    suspicious_phrases=phrases,
                    vishing_probability=vishing_probability,
                )
                if hybrid.get("source") == "hybrid":
                    result["verdict"]        = hybrid.get("verdict", ml_label)
                    result["source"]         = "hybrid"
                    result["ai_status"]      = hybrid.get("ai_status")
                    result["ai_verdict"]     = hybrid.get("ai_verdict")
                    result["ai_risk_level"]  = hybrid.get("ai_risk_level")
                    result["ai_alignment"]   = hybrid.get("ai_alignment")
                    result["explanation"]    = hybrid.get("explanation")
                    result["scam_type"]      = hybrid.get("scam_type")
                    result["tactics"]        = hybrid.get("tactic", [])
                    result["similar_cases"]  = hybrid.get("similar_cases", [])
                    result["action_steps"]   = hybrid.get("action_steps", [])
                    result["divergence_flag"] = hybrid.get("divergence_flag", False)

                    if result["divergence_flag"]:
                        result["verdict"] = VERDICT_SUSPICIOUS
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
# Container signatures for the formats the API accepts. Checked against the
# uploaded bytes so a renamed file cannot pass the extension allowlist alone.
_AUDIO_SIGNATURES: tuple[tuple[int, bytes], ...] = (
    (0, b"RIFF"),          # .wav  (RIFF/WAVE)
    (0, b"OggS"),          # .ogg
    (0, b"fLaC"),          # .flac
    (0, b"ID3"),           # .mp3 with ID3 tag
    (0, b"\x1a\x45\xdf\xa3"),  # .webm / Matroska (EBML)
    (4, b"ftyp"),          # .m4a / MP4 family
)


def _looks_like_audio(content: bytes) -> bool:
    """True when the leading bytes match a supported audio container."""
    head = content[:32]
    for offset, magic in _AUDIO_SIGNATURES:
        if head[offset:offset + len(magic)] == magic:
            return True
    # Bare MPEG audio frame sync (mp3 without an ID3 header): 11 set bits.
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return True
    return False



@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    # Validate file type
    allowed = {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"}
    suffix = Path(file.filename or "audio.wav").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}")

    # ── Streamed size enforcement ──
    # The previous implementation did `content = await file.read()` and checked
    # the length afterwards, so an oversized upload was fully buffered in
    # memory before the 413 was returned — a 2 GB POST could exhaust the
    # container before the limit was ever applied. Enforce while reading.
    max_bytes = settings.MAX_UPLOAD_BYTES
    max_mb = max_bytes // (1024 * 1024)
    buffer = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            log_event(logging.WARNING, "upload.too_large", limit_mb=max_mb)
            raise HTTPException(status_code=413, detail=f"File too large (max {max_mb}MB)")
    content = bytes(buffer)

    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # ── Content-based type check ──
    # The extension is attacker-controlled metadata. Verify the bytes actually
    # look like a container we accept before handing the file to the ASR API.
    if not _looks_like_audio(content):
        log_event(logging.WARNING, "upload.rejected", reason="magic_bytes", suffix=suffix)
        raise HTTPException(
            status_code=400,
            detail="File content does not match a supported audio format",
        )

    # Transcribe via Groq Whisper API (whisper-large-v3-turbo)
    tmp = None
    try:
        client = _get_groq_client()
        if client is None:
            raise HTTPException(status_code=500, detail="Groq API key not configured")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content)
            tmp = f.name

        import asyncio
        def _sync_transcribe():
            with open(tmp, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(file.filename or f"audio{suffix}", audio_file.read()),
                    model="whisper-large-v3-turbo",
                    language="en",
                    response_format="verbose_json",
                )
            return transcription

        transcription_obj = await asyncio.to_thread(_sync_transcribe)
        
        # verbose_json returns text and duration
        transcript_text = transcription_obj.text.strip()
        duration = getattr(transcription_obj, "duration", 0.0)
        
        return {
            "transcript": transcript_text,
            "duration_seconds": duration,
            "model_used": "whisper-large-v3-turbo"
        }
    except HTTPException:
        raise
    except Exception as e:
        log_event(logging.ERROR, "transcribe.failed", error=repr(e)[:300])
        raise HTTPException(status_code=502, detail="Transcription service failed. Please try again.")
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
@app.get("/api/rate-limit")
async def rate_limit_status(user: dict = Depends(get_current_user)):
    """Return the current user's scan usage for the rolling 1-hour window."""
    username = user["sub"]
    allowed, used = check_rate_limit(username)
    return {
        "used": used,
        "max": MAX_ANALYSES_PER_HOUR,
        "remaining": max(0, MAX_ANALYSES_PER_HOUR - used),
        "allowed": allowed,
        "window": "1 hour",
    }


@app.get("/api/health")
async def health(request: Request):
    """Liveness + dependency status.

    This endpoint used to report ``supabase: true`` by merely constructing a
    client — an operation that performs no network I/O. It therefore reported
    a healthy database throughout a total outage, which is why a paused
    project surfaced only as an unexplained 500 on login. It now issues a real
    query.
    """
    groq_ok = check_groq_available()
    request.app.state.groq_available = groq_ok

    db = db_health_check()

    return {
        "ml_models": hasattr(request.app.state, "models") and bool(request.app.state.models),
        "groq": groq_ok,
        "ollama": groq_ok,  # legacy compat: frontend may still check this key
        "chromadb": getattr(request.app.state, "chroma_count", 0),
        "supabase": db["ok"],
        "supabase_detail": db["detail"],
        "supabase_latency_ms": db["latency_ms"],
    }


# ═══════════════════════════════════════════════
# ANALYTICS ENDPOINT (Admin Dashboard)
# ═══════════════════════════════════════════════
@app.get("/api/analytics")
async def analytics(user: dict = Depends(require_role("admin"))):
    """Aggregate stats from audit_log for the admin analytics dashboard.

    AUTHORISATION: admin only. This endpoint returns every user's scan history
    plus a username leaderboard. It previously depended on
    ``get_current_user``, so any account that could register could read the
    whole system's activity — the `role` claim was issued in the token and
    then never checked anywhere in the application.
    """
    from collections import Counter, defaultdict

    rows = get_recent_analytics(limit=500)

    if not rows:
        return {
            "total_scans": 0, "total_users": 0, "avg_confidence": 0, "vishing_rate": 0,
            "verdict_distribution": [], "daily_trend": [], "confidence_distribution": [], "top_users": [],
        }

    # Verdict distribution
    verdict_counts = Counter()
    for r in rows:
        v = (r.get("verdict") or "").lower()
        if "vishing" in v or "hang up" in v:
            verdict_counts["Vishing"] += 1
        elif "safe" in v or "legitimate" in v:
            verdict_counts["Safe"] += 1
        else:
            verdict_counts["Inconclusive"] += 1
    verdict_distribution = [{"name": k, "value": v} for k, v in verdict_counts.items()]

    # Daily trend (last 7 days)
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).date()
    daily = defaultdict(lambda: {"total": 0, "vishing": 0, "safe": 0})
    for r in rows:
        try:
            ts = datetime.fromisoformat((r.get("analyzed_at") or "").replace("Z", "+00:00"))
            day = ts.date()
            if (today - day).days <= 6:
                label = day.strftime("%d %b")
                daily[label]["total"] += 1
                v = (r.get("verdict") or "").lower()
                if "vishing" in v or "hang up" in v:
                    daily[label]["vishing"] += 1
                elif "safe" in v or "legitimate" in v:
                    daily[label]["safe"] += 1
        except Exception:
            pass
    daily_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        label = day.strftime("%d %b")
        entry = daily.get(label, {"total": 0, "vishing": 0, "safe": 0})
        daily_trend.append({"date": label, **entry})

    # Confidence distribution
    buckets = defaultdict(int)
    for r in rows:
        conf = float(r.get("confidence") or 0)
        bucket = min(int(conf * 10), 9)
        label = f"{bucket * 10}-{bucket * 10 + 10}%"
        buckets[label] += 1
    confidence_distribution = [
        {"range": f"{i*10}-{i*10+10}%", "count": buckets.get(f"{i*10}-{i*10+10}%", 0)}
        for i in range(10)
    ]

    # Top users
    user_counts = Counter(r.get("username", "unknown") for r in rows)
    top_users = [{"username": u, "scans": c} for u, c in user_counts.most_common(5)]

    # Averages
    confs = [float(r.get("confidence") or 0) for r in rows]
    avg_confidence = round(sum(confs) / len(confs) * 100, 1) if confs else 0
    vishing_rate = round(verdict_counts.get("Vishing", 0) / len(rows) * 100, 1) if rows else 0

    total_users = count_users() or len(set(r.get("username") for r in rows))

    return {
        "total_scans": len(rows), "total_users": total_users,
        "avg_confidence": avg_confidence, "vishing_rate": vishing_rate,
        "verdict_distribution": verdict_distribution, "daily_trend": daily_trend,
        "confidence_distribution": confidence_distribution, "top_users": top_users,
    }




# ═══════════════════════════════════════════════
# BENCHMARK ENDPOINT
# ═══════════════════════════════════════════════
_BENCHMARK_CASES = [
    ("vishing", "vishing",
     "This is the bank security department. Your account has been suspended due to suspicious "
     "unauthorized activity. You must verify your details and OTP immediately or legal action "
     "will be taken. Do not tell anyone about this call. Press 1 now."),
    ("vishing", "vishing",
     "Hello, I am calling from LHDN Inland Revenue. There is a warrant for your arrest due to "
     "unpaid taxes. You must settle fine immediately via Bitcoin transfer to avoid detention. "
     "Do not hang up or inform family members."),
    ("vishing", "vishing",
     "Your Microsoft Windows computer has been infected with a dangerous virus. Please install "
     "AnyDesk immediately so our certified technical support team can remotely remove the threat. "
     "Your banking credentials are at risk."),
    ("vishing", "vishing",
     "Congratulations! You have been selected as our lucky prize winner. To claim your reward, "
     "please confirm your credit card number and NRIC immediately. Offer expires within 24 hours."),
    ("vishing", "vishing",
     "This is Interpol. We have detected suspicious activity linked to your account involving "
     "money laundering. To avoid arrest, transfer funds of RM 5000 to our secure account now. "
     "Do not discuss this matter with anyone."),
    ("safe", "safe",
     "Hello, this is a courtesy call from the pharmacy. Your prescription is ready for pickup. "
     "Please bring your MyKad when you collect it. Our opening hours are 9am to 6pm. Have a great day."),
    ("safe", "safe",
     "Hi, I am calling from the school administration to remind you that the parent-teacher "
     "meeting is scheduled for next Friday at 3pm. No action is required from your side."),
    ("safe", "safe",
     "This is your dentist clinic calling to confirm your appointment tomorrow at 10am. "
     "If you need to reschedule, please call us back at our official number. See you soon."),
    ("safe", "safe",
     "Good afternoon, I am calling from the delivery department. Your parcel has arrived at the "
     "hub and will be delivered tomorrow between 9am and 12pm. You do not need to do anything."),
    ("safe", "safe",
     "Hello, this is customer service following up on your recent feedback. We have resolved the "
     "issue you raised last week. Is there anything else we can help you with today?"),
]


@app.get("/api/benchmark")
async def benchmark(request: Request, user: dict = Depends(get_current_user)):
    """
    Run a live ML speed and accuracy benchmark using the loaded models.
    Returns per-sample results plus aggregate accuracy and latency metrics.
    """
    import time as _time
    models   = request.app.state.models
    nn_model = request.app.state.nn_model

    cases, latencies, correct = [], [], 0
    for true_label, expected, transcript in _BENCHMARK_CASES:
        t0 = _time.perf_counter()
        ml_label, ml_score = run_inference(transcript, "SVM", models, nn_model)
        insuf, _ = insufficient_evidence(transcript, ml_score, label=ml_label)
        latency_ms = (_time.perf_counter() - t0) * 1000

        final_verdict = "inconclusive" if insuf else ml_label
        passed = (final_verdict == expected) or (expected == "vishing" and insuf)
        correct += int(passed)
        latencies.append(latency_ms)

        cases.append({
            "index":          len(cases) + 1,
            "true_label":     true_label,
            "expected":       expected,
            "got":            final_verdict,
            "confidence":     round(ml_score, 4),
            "latency_ms":     round(latency_ms, 2),
            "pass":           passed,
            "transcript_preview": transcript[:80] + "...",
        })

    accuracy   = round(correct / len(_BENCHMARK_CASES) * 100, 1)
    avg_lat    = round(sum(latencies) / len(latencies), 2)
    max_lat    = round(max(latencies), 2)
    ready      = accuracy >= 80 and avg_lat < 200

    return {
        "accuracy":        accuracy,
        "correct":         correct,
        "total":           len(_BENCHMARK_CASES),
        "avg_latency_ms":  avg_lat,
        "max_latency_ms":  max_lat,
        "ready":           ready,
        "vishing_threshold": 0.80,
        "reject_threshold":  0.80,
        "cases":           cases,
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
# THREAT INTELLIGENCE — PenipuMY API (External)
# ═══════════════════════════════════════════════
import penipu_client


@app.get("/api/threat-intel/phone")
async def threat_intel_phone(q: str, user: dict = Depends(get_current_user)):
    """Look up a phone number against PenipuMY scam database."""
    if not q or len(q.strip()) < 3:
        raise HTTPException(status_code=400, detail="Phone number must be at least 3 characters")
    if not penipu_client.is_configured():
        raise HTTPException(status_code=503, detail="PenipuMY API key not configured")
    try:
        result = await penipu_client.lookup_phone(q.strip())
        return result
    except Exception as e:
        log_event(logging.ERROR, "threatintel.upstream_failed", op="lookup", error=repr(e)[:300])
        raise HTTPException(status_code=502, detail="Threat intelligence lookup failed. Please try again.")


@app.get("/api/threat-intel/bank")
async def threat_intel_bank(q: str, user: dict = Depends(get_current_user)):
    """Look up a bank account against PenipuMY scam database."""
    if not q or len(q.strip()) < 3:
        raise HTTPException(status_code=400, detail="Bank account must be at least 3 characters")
    if not penipu_client.is_configured():
        raise HTTPException(status_code=503, detail="PenipuMY API key not configured")
    try:
        result = await penipu_client.lookup_bank(q.strip())
        return result
    except Exception as e:
        log_event(logging.ERROR, "threatintel.upstream_failed", op="lookup", error=repr(e)[:300])
        raise HTTPException(status_code=502, detail="Threat intelligence lookup failed. Please try again.")


@app.get("/api/threat-intel/search")
async def threat_intel_search(q: str, type: str = "auto", user: dict = Depends(get_current_user)):
    """Search PenipuMY scam database by phone, bank, social, or name."""
    if not q or len(q.strip()) < 3:
        raise HTTPException(status_code=400, detail="Search query must be at least 3 characters")
    if not penipu_client.is_configured():
        raise HTTPException(status_code=503, detail="PenipuMY API key not configured")
    try:
        result = await penipu_client.search(q.strip(), search_type=type)
        return result
    except Exception as e:
        log_event(logging.ERROR, "threatintel.upstream_failed", op="search", error=repr(e)[:300])
        raise HTTPException(status_code=502, detail="Threat intelligence lookup failed. Please try again.")


# REMOVED: GET /api/threat-intel/key
#
# This endpoint returned the raw PenipuMY API key to any authenticated caller,
# so the browser could query the third-party API directly. Because
# registration is open, anyone able to create an account could harvest the
# key, and it was visible in DevTools on every page load of the Threat Intel
# screen. That converts a server-side secret into a public one.
#
# The documented motivation was a geo-block on the Hugging Face Space egress
# IP. The correct remedy for that is a server-side egress path, not publishing
# the credential. All PenipuMY access now goes through the proxy routes above,
# which keep the key on the server.


@app.get("/api/threat-intel/stats")
async def threat_intel_stats(user: dict = Depends(get_current_user)):
    """Get platform-wide scam statistics from PenipuMY."""
    if not penipu_client.is_configured():
        raise HTTPException(status_code=503, detail="PenipuMY API key not configured")
    try:
        result = await penipu_client.get_stats()
        return result
    except Exception as e:
        log_event(logging.ERROR, "threatintel.upstream_failed", op="stats", error=repr(e)[:300])
        raise HTTPException(status_code=502, detail="Threat intelligence lookup failed. Please try again.")


# ═══════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=os.environ.get("HOST", "127.0.0.1"), port=8000, reload=False)

