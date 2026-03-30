# ShieldGuard — Complete System Context
> **Version:** 3.0 — Hybrid Intelligence System (React + FastAPI)
> **Project:** Vishing Detection System using ML, NLP, LLM & Multi-Agent AI
> **Type:** FYP — Cybersecurity
> **Status:** IMPLEMENTED — Phase 1 (ML) + Phase 2 (LLM + RAG + CrewAI) + Phase 3 (React + FastAPI migration)

---

## Project Overview

**ShieldGuard** is a web-based vishing (voice phishing) detection system. Users can record a suspicious call, upload an audio file, or paste a transcript — the system classifies it as **vishing** or **safe** using a hybrid cascade of ML models, RAG pattern matching, and LLM-powered multi-agent reasoning.

The system has two frontends:
- **Legacy:** Streamlit (monolithic, in `app/`)
- **Current:** React + Tailwind CSS (decoupled, in `frontend/`) with FastAPI backend (`backend/`)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT                                  │
│         (audio recording / uploaded file / transcript)          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          │  React Frontend       │  Port 5173
          │  (Vite + Tailwind)    │
          └───────────┬───────────┘
                      │ HTTP (Axios + JWT)
          ┌───────────┴───────────┐
          │  FastAPI Backend      │  Port 8000
          │  (Python REST API)    │
          └───────────┬───────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — ML CLASSIFIER  (Phase 1)                             │
│                                                                 │
│  Engine:  TF-IDF + SVM / LR / RF / NN                           │
│  Speed:   <100ms (fast, deterministic)                          │
│  Output:  ml_score (float), ml_label, top_keywords              │
│                                                                 │
│  if ml_score < 0.45  → ML-ONLY result (skip LLM)               │
│  if ml_score ≥ 0.45  → proceed to Layer 2                       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — RAG SEARCH  (Phase 2)                                │
│                                                                 │
│  Engine:  ChromaDB + sentence-transformers (all-MiniLM-L6-v2)   │
│  Data:    1,266 indexed vishing transcripts                     │
│  Action:  Query top-2 most similar historical scam transcripts  │
│  Output:  similar_cases → {text_preview, scam_type, similarity} │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — CREWAI MULTI-AGENT  (Phase 2)                        │
│                                                                 │
│  LLM:    Llama 3.2 3B via Ollama (local, no API key)            │
│  Process: Sequential — each agent reads previous output         │
│                                                                 │
│  Agent A — Technical Auditor                                    │
│    → Validates if ML flag is justified or false positive        │
│                                                                 │
│  Agent B — Pattern Detective                                    │
│    → Classifies scam type using transcript + RAG results        │
│                                                                 │
│  Agent C — Psychology Profiler                                  │
│    → Identifies social engineering tactics (URGENCY, FEAR, etc) │
│                                                                 │
│  Agent D — Safety Guardian                                      │
│    → Produces user-facing verdict + explanation + action steps  │
│                                                                 │
│  Output:  verdict, explanation, scam_type, tactics, actions     │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  CROSS-CHECK — Divergence Detection                             │
│                                                                 │
│  if ML says "vishing" but LLM says "safe" → FLAG               │
│  if ML says "safe" but LLM says "vishing" → FLAG               │
│  Flagged → verdict = "SUSPICIOUS — UNCONFIRMED"                 │
│  Threshold: DIVERGENCE_THRESHOLD = 0.3                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Backend (Python)
| Component | Technology | Version |
|---|---|---|
| Web Framework | FastAPI | ≥0.115 |
| ASGI Server | Uvicorn | ≥0.32 |
| ML Framework | scikit-learn | 1.7.2 |
| Deep Learning | TensorFlow/Keras | 2.15.1 |
| NLP Vectorizer | TF-IDF (sklearn) | — |
| Speech-to-Text | OpenAI Whisper | base model |
| RAG Database | ChromaDB | ≥0.5.0 |
| RAG Embeddings | sentence-transformers | all-MiniLM-L6-v2 |
| Agent Framework | CrewAI | ≥0.28.0 |
| LLM Backend | Ollama | llama3.2:3b (local) |
| LLM Interface | LangChain + langchain-ollama | ≥0.2.0 |
| Database | Supabase (PostgreSQL) | Cloud |
| Authentication | bcrypt + JWT (python-jose) | — |
| Audio Processing | pydub + ffmpeg | — |

