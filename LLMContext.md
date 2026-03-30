# ShieldGuard — Complete System Context
> **Version:** 2.0 — Hybrid Intelligence System
> **Project:** Vishing Detection System using ML, NLP, LLM & Multi-Agent AI
> **Type:** FYP — Cybersecurity
> **Status:** IMPLEMENTED — Phase 1 (ML) + Phase 2 (LLM + RAG + CrewAI) both live

---

## Project Overview

**ShieldGuard** is a web-based vishing (voice phishing) detection system. Users can record a suspicious call, upload an audio file, or paste a transcript — the system classifies it as **vishing** or **safe** using a hybrid cascade of ML models, RAG pattern matching, and LLM-powered multi-agent reasoning.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INPUT                                  │
│         (audio recording / uploaded file / transcript)          │
└─────────────────────┬───────────────────────────────────────────┘
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
│  Agent A: Technical Auditor    → validates ML flag              │
│  Agent B: Pattern Detective    → classifies scam type           │
│  Agent C: Psychology Profiler  → detects manipulation tactics   │
│  Agent D: Safety Guardian      → writes user-facing verdict     │
│                                                                 │
│  Output:  verdict, scam_type, tactics, explanation, action_steps│
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  CROSS-CHECK — DIVERGENCE DETECTION                             │
│                                                                 │
│  Compares ML verdict vs LLM verdict                             │
│  If they disagree → flag as "SUSPICIOUS — UNCONFIRMED"          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  SHIELDGUARD UI  (Streamlit)                                    │
│                                                                 │
│  Displays: ML verdict, confidence bar, highlighted transcript,  │
│  XAI reasoning bar chart, AI explanation panel, tactic chips,   │
│  RAG similar cases, action steps, safety advice                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Full Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | Streamlit + custom HTML/CSS | Web UI with dark cyberpunk theme |
| **ML Models** | SVM, Logistic Regression, Random Forest, Neural Network | Phase 1 — fast binary classification |
| **Feature Extraction** | TF-IDF (char_wb n-grams, 3-5, 30K features) | Text features for classical ML |
| **Speech-to-Text** | OpenAI Whisper (`base` model, local) | Audio → transcript |
| **Audio Recording** | `streamlit-audiorecorder` | Live mic capture in browser |
| **Vector Database** | ChromaDB (persistent, local) | RAG — 1,266 indexed scam transcripts |
| **Embedding Model** | `all-MiniLM-L6-v2` (sentence-transformers) | 384-dim embeddings for similarity search |
| **LLM** | Llama 3.2 3B via Ollama (local) | Natural language reasoning & explanation |
| **Agent Framework** | CrewAI 1.x (sequential process) | 4-agent multi-agent system |
| **LLM Integration** | `langchain-ollama` (`OllamaLLM`) | LangChain-compatible LLM wrapper |
| **Database** | Supabase (PostgreSQL cloud) | Users, auth, audit logs, rate limiting |
| **Auth** | bcrypt (rounds=12) | Password hashing |
| **Fonts** | Orbitron, Rajdhani, Share Tech Mono | Google Fonts for UI |

---

## Project File Structure

```
VishingDetection/
├── .streamlit/
│   └── secrets.toml              ← Supabase credentials (gitignored)
├── .hf_cache/                    ← HuggingFace model cache (gitignored)
│
├── app/
│   ├── main.py                   ← Entry point, auth router, session state
│   ├── streamlit_app.py          ← Main UI, ML inference, hybrid result display
│   ├── database.py               ← Supabase client, all DB operations
│   ├── auth.py                   ← Password hashing, validation, XSS sanitization
│   ├── supabase_schema.sql       ← SQL schema for Supabase tables
│   ├── hybrid_engine.py          ← Phase 2: ML → RAG → CrewAI orchestrator
│   ├── rag_module.py             ← Phase 2: ChromaDB + sentence-transformers RAG
│   ├── llm_config.py             ← Phase 2: Ollama LLM configuration + health check
│   └── agents/
│       ├── __init__.py           ← Package init
│       ├── agent_definitions.py  ← 4 CrewAI agent definitions
│       └── crew.py               ← Crew assembly, prompt building, output parsing
│
├── models/
│   ├── vectorizer.pkl            ← TF-IDF vectorizer (standalone)
│   ├── svm_model.pkl             ← CalibratedClassifierCV wrapping LinearSVC
│   ├── logistic_regression_model.pkl  ← Pipeline (tfidf → LogisticRegression)
│   ├── rf_model.pkl              ← Pipeline (tfidf → RandomForestClassifier)
│   ├── neural_network.keras      ← Keras model with TextVectorization
│   └── neural_network.h5         ← Legacy H5 format (backup)
│
├── data/
│   ├── english_dataset_final_v2.csv  ← Primary dataset (1,803 rows)
│   ├── scam_library/             ← ChromaDB persistent storage (gitignored)
│   └── (various CSV files)       ← Other dataset versions
│
├── notebooks/
│   └── 01_baseline_text_classification.ipynb
├── tests/
├── requirements.txt
└── users.db                      ← OLD SQLite file (unused, safe to delete)
```

