# ShieldGuard — Complete System Context
> **Version:** 3.7 - SVM-Only Production Deployment
> **Project:** Vishing Detection System using ML, NLP, LLM & Multi-Agent AI
> **Type:** FYP — Cybersecurity
> **Status:** IMPLEMENTED — Phase 1 (SVM v3) + Phase 2 (LLM + RAG + Groq API) + Phase 3 (React + FastAPI) + Phase 4 (Admin Analytics) + Phase 5 (Research-Backed Literature Alignment) + Phase 6 (SVM-Only Production Deployment)

---

## Changelog

### v3.7 — 2026-05-12 — SVM-Only Production Deployment

**Production Model Simplification:**
- Standardized the deployed application on one final model: `models/svm_model.pkl`.
- Moved non-production artifacts (`neural_network.keras`, `svm_model_v2.pkl`) into `models/legacy/` alongside LR/RF/NN baseline models.
- Updated `backend/models_loader.py` so the production backend loads only SVM v3 and no longer requires LR, RF, or NN artifacts at startup.
- Removed the advanced model-selection UI from the React dashboard and legacy Streamlit interface.
- Documentation now states the final model decision clearly: LR, RF, and NN were evaluated experimentally, but SVM v3 was selected because it provides the best balance of accuracy, speed, calibrated probability output, and explainability.

### v3.6 — 2026-05-12 — Research Evidence Map & Literature Review Alignment

**Chapter 2 Research Upgrade:**
- Added a curated 2023-2026 literature evidence map focused on vishing, voice phishing, AI/ML detection, audio-transcript pipelines, LLM reasoning, RAG, explainability, and adversarial robustness.
- Prioritized papers that directly support ShieldGuard's architecture: speech-to-text input, transcript classification, TF-IDF/SVM baseline strength, deep learning alternatives, RAG-assisted context retrieval, LLM review, and user-facing explanations.
- Removed duplicated research positioning by grouping studies by their role in the system rather than listing similar papers repeatedly.
- Added a clear "How ShieldGuard maps to the literature" subsection so examiners can immediately see why each research stream matters.
- Wording is intentionally plain and defense-ready: technical enough for high marks, readable enough for non-specialist evaluators.

### v3.5 — 2026-05-06 — Admin Analytics Dashboard

**New Feature: Analytics Dashboard (`/admin`):**
- Added `AdminDashboard.jsx` — a dedicated analytics page accessible from the header navigation.
- Displays four KPI cards: Total Analyses, Registered Users, Vishing Rate, Average Confidence.
- Verdict Breakdown — donut chart (Vishing / Safe / Inconclusive) powered by Recharts.
- Detection Trend — 7-day stacked area chart showing daily vishing vs safe vs total.
- Confidence Distribution — histogram bar chart color-coded by risk level.
- Top Users — ranked progress-bar leaderboard of most active users.
- System Status bar — live component status (ML Engine, RAG, Groq LLM, Supabase).
- Data sourced from existing Supabase `audit_log` table via new `GET /api/analytics` endpoint.
- Styled to match existing dark glassmorphism theme — no emojis, clean tech-startup aesthetic.

**Bug Fix: CSS Text Overflow:**
- Added `overflow-wrap: break-word`, `word-break: break-word`, and `overflow: hidden` to `.sg-card` in `index.css`.
- Prevents long unbroken strings from overflowing card boundaries across all UI components.

**Frontend Navigation:**
- Added "Analytics" button to the header navbar linking to `/admin`.
- Updated `App.jsx` router with protected `/admin` route.
- Updated header system status sub-text from `SVM v2` to `SVM v3 · Groq · RAG`.

**Impact on ML accuracy:** Zero. Read-only analytics feature.

### v3.4 — 2026-05-05 — Groq Cloud API Migration (LLM + Whisper)

