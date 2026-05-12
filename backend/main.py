"""
main.py — FastAPI backend for ShieldGuard
==========================================
Exposes all ShieldGuard intelligence via REST endpoints.
Core logic is imported unchanged from the copied modules.

[v3.4 — 2026-05-05] LLM: Ollama → Groq API, Whisper: local → Groq API
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
from hybrid_engine import run_hybrid_analysis
from rag_module import ensure_scam_library
from llm_config import check_groq_available, check_ollama_available, _get_groq_client
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

    return {
        "status": "online" if ml_ok else "degraded",
        "components": {
            "ml_classifier":  {"ok": ml_ok,    "detail": "SVM v3 production model" if ml_ok else "not loaded"},
            "rag_chromadb":   {"ok": chroma > 0, "detail": f"{chroma} entries"},
            "llm_groq":       {"ok": groq_ok,   "detail": "reachable" if groq_ok else "not reachable"},
            "whisper_stt":    {"ok": groq_ok,    "detail": "Groq whisper-large-v3-turbo" if groq_ok else "requires Groq API"},
        },
        "model_count": len(ml_models) if ml_ok else 0,
        "version": "3.4",
    }


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
# Per-user lock: prevents multiple concurrent analyses from the same user.
# If the user clicks "Analyze" while one is already running, the second
# request is rejected immediately instead of queueing up Ollama calls.
import asyncio
_analysis_locks: dict[str, asyncio.Lock] = {}

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest, request: Request, user: dict = Depends(get_current_user)):
    username = user["sub"]

    # ── Per-user concurrency guard ──
    if username not in _analysis_locks:
        _analysis_locks[username] = asyncio.Lock()
    lock = _analysis_locks[username]
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
        too_short = len(transcript.strip().split()) < 5
        insuf = too_short
        insuf_reason = (
            "Transcript too short - provide more context for reliable analysis"
            if too_short else ""
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
                )
            return transcription.text.strip()

        transcript_text = await asyncio.to_thread(_sync_transcribe)
        return {"transcript": transcript_text}
    except HTTPException:
        raise
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
    groq_ok = check_groq_available()
    request.app.state.groq_available = groq_ok

    supabase_ok = True
    try:
        from database import get_supabase
        get_supabase()
    except Exception:
        supabase_ok = False

    return {
        "ml_models": hasattr(request.app.state, "models") and bool(request.app.state.models),
        "groq": groq_ok,
        "ollama": groq_ok,  # legacy compat: frontend may still check this key
        "chromadb": getattr(request.app.state, "chroma_count", 0),
        "supabase": supabase_ok,
    }


# ═══════════════════════════════════════════════
# ANALYTICS ENDPOINT (Admin Dashboard)
# ═══════════════════════════════════════════════
@app.get("/api/analytics")
async def analytics(user: dict = Depends(get_current_user)):
    """Aggregate stats from audit_log for the admin analytics dashboard."""
    try:
        from database import get_supabase
        from collections import Counter, defaultdict

        sb = get_supabase()
        resp = (
            sb.table("audit_log")
              .select("verdict, confidence, model_used, input_mode, analyzed_at, username")
              .order("analyzed_at", desc=True)
              .limit(500)
              .execute()
        )
        rows = resp.data or []

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

        users_resp = sb.table("users").select("username", count="exact").execute()
        total_users = users_resp.count or len(set(r.get("username") for r in rows))

        return {
            "total_scans": len(rows), "total_users": total_users,
            "avg_confidence": avg_confidence, "vishing_rate": vishing_rate,
            "verdict_distribution": verdict_distribution, "daily_trend": daily_trend,
            "confidence_distribution": confidence_distribution, "top_users": top_users,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)[:200]}")




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
# RUN
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