### Frontend (JavaScript)
| Component | Technology | Version |
|---|---|---|
| UI Framework | React | 18 |
| Build Tool | Vite | 8.x |
| CSS Framework | Tailwind CSS | 4.x |
| HTTP Client | Axios | — |
| Routing | react-router-dom | v6 |
| State Management | Zustand | — |
| Charts | Recharts | — |

### Infrastructure
| Component | Technology |
|---|---|
| LLM Server | Ollama (localhost:11434) |
| Database | Supabase (cloud PostgreSQL) |
| Models Storage | Local filesystem (`models/`) |
| RAG Storage | Local filesystem (`data/scam_library/`) |
| Audio Engine | ffmpeg (D:\ffmpeg\ffmpeg-8.1-essentials_build\bin) |

---

## Security Implementation

### Authentication
- **Password Hashing:** bcrypt with 12 salt rounds
- **Password Policy:** Minimum 12 characters, requires uppercase, lowercase, digit, and special character
- **Username Policy:** 3-32 characters, alphanumeric + underscore only
- **Session Management:** JWT tokens (HS256) with 24-hour expiry, stored in memory (not localStorage)
- **Token Handling:** Attached as `Authorization: Bearer <token>` on every API request

### Brute-Force Protection
- **Max Attempts:** 5 failed logins per 15-minute window
- **Lockout Duration:** 15 minutes after 5th failure
- **Tracking:** All login attempts logged to Supabase `login_attempts` table

### Rate Limiting
- **Scan Limit:** 30 analyses per hour per user
- **Tracking:** Each scan event logged to Supabase `rate_limit` table
- **Enforcement:** Checked before every analysis; returns HTTP 429 when exceeded

### Input Sanitization
- **XSS Prevention:** All transcript inputs stripped of HTML tags via `re.sub(r"<[^>]+>", "", text)`
- **HTML Entity Decoding:** `html.unescape()` applied after stripping
- **Length Limit:** Maximum 10,000 characters per transcript

### CORS
- **Development:** Allows `http://localhost:5173` (Vite) and `http://localhost:3000`
- **Configuration:** Via `CORS_ORIGINS` environment variable

### Data Privacy
- **No External APIs:** All AI processing runs locally (Ollama, ChromaDB, Whisper)
- **No Data Sent Externally:** Transcripts never leave the local machine
- **Credential Storage:** Supabase keys in `.env` file (gitignored)

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Login with username/password, returns JWT |
| POST | `/api/auth/register` | Create account, returns JWT |
| POST | `/api/auth/logout` | Logout (client-side token discard) |
| GET | `/api/auth/me` | Get current user from JWT |