**LLM Migration (Ollama → Groq API):**
- Replaced local Ollama (`llama3.2:3b`) with Groq Cloud API (`llama-3.3-70b-versatile`).
- 70B parameter model provides significantly better reasoning, JSON compliance, and scam analysis accuracy.
- Inference speed improved from 15-30s per hybrid analysis to < 2 seconds via Groq's LPU hardware.
- Updated `llm_config.py`: Removed `OllamaLLM` / `langchain_ollama` imports, replaced with `groq` SDK singleton.
- Updated `agents/crew.py`: Replaced `_ollama_generate()` HTTP calls with `_groq_generate()` using `groq.chat.completions.create()`.
- All prompts (Forensic Analyst, Safety Guardian) and output parsers remain **byte-for-byte identical** — zero impact on analysis logic.

**Whisper ASR Migration (local → Groq API):**
- Replaced local PyTorch Whisper (`base` model, ~74M params) with Groq's `whisper-large-v3-turbo` API.
- Large-v3-turbo is the most accurate Whisper variant available — significantly better for accented speech and noisy audio.
- Removed `load_whisper()` from `models_loader.py`. No local PyTorch model loading required.
- Updated `/api/transcribe` endpoint in `main.py` to send audio to Groq API.

**Infrastructure changes:**
- Added `GROQ_API_KEY` to `backend/.env` (gitignored).
- Ollama is no longer a prerequisite — system runs entirely without local LLM/ASR servers.
- Updated health endpoints (`/api/health`, `/api/health_detailed`) to check Groq API status.
- Frontend labels updated: footer tags, diagnostics, dashboard messages.

**Impact on ML accuracy:** Zero. SVM v3, ChromaDB RAG, and TF-IDF XAI are unchanged.

### v3.3 - 2026-04-29 - ML v3 Limited-Dataset Retraining

**ML training changes:**
- Added `notebooks/03_limited_dataset_svm_training.py` with `CELL 1`, `CELL 2`, etc. comments so each section can be copied directly into Jupyter Notebook cells.
- Retrained the active SVM with a leakage-safe workflow: split real data first, augment only the training split, add hard-negative safe examples, add hard-positive vishing examples, tune the threshold on validation data, and evaluate once on the clean held-out test set.
- Promoted the retrained model to `models/svm_model.pkl`.
- Saved reproducibility metadata in `models/svm_model_metadata.json` and detailed metrics in `docs/ml_training_v3_metrics.json`.
- Updated the backend production threshold to `VISHING_THRESHOLD = 0.80` and aligned the benchmark endpoint threshold metadata.

**Verified metrics:**
- Clean held-out test accuracy: **98.88%**
- Clean held-out macro F1: **98.69%**
- Clean held-out balanced accuracy: **99.20%**
- Clean test confusion matrix: safe `108/108` correct, vishing `245/249` correct.
- Targeted sanity checks passed for legitimate dentist, bank callback, delivery reminder, OTP threat, legal transfer, and remote-access scam examples.
- CLI benchmark after retraining: **100%** (10/10 labelled samples).

### v3.2 — 2026-04-23 — Precision Thresholding + Speed Optimisation

**Precision Hardening (research-backed):**
- Added `VISHING_THRESHOLD = 0.75`: Decision boundary raised from 0.50 to 0.75 to reduce False Positives / alert fatigue. Justified by Provost & Fawcett (2001) cost-sensitive classification framework.
- Added `REJECT_THRESHOLD = 0.80` (asymmetric): Applied only on vishing predictions via Chow's Classification-with-Reject-Option (C.K. Chow, 1970). If `0.75 ≤ P(vishing) < 0.80`, verdict is `INCONCLUSIVE` and escalated to LLM. Safe predictions pass through without reject gating (Bartlett & Wegkamp, 2008).
- Added `preprocess_text()` to `inference.py`: Mirrors training pipeline (`normalize_english()` → `lemmatize_text()`). Fixes critical train/inference preprocessing mismatch that caused 97.8% false positive rate on safe calls.
- Expanded `VISHING_PATTERNS` from 14 → 30 regex patterns: Added tech support scam, crypto/investment, government impersonation, and isolation/secrecy categories.