---

## File-by-File Documentation

### Phase 1 Files (ML + UI)

#### `app/main.py` — Entry Point & Auth Router
- Sets `st.set_page_config(layout="centered")`
- Initializes session state (12 keys including Phase 2 additions)
- Calls `ensure_scam_library()` on startup (Phase 2: populates ChromaDB)
- Renders login/register with full custom CSS (dark cyberpunk theme)
- Routes to `render_app()` after successful authentication
- Security: brute-force lockout display, remaining attempts counter

#### `app/streamlit_app.py` — Main Application UI
- **Header**: SHIELDGUARD logo, SYSTEM ONLINE badge, operator name, logout
- **Hero section**: description, stats (98.5% accuracy, 4+1 ML+LLM, RAG, 4 AI Agents, XAI)
- **3-step guide**: Record/Upload → Analyze → Act on Results
- **Rate limit bar**: shows usage (30 scans/hour)
- **3-tab input system**:
  - Tab 1: Record Audio (live mic via `streamlit-audiorecorder`)
  - Tab 2: Upload Recording (.wav/.mp3/.m4a/.ogg/.flac, max 25MB)
  - Tab 3: Paste Transcript (with sample vishing/safe buttons)
- **Whisper transcription** for both audio tabs
- **Advanced Settings**: AI model selection (SVM, LR, RF, NN)
- **Analysis flow**: ML inference → hybrid analysis (RAG + CrewAI) → render results
- **Result rendering**: threat/safe/inconclusive cards with pulsing glow animations
- **Suspicious phrase detection**: regex patterns → highlighted transcript
- **XAI reasoning panel**: weighted bar chart (SVM + LR only) showing TF-IDF contributions
- **Phase 2 panels** (when hybrid analysis triggered):
  - AI Analysis card (scam type, detected tactics, LLM explanation)
  - Social engineering tactic chips (URGENCY, AUTHORITY, FEAR, ISOLATION, RECIPROCITY)
  - RAG similar cases card (similarity %, matched scam type, text preview)
  - AI recommended action steps
  - Divergence warning (when ML and LLM disagree)
  - Source badge: "ML ONLY" vs "HYBRID (ML + AI)"
- **Safety advice**: different recommendations for vishing vs safe
- **Scan history**: last 10 results from Supabase audit_log
- **Footer**: SHIELDGUARD v2.0 with tech stack labels

#### `app/database.py` — Supabase Backend
- `get_supabase()` — cached Supabase client
- `init_db()` — no-op (tables created via SQL schema)
- `get_user(username)` — fetch user row
- `create_user(username, password_hash)` — insert new user
- `record_login_attempt(username, success)` — logs attempt, updates last_login
- `is_locked_out(username)` → `(locked: bool, minutes_remaining: int)`
- `count_recent_failures(username)` — for remaining attempts display
- `log_analysis(...)` — writes every scan to audit_log
- `get_user_history(username, limit)` — last N scans for history panel
- `check_rate_limit(username)` → `(allowed: bool, used_count: int)`
- `record_rate_event(username)` — inserts rate limit event
- Constants: `MAX_ATTEMPTS=5`, `LOCKOUT_MINUTES=15`, `MAX_ANALYSES_PER_HOUR=30`

#### `app/auth.py` — Authentication & Sanitization
- `validate_password(password)` — 12+ chars, upper, lower, digit, special
- `validate_username(username)` — alphanumeric + underscore, 3–32 chars
- `sanitize_input(text, max_length)` — strips HTML tags, prevents XSS
- `hash_password(password)` — bcrypt, rounds=12
- `verify_password(password, hashed)` — safe bcrypt check

#### `app/supabase_schema.sql` — Database Schema
Creates 4 tables: `users`, `login_attempts`, `audit_log`, `rate_limit`
Creates indexes on (username, time) for fast lockout/rate queries
Enables Row Level Security (RLS) on all tables

---

### Phase 2 Files (LLM + RAG + CrewAI)