### Analysis
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze` | Full ML + hybrid cascade analysis |
| POST | `/api/transcribe` | Upload audio → Whisper transcription |
| GET | `/api/history` | Get last N scan results from Supabase |
| GET | `/api/health` | System health check (models, Ollama, ChromaDB, Supabase) |
| GET | `/api/samples` | Get sample vishing/safe transcripts |

### Analysis Response Schema
```json
{
  "verdict": "VISHING DETECTED | CALL APPEARS SAFE | INCONCLUSIVE | SUSPICIOUS — UNCONFIRMED",
  "confidence": 0.942,
  "source": "hybrid | ml_only",
  "ml_label": "vishing | safe",
  "ml_model": "SVM",
  "insufficient_evidence": false,
  "insufficient_reason": null,
  "suspicious_phrases": ["account will be suspended", "verify your OTP"],
  "highlighted_transcript": "<full transcript with <mark> tags>",
  "top_keywords": [["verify", 0.823], ["account", 0.711]],
  "explanation": "LLM-generated explanation string or null",
  "scam_type": "Bank Impersonation | null",
  "tactics": ["URGENCY", "AUTHORITY", "ISOLATION"],
  "similar_cases": [
    { "text_preview": "...", "scam_type": "OTP Fraud", "similarity": 0.87 }
  ],
  "action_steps": ["Hang up immediately", "Call your bank..."],
  "divergence_flag": false
}
```

---

## ML Models

### Training Data
- **Dataset:** 1,785 labeled call transcripts (`data/english_dataset_final_v2.csv`)
- **Split:** 80/20 train/test
- **Labels:** "vishing" and "safe"
- **Preprocessing:** TF-IDF vectorization

### Models (Phase 1)
| Model | File | Accuracy | Note |
|---|---|---|---|
| SVM | `models/svm_model.pkl` | 98.5% | CalibratedClassifier wrapping Pipeline(tfidf + svc) |
| Logistic Regression | `models/logistic_regression_model.pkl` | ~97% | Pipeline(tfidf + lr) |
| Random Forest | `models/rf_model.pkl` | ~96% | Pipeline(tfidf + rf) |
| Neural Network | `models/neural_network.keras` | ~97% | Keras model, input: tf.constant([text]) |
| Vectorizer | `models/vectorizer.pkl` | — | Shared TF-IDF vectorizer |

### Inference Interface
- **Classical models:** `model.predict([text])` → label, `model.predict_proba([text])` → probabilities
- **Neural Network:** `nn.predict(tf.constant([text])) → float` (sigmoid, >0.5 = vishing)

### Explainability (XAI)
- **SVM + LR only:** TF-IDF coefficient extraction
- Identifies top-5 keywords contributing most to the prediction
- Displayed as horizontal bar chart in frontend

---

## RAG Module (ChromaDB)

- **Collection:** `scam_transcripts` in `data/scam_library/`
- **Embedding Model:** `all-MiniLM-L6-v2` (384-dim, CPU-friendly)
- **Index Size:** 1,266 vishing transcripts from training data
- **Query:** Cosine similarity, returns top-2 matches
- **Scam Types:** Bank Impersonation, OTP Fraud, Tech Support Scam, Government Impersonation, Prize/Lottery Scam, Authority Threat Scam, Refund Scam, Investment Fraud, General Vishing
- **Cache:** HuggingFace models cached at `.hf_cache/` relative to project root

---

## Multi-Agent System (CrewAI)

### Agents
| Agent | Role | Output |
|---|---|---|
| Technical Auditor | Validates ML flag (confirms or challenges) | "ML flag CONFIRMED" or "ML flag UNCERTAIN" |
| Pattern Detective | Classifies scam type using transcript + RAG | Scam type + reasoning |
| Psychology Profiler | Detects social engineering tactics | List of tactics with evidence |
| Safety Guardian | Produces final user-facing verdict | VERDICT, SCAM_TYPE, TACTICS, EXPLANATION, ACTION_STEPS |

### Configuration
- **LLM:** `ollama/llama3.2:3b` (string identifier for CrewAI 1.x)
- **Process:** Sequential (each agent sees previous agent's output)
- **Fallback:** If Ollama is offline, returns ML-only result with graceful message

---

## Vishing Detection Patterns

14 regex patterns detect suspicious phrases:
- Account threats: `account.{0,15}(suspend|block|freeze|close|terminat)`
- Identity verification: `(verify|confirm).{0,15}(account|identity|detail|information)`
- Urgency language: `(urgent|immediately|right now|act now|limited time|within \d+ hour)`
- OTP requests: `(OTP|one.time.password|one time pin|passcode)`
- Financial info: `(bank|credit card|debit card).{0,20}(number|detail|info)`
- Social engineering: `do not (tell|share|inform|disclose).{0,20}(anyone|anyone else|family|police|authority)`
- Legal threats: `(legal action|arrested|lawsuit|court order|warrant)`
- Money transfers: `transfer.{0,20}(fund|money|amount|rm|ringgit|dollar)`

---

## Supabase Database Schema

### Tables
| Table | Columns | Purpose |
|---|---|---|
| `users` | username, password_hash, role, created_at, last_login | User accounts |
| `login_attempts` | username, success, attempted_at | Brute-force tracking |
| `audit_log` | username, input_length, input_mode, model_used, verdict, confidence, analyzed_at | Scan history |
| `rate_limit` | username, action, occurred_at | Rate limiting |

---

## File Structure

```
VishingDetection/
│
├── backend/                      ← FastAPI backend (current)
│   ├── main.py                   ← FastAPI app: lifespan, endpoints, JWT auth
│   ├── models_loader.py          ← ML model loading (joblib, keras)
│   ├── inference.py              ← run_inference, get_explanation, detect_suspicious_phrases
│   ├── hybrid_engine.py          ← ML→RAG→CrewAI cascade orchestrator
│   ├── rag_module.py             ← ChromaDB scam library + similarity search
│   ├── llm_config.py             ← Ollama LLM configuration
│   ├── database.py               ← Supabase client + all DB functions
│   ├── auth.py                   ← Password hashing, validation, sanitization
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent_definitions.py  ← 4 CrewAI agent definitions
│   │   └── crew.py               ← Crew assembly, task prompting, output parsing
│   ├── requirements.txt
│   └── .env                      ← Environment variables (gitignored)
│
├── frontend/                     ← React frontend (current)
│   ├── index.html                ← Google Fonts, meta tags
│   ├── vite.config.js            ← Vite + Tailwind + API proxy to :8000
│   ├── package.json
│   └── src/
│       ├── App.jsx               ← Router: /login, /app (protected)
│       ├── main.jsx              ← React DOM mount
│       ├── index.css             ← Tailwind + design system (CSS variables, keyframes)
│       ├── api/client.js         ← Axios with JWT interceptor
│       ├── hooks/
│       │   ├── useAuth.js        ← Zustand: login, register, logout, token
│       │   ├── useAnalysis.js    ← Zustand: analyze with progress tracking
│       │   └── useTranscribe.js  ← Zustand: audio transcription
│       ├── pages/
│       │   ├── LoginPage.jsx     ← Login/Register with lockout display
│       │   └── MainDashboard.jsx ← Full analysis dashboard
│       └── components/
│           ├── layout/           ← Header (logo, online badge), Footer
│           ├── auth/             ← LoginForm, RegisterForm
│           ├── input/            ← InputTabs, AudioRecorder, AudioUploader, TranscriptInput
│           ├── results/          ← VerdictCard, RiskGauge, ConfidenceBar, PhraseChips,
│           │                       HighlightedTranscript, XAIPanel, AIAnalysisCard,
│           │                       TacticChips, RAGSimilarCases, ActionSteps,
│           │                       SafetyAdvice, DivergenceWarning
│           ├── dashboard/        ← HeroSection, StepGuide, RateLimitBar, ScanHistory
│           └── ui/               ← StatusBadge, InfoBox, WarnBox, ModelSelector
│
├── app/                          ← Streamlit frontend (legacy, Phase 1+2)
│   ├── main.py                   ← Streamlit entry point
│   ├── streamlit_app.py          ← UI + inference + CSS
│   ├── hybrid_engine.py
│   ├── rag_module.py
│   ├── llm_config.py
│   ├── database.py               ← Uses st.secrets (Streamlit-specific)
│   ├── auth.py
│   └── agents/
│
├── models/                       ← Trained ML models (production)
│   ├── svm_model.pkl
│   ├── logistic_regression_model.pkl
│   ├── rf_model.pkl
│   ├── neural_network.keras
│   └── vectorizer.pkl
│
├── data/
│   ├── english_dataset_final_v2.csv  ← Production dataset (1,785 transcripts)
│   ├── scam_library/                 ← ChromaDB persistent storage
│   ├── archive/                      ← Old/intermediate datasets (gitignored)
│   └── raw/                          ← Raw audio & source data (gitignored)
│
├── docs/                         ← Documentation & reference files
│   ├── supabase_schema.sql       ← Database schema
│   └── requirements_streamlit.txt ← Legacy Streamlit dependencies
│
├── notebooks/                    ← Jupyter notebooks (training & experiments)
│   ├── 01_baseline_text_classification.ipynb
│   ├── 02_prepare_korccvi.ipynb
│   ├── 03_prepare_kaggle_voice.ipynb
│   ├── 04_index_kaggle_audio.ipynb
│   ├── evaluation.ipynb
│   └── test.ipynb
│
├── tests/                        ← Test files
│   ├── test_auth.py
│   └── test_rag.py
│
├── .streamlit/secrets.toml       ← Supabase credentials (legacy, gitignored)
├── .gitignore
├── README.md                     ← Quick start guide
└── LLMContext.md                 ← This file — complete system documentation
```


---

## How to Run

### Prerequisites
- Python 3.12+
- Node.js 18+
- Ollama installed with `llama3.2:3b` model pulled
- ffmpeg installed at `D:\ffmpeg\ffmpeg-8.1-essentials_build\bin`

### Option A: React + FastAPI (Recommended)

**Terminal 1 — Backend:**
```powershell
cd d:\FYP1\VishingDetection
.venv\Scripts\activate
cd backend
python main.py
# Backend runs on http://localhost:8000
```

**Terminal 2 — Frontend:**
```powershell
cd d:\FYP1\VishingDetection\frontend
npm install
npm run dev
# Frontend runs on http://localhost:5173
```

**Open:** http://localhost:5173

### Option B: Streamlit (Legacy)

```powershell
cd d:\FYP1\VishingDetection
.venv\Scripts\activate
.venv\Scripts\streamlit.exe run app/main.py
# Runs on http://localhost:8501
```

### Environment Variables (Backend)

Create `backend/.env`:
```
SUPABASE_URL=https://xwuwynsvpgavsadnnlko.supabase.co
SUPABASE_KEY=your-anon-key
OLLAMA_BASE_URL=http://localhost:11434
JWT_SECRET=your-secret-key
MODELS_DIR=../models
HF_CACHE_DIR=../.hf_cache
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Start Ollama (Required for Hybrid Analysis)
```powershell
ollama serve
# In another terminal:
ollama pull llama3.2:3b
```