**Speed Optimisation:**
- Replaced CrewAI framework with **direct async Ollama HTTP calls** via `httpx`. Eliminates ~5-10s framework overhead per analysis.
- Consolidated 4 agents → 2 prompts (Forensic Analyst + Safety Guardian). Reduces LLM round-trips from 4 → 2.
- Added `num_predict: 512` token cap in Ollama presets. Prevents verbose LLM output.
- Estimated improvement: **60-90s → 15-30s** per hybrid analysis.

**UI Hardening:**
- Fixed RiskGauge: Now verdict-aware. Safe verdicts show "LOW RISK", inconclusive shows "CAUTION" instead of incorrectly showing "HIGH RISK".
- Added duplicate submission guard in `useAnalysis.js`: `if (get().loading) return null` prevents multiple concurrent analyses.
- Analyze button shows "Analyzing..." and disables during processing.
- Fixed system status hook: Changed `/api/health` → `/api/health_detailed` so the header correctly shows "SYSTEM ONLINE".
- Updated stats strip: `4 AI Agents` → `2 AI Agents`.

**Testing & Diagnostics:**
- Added `tests/benchmark.py`: CLI benchmark (10 labelled samples, measures accuracy + latency).
- Added `GET /api/benchmark` endpoint: Live ML benchmark accessible from the dashboard.
- Added `SystemDiagnostics.jsx`: Collapsible diagnostics panel in the dashboard with per-sample pass/fail table, metric cards, and citation badges.

**Verified metrics (v3.2 benchmark):**
- ML Accuracy: **90%** (9/10 correct, 1 false positive on dentist call — mitigated by hybrid LLM layer)
- ML Latency: **2.0ms avg** (well within 200ms target)
- Status: **READY FOR USER TESTING**

### v3.1 — 2026-04-22 — ML Model Upgrade

**What changed:**
- Retrained SVM classifier with 5 improvements (see ML Models section below).
- F1-macro improved from **0.9809 → 0.9936** (+1.27%). Accuracy 98.5% → 99.4%.
- Promoted `svm_model_v2.pkl` to `models/svm_model.pkl` (production).
- Moved all v1 models to `models/legacy/` (LR, RF, NN h5, vectorizer).
- Updated `backend/inference.py`: `get_explanation` now supports both v1 (single TF-IDF) and v2 (FeatureUnion) pipeline structures automatically.
- Updated `backend/models_loader.py`: vectorizer is now optional because the SVM pipeline embeds its own FeatureUnion.
- Added `notebooks/02_improved_ml_training.py`: complete v2 training script with cell-by-cell Jupyter comments.

### v3.0 — Earlier — React + FastAPI Migration
- Decoupled Streamlit monolith into React frontend + FastAPI backend.
- Added JWT authentication, Supabase persistence, multi-agent LLM reasoning.

---

## Project Overview

**ShieldGuard** is a web-based vishing (voice phishing) detection system. Users can record a suspicious call, upload an audio file, or paste a transcript — the system classifies it as **vishing** or **safe** using a hybrid cascade of ML models, RAG pattern matching, and LLM-powered multi-agent reasoning.

The system has two frontends:
- **Legacy:** Streamlit (monolithic, in `app/`)
- **Current:** React + Tailwind CSS (decoupled, in `frontend/`) with FastAPI backend (`backend/`)

---

## Research Evidence Map (2023-2026)

This section aligns ShieldGuard with the strongest recent research for a Chapter 2 literature review. The focus is not "AI for phishing" in general; it is specifically the research path that justifies a practical vishing detector: audio capture, transcription, text classification, retrieval of known scam patterns, LLM-assisted reasoning, and explainable user warnings.

### Core Vishing and Voice-Phishing Papers