#### `app/llm_config.py` — Ollama LLM Configuration
- `OLLAMA_BASE_URL = "http://localhost:11434"`
- `MODEL_PRESETS` — config for llama3.2:3b, qwen2.5:32b, llama3.3:70b
- `check_ollama_available()` — pings Ollama server, returns `True/False`
- `get_available_models()` — lists all pulled models in Ollama
- `get_llm(model)` — returns `OllamaLLM` instance (from `langchain-ollama`)

#### `app/rag_module.py` — RAG with ChromaDB
- Sets `HF_HOME` to project-local `.hf_cache/` directory (avoids C: drive issues)
- **Embedding model**: `all-MiniLM-L6-v2` (384-dim, CPU-friendly, ~80MB)
- **Storage**: `data/scam_library/` (persistent ChromaDB, cosine similarity)
- `build_scam_library(csv_path)` — reads dataset, filters vishing rows, embeds and stores in ChromaDB. Auto-detects text/label columns. Heuristic scam type classification. Batch size 64.
- `_classify_scam_type(text)` — keyword-based classifier: Bank Impersonation, OTP Fraud, Tech Support Scam, Government Impersonation, Prize/Lottery, Authority Threat, Refund Scam, Investment Fraud, General Vishing
- `query_similar_scams(transcript, n_results=2)` → `[{text_preview, scam_type, similarity}]`
- `ensure_scam_library()` — called on startup, builds library if empty (1,266 entries from dataset)

#### `app/hybrid_engine.py` — Hybrid Orchestrator
- `ML_THRESHOLD = 0.45` — skip LLM below this score
- `DIVERGENCE_THRESHOLD = 0.3` — flag ML vs LLM disagreement
- `run_hybrid_analysis(transcript, model_choice, ml_label, ml_score, top_keywords, ...)` → dict:
  1. **Threshold gate**: score < 0.45 → return ML-only result
  2. **RAG lookup**: query ChromaDB for top-2 similar scam cases
  3. **Build case file**: package transcript + ML outputs + RAG results
  4. **Run CrewAI crew**: 4-agent sequential pipeline
  5. **Cross-check**: compare ML verdict vs LLM verdict, flag divergence
  6. **Return**: structured dict with verdict, confidence, source, explanation, tactics, scam_type, similar_cases, action_steps, divergence_flag

#### `app/agents/__init__.py` — Package Init
Empty init to make `agents/` a proper Python package.

#### `app/agents/agent_definitions.py` — 4 CrewAI Agents
Each agent is a `crewai.Agent` with role, goal, backstory, and `llm` set to a string identifier (`"ollama/llama3.2:3b"` for CrewAI 1.x):

| Agent | Role | What It Does |
|---|---|---|
| **Technical Auditor** | ML Score Interpreter | Validates whether ML flag is justified by examining transcript structure |
| **Pattern Detective** | Scam Methodology Classifier | Matches call to known scam type using RAG results + transcript |
| **Psychology Profiler** | Social Engineering Analyst | Identifies URGENCY, AUTHORITY, FEAR, ISOLATION, RECIPROCITY tactics |
| **Safety Guardian** | User Output Writer | Consolidates all findings into plain-language verdict + action steps |

#### `app/agents/crew.py` — Crew Assembly & Execution
- `_build_audit_prompt(case_file)` — builds prompt for Technical Auditor
- `_build_pattern_prompt(case_file)` — builds prompt for Pattern Detective (includes RAG results)
- `_build_psych_prompt(case_file)` — builds prompt for Psychology Profiler
- `_build_guardian_prompt(case_file)` — builds prompt for Safety Guardian (structured output format)
- `_parse_guardian_output(raw_output)` — regex parser for VERDICT, SCAM_TYPE, TACTICS, EXPLANATION, ACTION_STEPS
- `run_crew(case_file, model)` — assembles 4 agents + 4 tasks → `Crew(process=sequential)` → `crew.kickoff()` → parse and return structured dict
- **Error handling**: if Ollama unreachable or crew fails, returns graceful fallback dict

---

## ML Models — Phase 1

### Dataset
| Property | Value |
|---|---|
| File | `english_dataset_final_v2.csv` |
| Total rows | 1,803 |
| After dedup | 1,785 |
| Vishing | 1,248 |
| Safe | 537 |
| Split method | `GroupShuffleSplit` (leakage-safe) |
| Train set | 1,249 (854 vishing, 395 safe) |
| Test set | 536 (394 vishing, 142 safe) |

### Feature Extraction
```python
TfidfVectorizer(
    analyzer     = "char_wb",     # character n-grams with word boundaries
    ngram_range  = (3, 5),
    min_df       = 2,
    max_df       = 0.95,
    max_features = 30_000
)
```
Character-level n-grams capture partial words, morphological patterns, and are robust to spelling variations in scam scripts.