---

## Design System

### Fonts
- **Orbitron** — Display/headings (cyberpunk, futuristic)
- **Rajdhani** — Body text (clean, readable)
- **Share Tech Mono** — Monospace/data (terminal aesthetic)

### Color Palette
| Variable | Hex | Usage |
|---|---|---|
| `--bg` | `#04080f` | Page background |
| `--c1` | `#08111c` | Card background |
| `--c2` | `#0b1825` | Nested card background |
| `--red` | `#e8203c` | Threat/danger |
| `--green` | `#00e87a` | Safe/success |
| `--blue` | `#00aaff` | Accent/info |
| `--amber` | `#f0a800` | Warning/caution |
| `--text` | `#d8eaf8` | Primary text |
| `--muted` | `#4a7090` | Secondary text |
| `--border` | `#112233` | Borders |

### Animations
- `fadeUp` — Element entrance animation
- `flicker` — Logo glitch effect
- `pulsered` / `pulsegreen` — Verdict card glow
- `blink` — System online indicator
- `recpulse` — Recording indicator pulse
- `vaporOut` / `vaporIn` — Hero text cycling
- `drawPath` / `fadePath` — SVG background paths

### Key UI Elements
- **RiskGauge** — SVG semicircle with animated needle (green→amber→red)
- **VerdictCard** — Pulsing glow border matching threat level
- **HeroSection** — Mouse-reactive SVG paths + vaporize text cycling
- **AudioRecorder** — Browser MediaRecorder API with pulsing red dot
- Grid background with radial blue/red glows

---

## Threshold Configuration

| Threshold | Value | Purpose |
|---|---|---|
| `ML_THRESHOLD` | 0.45 | Skip LLM if ML confidence < 45% |
| `DIVERGENCE_THRESHOLD` | 0.3 | Flag ML vs LLM disagreement |
| `min_words` | 5 | Minimum transcript length |
| `min_conf` | 0.70 | Minimum confidence for conclusive verdict |
| `MAX_ANALYSES_PER_HOUR` | 30 | Rate limit per user |
| `MAX_ATTEMPTS` | 5 | Login attempts before lockout |
| `LOCKOUT_MINUTES` | 15 | Lockout duration |