| Year | Paper | Why it matters for ShieldGuard | Link |
|---|---|---|---|
| 2026 | Automatically Detecting Voice Phishing: A Large Audio Model Approach | Shows that modern voice-phishing detection is moving beyond keyword rules into large audio models and deep learning. This supports ShieldGuard's direction of treating vishing as an AI-supported speech security problem, not only a text-filtering task. | https://doi.org/10.25300/MISQ/2025/19532 |
| 2026 | A Real-Time AI-based Framework for Vishing Detection | Directly supports ShieldGuard's goal of fast, user-facing vishing analysis. The paper frames vishing defense as a real-time assistant that monitors spoken communication and explains risk while the user can still act. | https://www.medien.ifi.lmu.de/pubdb/publications/pub/jia2026esorics/jia2026esorics.pdf |
| 2025 | Vishing: Detecting Social Engineering in Spoken Communication — A First Survey & Urgent Roadmap | Strong foundation for Chapter 2 because it explains why vishing is different from normal phishing: persuasion, authority, urgency, deception, and voice interaction must be interpreted together. | https://www.sciencedirect.com/science/article/pii/S0885230825000270 |
| 2025 | A Multimodal Voice Phishing Detection System Integrating Text and Audio Analysis | Closely matches ShieldGuard's pipeline because it combines speech-to-text, text classification, and audio cues. It supports the idea that transcript analysis and audio processing should work together in real deployments. | https://www.mdpi.com/2076-3417/15/20/11170 |
| 2025 | Detecting Voice Phishing with Precision: Fine-Tuning Small Language Models | Supports the LLM side of ShieldGuard. It shows that Llama-family models can be adapted for voice-phishing judgment when guided by expert criteria, which is similar to ShieldGuard's forensic and safety-review prompts. | https://arxiv.org/abs/2506.06180 |
| 2025 | Talking Like a Phisher: LLM-Based Attacks on Voice Phishing Classifiers | Important for limitations and future work. It shows that LLM-generated scam scripts can evade ML classifiers, which justifies ShieldGuard's layered design instead of trusting one model blindly. | https://arxiv.org/abs/2507.16291 |
| 2024 | Korean Voice Phishing Detection Applying NER With Key Tags and Sentence-Level N-Gram | Supports feature engineering for transcript-based vishing detection. Named entities, key tags, and sentence-level n-grams are conceptually close to ShieldGuard's phrase indicators and TF-IDF features. | https://ieeexplore.ieee.org/document/10496052/ |
| 2023 | Attention-Based 1D CNN-BiLSTM Hybrid Model Enhanced with FastText Word Embedding for Korean Voice Phishing Detection | Useful comparison against ShieldGuard's SVM. It shows that deep learning with attention can capture sequence patterns, while ShieldGuard chooses a faster and more explainable ML-first approach for real-time use. | https://www.mdpi.com/2227-7390/11/14/3217 |
| 2023 | Real-Time Korean Voice Phishing Detection Based on Machine Learning Approaches | Strong baseline reference for real-time ML detection. It supports the argument that classical ML can be effective and fast for vishing transcripts, especially when deployment speed matters. | https://doi.org/10.1007/s12652-021-03587-x |

### Supporting AI, RAG, and Explainability Papers

| Year | Paper | Why it matters for ShieldGuard | Link |
|---|---|---|---|
| 2026 | User-Centric Phishing Detection: A RAG and LLM-Based Approach | Supports ShieldGuard's RAG layer: retrieve similar known scam cases, then use an LLM to explain the risk in user-friendly language. | https://arxiv.org/abs/2601.21261 |
| 2025 | EXPLICATE: Enhancing Phishing Detection through Explainable AI and LLM-Powered Interpretability | Supports ShieldGuard's XAI panels, highlighted transcript, tactic labels, and natural-language explanations. It is especially useful for arguing that detection systems must explain why something is suspicious. | https://arxiv.org/abs/2503.20796 |
| 2024 | Enhancing Phishing Email Detection with Context-Augmented Open Large Language Models | Although email-focused, it supports context-augmented LLM detection. This is relevant to ShieldGuard's use of retrieved scam patterns before LLM review. | https://journals.hs-offenburg.de/index.php/urai/article/view/23 |
| 2024 | Digital Deception: Generative Artificial Intelligence in Social Engineering and Phishing | Useful background for the threat landscape. It explains why generative AI increases the scale and realism of social engineering attacks, including vishing. | https://link.springer.com/article/10.1007/s10462-024-10973-2 |
| 2024 | PITCH: AI-assisted Tagging of Deepfake Audio Calls using Challenge-Response | Supports the audio-risk side of the literature review, especially when discussing deepfake or synthetic-voice calls as an extension of vishing defense. | https://arxiv.org/abs/2402.18085 |