### Model Performance

| Model | Accuracy | Balanced Acc | F1-Macro |
|---|---|---|---|
| SVM (CalibratedClassifierCV) | 98.51% | 98.31% | 98.09% |
| Logistic Regression | 98.51% | 98.76% | 98.11% |
| Random Forest | 97.76% | 96.90% | 97.11% |

**SVM per-class:**
```
              precision  recall  f1-score  support
safe            0.965   0.979     0.972      142
vishing         0.992   0.987     0.990      394
accuracy                          0.985      536
```

### Neural Network Architecture
```
Input: shape=(1,) dtype=tf.string
  → TextVectorization (character-level, max_tokens=2000, seq_len=300)
  → Embedding (input_dim=2000, output_dim=64)
  → Conv1D (128 filters, kernel=5, activation=relu)
  → GlobalMaxPooling1D
  → Dropout(0.3)
  → Dense(64, relu)
  → Dropout(0.2)
  → Dense(1, sigmoid)

Optimizer: Adam(lr=1e-3)
Loss: binary_crossentropy
Class weights: {safe: 1.581, vishing: 0.731}
Early stopping: patience=3, restore_best_weights=True
```

### Inference Logic
```python
# Classical models (SVM, LR, RF)
label      = model.predict([text])[0]            # "vishing" or "safe"
confidence = float(np.max(model.predict_proba([text])))

# Neural network
prob  = float(nn_model.predict(tf.constant([text])).reshape(-1)[0])
label = "vishing" if prob >= 0.5 else "safe"

# Explainability (SVM + LR only)
# TF-IDF coef_[0] from pipeline → top 5 by absolute weight → bar chart
```

### Evidence Quality Check
- Min 5 words → else INCONCLUSIVE
- Min 70% confidence → else INCONCLUSIVE

---

## Audio Pipeline

```
User (mic or file upload)
       ↓
streamlit-audiorecorder OR st.file_uploader
       ↓
audio bytes (.wav / .mp3 / .m4a / .ogg / .flac)
       ↓
tempfile written to disk
       ↓
Whisper base model → transcribe(fp16=False)
       ↓
tempfile deleted immediately
       ↓
transcript string → sanitize_input()
       ↓
ML inference → hybrid analysis → result
```

**Whisper model:** `base` (≈140MB, downloads automatically)
**Install:** `pip install openai-whisper` + ffmpeg on system PATH

---

## Security Features

| Feature | Implementation |
|---|---|
| Password hashing | bcrypt rounds=12 |
| Brute-force lockout | 5 failed attempts → 15 min lockout (Supabase) |
| Remaining attempts display | Shown after each failed login |
| Input sanitization | HTML tag stripping + max 10,000 chars |
| Username validation | Regex alphanumeric + underscore, 3–32 chars |
| Rate limiting | 30 scans/hour per user, visual progress bar |
| Audit logging | Every scan logged with model, verdict, confidence |
| Audio cleanup | Temp files deleted immediately after transcription |
| Secrets management | `.streamlit/secrets.toml` (gitignored) |
| XSS prevention | `html.unescape` + tag stripping |
| Local LLM | Ollama runs locally — no transcripts sent externally |

---

## Supabase Setup

**Tables:**
- `users` — id, username (UNIQUE), password_hash, role, created_at, last_login
- `login_attempts` — id, username, success, attempted_at
- `audit_log` — id, username, input_length, input_mode, model_used, verdict, confidence, analyzed_at
- `rate_limit` — id, username, action, occurred_at

**Config:** `.streamlit/secrets.toml`
```toml
[supabase]
url = "https://your-project.supabase.co"
key = "your-anon-key"
```

---

## UI / Design System

**Theme:** Dark cyberpunk / military-grade security aesthetic
**No emojis** anywhere in the UI

**Fonts:**
- `Orbitron` — headings, logo, buttons, badges
- `Rajdhani` — body text, labels, descriptions
- `Share Tech Mono` — monospace data, metadata, tech labels

**Color Palette:**
| Variable | Hex | Usage |
|---|---|---|
| `--bg` | `#04080f` | Deep navy background |
| `--c1` | `#08111c` | Card background |
| `--c2` | `#0b1825` | Nested card |
| `--red` | `#e8203c` | Threat / danger |
| `--green` | `#00e87a` | Safe / success |
| `--blue` | `#00aaff` | Accent / interactive |
| `--amber` | `#f0a800` | Warning / inconclusive |
| `--text` | `#d8eaf8` | Primary text |
| `--muted` | `#4a7090` | Secondary text |
| `--border` | `#112233` | Borders |