### How ShieldGuard Maps to the Literature

| Literature theme | What recent research says | ShieldGuard implementation |
|---|---|---|
| Real-time vishing protection | Detection must be fast enough to warn users during or immediately after a suspicious call. | FastAPI backend, lightweight SVM v3 inference, and dashboard feedback designed for quick analysis. |
| Speech-to-text pipeline | Voice phishing can be converted into transcripts so NLP models can analyze scam language. | Audio recording/upload is transcribed by Groq Whisper `large-v3-turbo` before classification. |
| Classical ML baseline | SVM, n-gram, and feature-engineering methods remain valuable when speed, transparency, and small datasets matter. | Calibrated LinearSVC with char+word TF-IDF FeatureUnion achieves 98.88% clean held-out accuracy. |
| Deep learning alternatives | CNN, BiLSTM, attention, and large audio models can learn richer sequential and acoustic patterns. | NN was evaluated experimentally, but the deployed app keeps SVM v3 for speed, stability, and explainability; multimodal audio features remain future work. |
| RAG context retrieval | Similar known cases improve reasoning and make AI explanations more grounded. | ChromaDB retrieves top similar scam transcripts before LLM review. |
| LLM-assisted reasoning | LLMs can classify tactics, summarize evidence, and provide human-readable warnings. | Groq Llama 3.3 70B produces forensic analysis, scam type, tactics, and action steps. |
| Explainable AI | Users need to understand the warning, not only receive a label. | Top TF-IDF keywords, highlighted transcript, tactic chips, similar cases, and action steps are shown in the UI. |
| Adversarial robustness | LLM-generated vishing scripts can bypass simple classifiers. | ML-first decision, RAG evidence, LLM advisory review, divergence detection, and inconclusive states reduce overreliance on one model. |

### Chapter 2 Positioning Statement

ShieldGuard contributes a practical hybrid architecture for vishing detection by combining the speed and explainability of classical ML with the contextual reasoning of RAG and LLMs. Recent studies show that vishing is not only a text classification problem; it is a spoken social-engineering problem involving urgency, authority, secrecy, financial pressure, and increasingly AI-generated speech. Therefore, ShieldGuard is designed as a layered defense: Whisper converts speech to text, SVM provides fast risk scoring, ChromaDB retrieves similar scam patterns, and the LLM converts technical evidence into a clear warning and safe action plan for the user.

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
│  Engine:  FeatureUnion (char_wb + word TF-IDF) + SVM v3         │
│  Preprocessing:  normalize_english() → lemmatize_text()         │
│  Speed:   ~2ms (fast, deterministic)                            │
│  Thresholds:                                                    │
│    VISHING_THRESHOLD = 0.80 (tuned on v3 validation split)     │
│    REJECT_THRESHOLD  = 0.80, asymmetric (Chow, 1970)           │
│  Output:  ml_score, ml_label, top_keywords                     │
│                                                                 │
│  if ml_label = "safe"     → pass through (low-risk decision)   │
│  if ml_label = "vishing" and conf < 0.80 → INCONCLUSIVE        │
│  if ml_score ≥ 0.45       → proceed to Layer 2 (hybrid)        │
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
│  LAYER 3 — GROQ CLOUD LLM  (Phase 2, v3.4)                      │
│                                                                 │
│  LLM:     Llama 3.3 70B via Groq API (cloud, free tier)          │
│  Method:  groq SDK → chat.completions.create()                   │
│  Token:   max_tokens = 512 (capped output)                       │
│                                                                 │
│  Prompt 1 — Forensic Analyst                                    │
│    → Validates ML flag + classifies scam type                   │
│                                                                 │
│  Prompt 2 — Safety Guardian                                     │
│    → Detects tactics + final verdict + action steps             │
│                                                                 │
│  Total: 2 LLM calls (down from 4 in v3.0/v3.1)                 │
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
| NLP Vectorizer | TF-IDF FeatureUnion (char_wb 3-5 + word 1-2) | — |
| Lemmatizer | NLTK WordNetLemmatizer | — |
| Speech-to-Text | OpenAI Whisper | large-v3-turbo (via Groq API) |
| RAG Database | ChromaDB | ≥0.5.0 |
| RAG Embeddings | sentence-transformers | all-MiniLM-L6-v2 |
| Agent Framework | Direct async HTTP (Groq SDK) | replaced Ollama HTTP in v3.4 |
| LLM Backend | Groq Cloud API | llama-3.3-70b-versatile |
| LLM Interface | groq Python SDK → chat.completions | replaced Ollama/LangChain in v3.4 |
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
| LLM Server | Groq Cloud API (llama-3.3-70b-versatile) |
| ASR Server | Groq Cloud API (whisper-large-v3-turbo) |
| Database | Supabase (cloud PostgreSQL) |
| Models Storage | Local filesystem (`models/`) |
| RAG Storage | Local filesystem (`data/scam_library/`) |
| Audio Engine | ffmpeg (local, for format conversion) |

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
- **ML Model:** The deployed classifier is SVM v3 (`models/svm_model.pkl`); TF-IDF feature extraction and ChromaDB retrieval run locally.
- **LLM + Whisper:** Transcripts are sent to Groq Cloud API for analysis. Groq's API terms state they do not train on API data.
- **Architecture supports local fallback:** The system can be reconfigured to use local Ollama for air-gapped/enterprise deployments
- **Credential Storage:** Supabase keys and Groq API key in `.env` file (gitignored)

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
| POST | `/api/transcribe` | Upload audio → Groq Whisper transcription |
| GET | `/api/history` | Get last N scan results from Supabase |
| GET | `/api/analytics` | Aggregated dashboard stats (verdict distribution, trend, confidence, top users) |
| GET | `/api/health` | System health check (models, Groq, ChromaDB, Supabase) |
| GET | `/api/health_detailed` | Detailed component-by-component health with version info |
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
- **Dataset:** 1,781 cleaned/deduplicated labeled call transcripts from `data/english_dataset_final_v2.csv`
- **Split:** Real data split into train/validation/test before any augmentation
- **Labels:** "vishing" and "safe"
- **Preprocessing (v3):** ASCII normalization → NLTK Lemmatization → FeatureUnion TF-IDF

### Active Model (v3 - Production)
| Model | File | Accuracy | F1-macro | Note |
|---|---|---|---|---|
| SVM v3 | `models/svm_model.pkl` | **98.88%** | **0.9869** | Final deployed classifier. FeatureUnion (char+word) + calibrated LinearSVC (best C=2.0, threshold=0.80). |

### Model Selection Rationale
- LR, RF, and NN were evaluated during experimentation and retained as legacy/reference artifacts.
- SVM v3 was selected for deployment because it provides the best practical balance of clean-test performance, millisecond-level inference, calibrated probability output, and transparent TF-IDF explanations.
- Keeping a single production model reduces startup dependencies, avoids model-selection confusion for users, and makes Chapter 4 evaluation easier to defend.