**Phase 2 UI additions:**
- `.ai-card` — gradient card with blue-purple top border for AI analysis
- `.tactic-chip` + `.tc-*` — color-coded chips for each social engineering tactic
- `.rag-card` + `.rag-match` — amber-themed RAG similarity results
- `.src-badge` — "ML ONLY" / "HYBRID (ML + AI)" source indicator
- `.divg-card` — amber warning for ML vs LLM divergence

---

## Dependencies

### Core (Phase 1)
```
streamlit, supabase, bcrypt, joblib, numpy, tensorflow, keras,
scikit-learn, pandas, matplotlib, nltk, openai-whisper,
streamlit-audiorecorder, ffmpeg
```

### Phase 2 Additions
```
crewai>=0.28.0           ← Multi-agent framework
langchain>=0.2.0         ← LLM abstraction layer
langchain-community>=0.2.0
langchain-ollama         ← Ollama LLM integration (replaces deprecated community)
chromadb>=0.5.0          ← Vector database for RAG
sentence-transformers>=3.0.0  ← Embedding model (all-MiniLM-L6-v2)
ollama>=0.2.0            ← Ollama Python client
```

### System Requirements
- **Ollama**: Download from https://ollama.com (runs LLMs locally)
- **ffmpeg**: Required for Whisper audio processing
- **Model**: `ollama pull llama3.2:3b` (~2GB, runs on any machine with 4GB+ RAM)

---

## Key Design Decisions

### Why a Hybrid ML + LLM cascade instead of LLM-only?
- ML inference is <100ms. LLM inference is 30-90 seconds for the full crew.
- For clearly benign calls (score < 0.45), running the LLM wastes resources.
- ML provides a numerical score and keyword list as concrete evidence for the LLM.
- ML models have 98.5% accuracy — they are not a bottleneck.

### Why CrewAI multi-agent instead of a single LLM call?
- A single prompt gives one opinion. Multi-agent forces self-validation.
- Agent A flags unreliable ML scores. Agent B independently checks patterns.
- Agent C catches soft psychological signals that TF-IDF misses.
- Reduces false positives and produces richer explanations.

### Why Ollama instead of OpenAI/Anthropic API?
- No API cost for a student FYP
- Data stays local — no call transcripts sent to external servers
- Works offline
- Examiner-impressive: "We run everything locally with no external dependencies"

### Why ChromaDB instead of keyword search?
- Semantic similarity — matches script *structure* even without exact keywords
- Scales to thousands of samples without slowing down
- Adds a "Prior Precedent" dimension that pure ML cannot provide

---

## How to Run

```bash
# 1. Start Ollama (if not already running)
ollama serve
ollama pull llama3.2:3b

# 2. Activate venv and run
cd d:\FYP1\VishingDetection
.venv\Scripts\activate
streamlit run app/main.py
```

App opens at **http://localhost:8501**

---

## Known Issues / Notes

- `users.db` (old SQLite) still exists in root — safe to delete
- `layout="centered"` in page config is critical for login card centering
- Whisper `fp16=False` is required on Windows/CPU
- `streamlit-audiorecorder` requires HTTPS in production for mic access
- HuggingFace cache redirected to `.hf_cache/` in project dir (C: drive space workaround)
- First hybrid analysis takes ~30-90s as 4 LLM agents reason sequentially
- If Ollama is down, system gracefully falls back to ML-only mode with info box
- `llama3.2:3b` is used for prototyping — switch to `llama3.3:70b` for best quality

---

## Git Commit (Phase 2)

```
feat(phase2): add hybrid ML + LLM + CrewAI + RAG architecture

- Add hybrid_engine.py: ML → RAG → CrewAI orchestration with threshold gate
- Add rag_module.py: ChromaDB scam library with 1,266 indexed vishing transcripts
- Add llm_config.py: Ollama LLM config with health checks (langchain-ollama)
- Add agents/crew.py: CrewAI crew assembly (4 agents, sequential process)
- Add agents/agent_definitions.py: Technical Auditor, Pattern Detective,
  Psychology Profiler, Safety Guardian
- Update streamlit_app.py: AI analysis panel, tactic chips, RAG similarity
  matches, source badges, divergence warnings, hybrid analysis flow
- Update main.py: RAG startup init, 3 new session state keys
- Update requirements.txt: crewai, chromadb, sentence-transformers, ollama
- Update hero section + stats to reflect v2.0 hybrid system
- Update footer to SHIELDGUARD v2.0 with full tech stack
```