### Legacy Models (v1 — Reference Only)
Moved to `models/legacy/` for documentation, comparison, and examiner discussion. These artifacts are not loaded by the deployed backend.
| Model | File | Accuracy | Note |
|---|---|---|---|
| SVM v1 | `models/legacy/svm_model_v1.pkl` | 98.5% | Single char_wb TF-IDF + CalibratedLinearSVC |
| Logistic Regression | `models/legacy/logistic_regression_model_v1.pkl` | ~98.5% | — |
| Random Forest | `models/legacy/rf_model_v1.pkl` | ~97.8% | — |
| Vectorizer | `models/legacy/vectorizer_v1.pkl` | — | Standalone TF-IDF (no longer needed in v2) |
| Neural Network | `models/legacy/neural_network.keras`, `models/legacy/neural_network_v1.h5` | ~98.7% | Experimental deep-learning baseline, not deployed |
| SVM v2 | `models/legacy/svm_model_v2.pkl` | reference | Previous SVM iteration before v3 |

### v3 Training Improvements
| Improvement | Detail | Result |
|---|---|---|
| Leakage-safe split | Split real data before augmentation | Clean validation/test metrics |
| Train-only EDA | Synonym replacement only on training safe class | Better safe recall without contaminating evaluation |
| Hard examples | Added safe callback/reminder examples and vishing pressure scripts to train only | Reduced false positives on legitimate calls |
| FeatureUnion | char_wb TF-IDF + word TF-IDF | Captures spelling patterns and semantic phrases |
| GridSearchCV | Stratified CV over SVM C values | Best C=2.0 selected automatically |

### Inference Interface
- **SVM v3:** `run_inference_detailed()` returns label, confidence, `vishing_probability`, `safe_probability`, and ML risk band
  - The pipeline internally applies FeatureUnion vectorization — no separate vectorizer call needed.
- **Legacy NN/LR/RF:** Kept only for report comparison; not loaded by the production app.

### Explainability (XAI)
- **SVM:** TF-IDF coefficient extraction via `get_explanation()` in `inference.py`
  - FeatureUnion-aware: automatically detects the active pipeline structure
  - Feature names prefixed with `[char]` or `[word]` to indicate which vectorizer contributed
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

## AI Review System (Groq Cloud API)

### Prompts
| Prompt | Role | Output |
|---|---|---|
| Forensic Analyst | Reviews ML output with transcript and RAG context | scam type, evidence, ML alignment |
| Safety Guardian | Produces user-facing explanation and next steps | verdict, tactics, explanation, action steps |

### Configuration
- **LLM:** `llama-3.3-70b-versatile` through Groq Cloud API
- **Process:** `groq` Python SDK → `chat.completions.create()`
- **Guardrail:** The LLM is advisory and cannot silently replace strong ML evidence.
- **Fallback:** If Groq API is offline, returns ML-only result with graceful message

---

## Vishing Detection Patterns

30 regex patterns detect suspicious phrases:
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
│   ├── models_loader.py          ← Production SVM model loading
│   ├── inference.py              ← run_inference, get_explanation, detect_suspicious_phrases
│   ├── hybrid_engine.py          ← ML→RAG→Groq cascade orchestrator
│   ├── rag_module.py             ← ChromaDB scam library + similarity search
│   ├── llm_config.py             ← Groq API configuration (SDK singleton)
│   ├── database.py               ← Supabase client + all DB functions
│   ├── auth.py                   ← Password hashing, validation, sanitization
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent_definitions.py  ← legacy agent definitions kept for reference
│   │   └── crew.py               ← Groq API prompts and output parsing
│   ├── requirements.txt
│   └── .env                      ← Environment variables (gitignored)
│
├── frontend/                     ← React frontend (current)
│   ├── index.html                ← Google Fonts, meta tags
│   ├── vite.config.js            ← Vite + Tailwind + API proxy to :8000
│   ├── package.json
│   └── src/
│       ├── App.jsx               ← Router: /login, /app, /admin (protected)
│       ├── main.jsx              ← React DOM mount
│       ├── index.css             ← Tailwind + design system (CSS variables, keyframes)
│       ├── api/client.js         ← Axios with JWT interceptor
│       ├── hooks/
│       │   ├── useAuth.js        ← Zustand: login, register, logout, token
│       │   ├── useAnalysis.js    ← Zustand: analyze with progress tracking
│       │   └── useTranscribe.js  ← Zustand: audio transcription
│       ├── pages/
│       │   ├── LoginPage.jsx     ← Login/Register with lockout display
│       │   ├── MainDashboard.jsx ← Full analysis dashboard
│       │   └── AdminDashboard.jsx ← Analytics dashboard (charts, KPIs, user leaderboard)
│       └── components/
│           ├── layout/           ← Header (logo, online badge, analytics nav), Footer
│           ├── auth/             ← LoginForm, RegisterForm
│           ├── input/            ← InputTabs, AudioRecorder, AudioUploader, TranscriptInput
│           ├── results/          ← VerdictCard, RiskGauge, ConfidenceBar, PhraseChips,
│           │                       HighlightedTranscript, XAIPanel, AIAnalysisCard,
│           │                       TacticChips, RAGSimilarCases, ActionSteps,
│           │                       SafetyAdvice, DivergenceWarning
│           ├── dashboard/        ← HeroSection, StepGuide, RateLimitBar, ScanHistory
│           └── ui/               ← StatusBadge, InfoBox, WarnBox
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
├── models/                       ← Trained ML models
│   ├── svm_model.pkl             ← ACTIVE: final SVM v3 (FeatureUnion, C=2.0, threshold=0.80)
│   ├── svm_model_metadata.json   ← v3 training metrics and threshold metadata
│   └── legacy/                   ← experimental/reference models, not loaded in production
│       ├── svm_model_v1.pkl
│       ├── logistic_regression_model_v1.pkl
│       ├── rf_model_v1.pkl
│       ├── vectorizer_v1.pkl
│       ├── svm_model_v2.pkl
│       ├── neural_network.keras
│       └── neural_network_v1.h5
│
├── data/
│   ├── english_dataset_final_v2.csv  ← Production dataset (1,785 transcripts)
│   ├── scam_library/                 ← ChromaDB persistent storage
│   ├── archive/                      ← Old/intermediate datasets (gitignored)
│   └── raw/                          ← Raw audio & source data (gitignored)
│
├── docs/                         ← Documentation & reference files
│   ├── ml_training_v3_metrics.json ← v3 validation/test metrics
│   ├── supabase_schema.sql       ← Database schema
│   └── requirements_streamlit.txt ← Legacy Streamlit dependencies
│
├── notebooks/                    ← Training notebooks and scripts
│   ├── 01_baseline_text_classification.ipynb  ← v1 baseline (SVM/LR/RF/NN)
│   ├── 02_improved_ml_training.py             ← previous v2 training
│   ├── 03_limited_dataset_svm_training.py     ← v3 Jupyter-copy training script
│   ├── 02_prepare_korccvi.ipynb
│   ├── 03_prepare_kaggle_voice.ipynb
│   ├── 04_index_kaggle_audio.ipynb
│   ├── confusion_matrix_v2.png                ← v2 confusion matrix
│   ├── kfold_results_v2.png                   ← 5-fold CV chart
│   ├── gridsearch_c_f1_v2.png                 ← GridSearch C vs F1 chart
│   ├── evaluation.ipynb
│   └── test.ipynb
│
├── tests/                        ← Test files
│   ├── test_auth.py
│   ├── test_rag.py
│   └── test_groq.py              ← Groq API integration test (vishing + safe)
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
- Groq API key (free tier at https://console.groq.com)
- ffmpeg installed (for audio format conversion)

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
GROQ_API_KEY=your-groq-api-key
JWT_SECRET=your-secret-key
MODELS_DIR=../models
HF_CACHE_DIR=../.hf_cache
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Groq API Key (Required for Hybrid Analysis + Whisper)
1. Sign up at https://console.groq.com (free)
2. Create an API key
3. Add to `backend/.env` as `GROQ_API_KEY=gsk_...`

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
