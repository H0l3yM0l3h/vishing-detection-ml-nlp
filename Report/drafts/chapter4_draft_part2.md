## 4.4 Development — Version 1: Full-Stack Migration and Authentication

The first development iteration focused on migrating the system from the FYP1 Streamlit prototype to a full-stack architecture using React.js for the frontend and FastAPI for the backend. This migration was necessary because Streamlit, while effective for rapid prototyping, imposes limitations on user interface customisation, concurrent user handling, and deployment flexibility. FastAPI was selected as the backend framework due to its native support for asynchronous request handling, automatic API documentation via OpenAPI, and high throughput under concurrent loads — all of which are critical for a near-real-time detection system (Phang et al., 2024).

### 4.4.1 Backend Setup and Structure

The FastAPI backend is initialised in `main.py` with a lifespan context manager that loads the final production SVM model into memory at startup, ensuring zero-latency model loading during inference. Earlier LR, RF, and NN models are retained only as legacy experiment artefacts for comparison and examiner discussion; they are not required by the deployed application.

**Table 4.5: Backend File Structure**

| File | Responsibility |
| :--- | :--- |
| `main.py` | FastAPI application entry point. Defines all API routes, JWT helpers, and the lifespan loader. |
| `inference.py` | ML inference logic, text preprocessing, vishing pattern detection, and XAI explanation extraction. |
| `hybrid_engine.py` | Orchestrates the ML → RAG → LLM cascade with threshold gates and divergence detection. |
| `rag_module.py` | ChromaDB vector store management, scam library building, and semantic similarity queries. |
| `models_loader.py` | Loads the final production SVM v3 artefact used by the deployed app. |
| `database.py` | Supabase client for user management, login tracking, audit logging, and rate limiting. |
| `auth.py` | Password hashing (bcrypt), input sanitisation, and username/password validation rules. |
| `llm_config.py` | Ollama connectivity checks and LLM model configuration. |

### 4.4.2 Authentication and Security Controls

Unlike the FYP1 prototype which used lightweight Streamlit session-based authentication, Version 1 of FYP2 implements a stateless JWT (JSON Web Token) authentication system. This design choice aligns with OWASP recommendations for RESTful API security, where server-side session storage is replaced by cryptographically signed tokens that expire after 24 hours.

**Table 4.6: Security Controls Implemented**

| Control | Implementation | Justification |
| :--- | :--- | :--- |
| **JWT Authentication** | Tokens signed with HS256 algorithm, 24-hour expiry. | Stateless authentication reduces server-side session management overhead. |
| **Brute-Force Protection** | Account lockout after 5 failed attempts within 15 minutes. | Prevents credential stuffing attacks on user accounts. |
| **Rate Limiting** | Maximum 30 analyses per user per hour. | Prevents abuse of ML/LLM resources and mitigates denial-of-service risk. |
| **Input Sanitisation** | All user inputs stripped of HTML/script tags, truncated to safe lengths. | Prevents Cross-Site Scripting (XSS) and injection attacks. |
| **Password Hashing** | bcrypt with automatic salting. | Industry-standard one-way hashing prevents plaintext password exposure. |
| **CORS Policy** | Restricted to `localhost:5173` and `localhost:3000`. | Prevents unauthorised cross-origin API access from unknown domains. |
| **Audit Logging** | Every analysis event recorded to Supabase with username, model, verdict, confidence, and timestamp. | Supports accountability, forensic investigation, and compliance auditing. |

These controls directly address the CIA triad considerations established in Chapter 3: **Confidentiality** is maintained through JWT tokens, password hashing, and minimal logging of sensitive content. **Integrity** is ensured through input sanitisation, model artefact versioning, and the separation of training and inference data. **Availability** is protected through rate limiting, brute-force lockout, and graceful fallback when external services (Ollama, Supabase) are unavailable.

### 4.4.3 Frontend Dashboard

The React.js frontend was developed as a Single Page Application (SPA) using Vite as the build tool. The dashboard provides a modern, responsive interface where users can input transcript text, upload audio files for Whisper transcription, and view comprehensive SVM-based analysis results.

**[IMAGE PLACEHOLDER: Figure 4.2 — ShieldGuard Login Page]**
*(Instruction: Insert a screenshot of the login page showing the username/password fields and the ShieldGuard branding.)*

**[IMAGE PLACEHOLDER: Figure 4.3 — ShieldGuard Analysis Dashboard]**
*(Instruction: Insert a screenshot of the main dashboard showing the transcript input area, "Analyze" button, and the audio upload option.)*

**Table 4.7: Frontend File Structure**

| Directory / File | Description |
| :--- | :--- |
| `frontend/src/App.jsx` | Root application component with routing logic. |
| `frontend/src/pages/` | Page-level components (Login, Register, Dashboard, History). |
| `frontend/src/components/` | Reusable UI components (ResultCard, ConfidenceGauge, KeywordHighlight). |
| `frontend/src/api/` | API client functions for authentication, analysis, and health checks. |
| `frontend/src/hooks/` | Custom React hooks for authentication state and API calls. |
| `frontend/src/index.css` | Global stylesheet with ShieldGuard design system. |

## 4.5 Development — Version 2: ML Pipeline Hardening and Explainability

The second iteration focused on hardening the ML inference pipeline and integrating Explainable AI (XAI) features into the detection output.

### 4.5.1 Text Preprocessing Pipeline

A critical lesson from FYP1 was that the preprocessing applied during inference must exactly mirror the preprocessing applied during training. Any mismatch — even subtle differences in Unicode handling or lemmatization — causes the TF-IDF features to diverge from what the model learned, resulting in severe accuracy degradation. This phenomenon is documented in recent vishing detection literature as "train-deploy mismatch" (Ma et al., 2025).

The preprocessing pipeline in `inference.py` applies the following steps in sequence:

1. **Zero-width character removal** — Strips invisible Unicode artefacts (e.g., `\u200b`) that create inconsistent tokens.
2. **NFKC Unicode normalisation** — Converts all characters to a consistent Unicode form.
3. **Smart punctuation replacement** — Converts curly quotes and em-dashes to their ASCII equivalents.
4. **ASCII-safe encoding** — Removes non-ASCII characters to prevent encoding errors during model persistence.
5. **Whitespace normalisation and lowercasing** — Collapses repeated spaces and standardises casing.
6. **Lemmatization** — Applies WordNet lemmatization for both verbs and nouns to normalise word forms (e.g., "transferring" → "transfer", "accounts" → "account").

### 4.5.2 Research-Backed Threshold Configuration

The system implements a research-backed, asymmetric threshold design for classification decisions. This is a significant advancement over the default 0.50 probability threshold used in standard binary classifiers.

**Table 4.8: Threshold Configuration and Research Justification**

| Threshold | Value | Purpose | Research Basis |
| :--- | :--- | :--- | :--- |
| **VISHING_THRESHOLD** | 0.80 | Model must achieve ≥80% vishing probability to emit a "vishing" label. | Provost & Fawcett (2001): shifting the decision boundary reduces false positives and minimises alert fatigue in security-critical applications. |
| **REJECT_THRESHOLD** | 0.80 | Vishing predictions below 80% confidence are marked INCONCLUSIVE and escalated. | Chow's Classification-with-Reject-Option rule (1970): uncertain predictions should be deferred rather than forced into a binary decision. |
| **STRONG_SAFE_THRESHOLD** | 0.20 | Vishing probability ≤20% is classified as definitively safe; LLM review is skipped. | Reduces unnecessary LLM invocations for clearly benign transcripts. |
| **STRONG_VISHING_THRESHOLD** | 0.85 | Vishing probability ≥85% is classified as high-risk. | Supports risk-band stratification for the dashboard UI. |

This asymmetric design means the reject threshold is only applied when the model predicts "vishing". Safe predictions pass through directly because the consequence of a false negative (missing a safe call) is far less severe than the consequence of a false positive (falsely alarming a legitimate call). This cost-sensitive approach is consistent with recommendations in Bartlett & Wegkamp (2008) and Geifman & El-Yaniv (2017).

### 4.5.3 Explainable AI (XAI) Features

To address the "black-box" criticism of machine learning systems, the ShieldGuard system provides three layers of explainability:

**Table 4.9: Explainability Components**

| XAI Feature | Implementation | User Benefit |
| :--- | :--- | :--- |
| **Top TF-IDF Keywords** | Extracts the highest-weighted n-gram features from the SVM coefficient vector for the input transcript. | Shows exactly which words/phrases influenced the vishing classification (e.g., "urgent transfer", "OTP", "legal action"). |
| **Suspicious Phrase Detection** | 25+ compiled regex patterns matching known vishing tactics (bank impersonation, authority threats, tech support scams, crypto fraud, isolation/secrecy). | Highlights specific manipulative language within the transcript using red markup. |
| **Confidence Gauge** | Displays the model's calibrated probability as a percentage bar with colour-coded risk bands (Low / Review / Elevated / High). | Provides immediate visual indication of threat severity. |

**[IMAGE PLACEHOLDER: Figure 4.4 — Analysis Result with XAI Features]**
*(Instruction: Insert a screenshot showing a vishing detection result with the confidence gauge, highlighted keywords in the transcript, and the top TF-IDF features displayed.)*

### 4.5.4 SVM Model Evolution (v1 → v3)

The primary classifier underwent significant refinement from FYP1 to FYP2. The v3 SVM model, which is the active production model, incorporates several improvements over the v1 baseline.

**Table 4.10: SVM Model Version History**

| Version | Feature Engineering | Key Changes | Macro F1 |
| :--- | :--- | :--- | :--- |
| **v1 (FYP1)** | Single TF-IDF (character n-grams 3-5) | Baseline CalibratedClassifierCV with LinearSVC. Standalone `vectorizer.pkl` required. | 0.9809 |
| **v3 (FYP2)** | FeatureUnion (char_wb TF-IDF + word TF-IDF) | Dual TF-IDF pipeline embedded inside the sklearn Pipeline. Lemmatization added. Train-only augmentation. C=2.0 tuning. Threshold validated at 0.80. | Improved (see Chapter 5) |

The v3 model embeds its own FeatureUnion internally within the scikit-learn Pipeline object. This means the standalone `vectorizer.pkl` file is no longer required at inference time — the entire preprocessing-to-classification flow is encapsulated within a single `svm_model.pkl` artefact. This design reduces the risk of vectoriser mismatch and simplifies deployment.

LR, RF, and NN models were evaluated during experimentation, but SVM v3 was selected as the final production classifier because it provides the best balance of clean-test performance, inference speed, calibrated probability output, and explainable TF-IDF feature weights. This decision also simplifies deployment because the live system only needs one model artefact: `models/svm_model.pkl`.

## 4.6 Development — Version 3: Hybrid ML + LLM Detection Engine

The third and final development iteration implements the Hybrid ML + LLM detection engine — the most significant architectural contribution of FYP2. This layered cascade architecture combines the speed and precision of classical ML with the contextual reasoning capabilities of a Large Language Model (LLM), addressing the limitation identified in Chapter 2 that classical models may struggle with highly complex, context-heavy social engineering tactics (Moussavou Boussougou & Park, 2023; Sim & Kim, 2025).

### 4.6.1 Layered Cascade Architecture

The hybrid engine operates as a five-step cascade:

1. **ML Inference** — The transcript is preprocessed and classified by the SVM v3 model. This produces a vishing probability, confidence score, risk band, top TF-IDF keywords, and detected suspicious phrases.
2. **Threshold Gate** — If the vishing probability is ≤20% (STRONG_SAFE_PROB) and no suspicious phrases are detected, the system returns the ML-only verdict immediately, skipping the LLM layer entirely. This optimisation reduces latency for clearly benign transcripts.
3. **RAG Lookup** — The transcript is embedded using the all-MiniLM-L6-v2 sentence transformer and queried against the ChromaDB scam library to retrieve the top-2 most similar historical scam cases. Each case includes a text preview, heuristic scam type classification, and cosine similarity score.
4. **LLM Agent Reasoning** — A case file containing the transcript, ML evidence, flagged keywords, suspicious phrases, and RAG results is passed to the agentic AI layer running on Ollama (Llama 3.2:3b). The agents analyse the evidence and produce a natural-language explanation, tactic identification, scam type classification, and recommended user actions.
5. **Cross-Check and Divergence Detection** — The system compares the ML verdict with the LLM verdict. If they disagree (e.g., ML says "vishing" but LLM says "safe"), a divergence flag is raised and the final verdict is set to "SUSPICIOUS — UNCONFIRMED", prompting human review.

**Table 4.11: Hybrid Engine Decision Rules**

| ML Probability | LLM Assessment | Final Verdict | AI Status |
| :--- | :--- | :--- | :--- |
| ≥85% (Strong Vishing) | Agrees with ML | VISHING | ai_supported_ml |
| ≥85% (Strong Vishing) | Questions ML | SUSPICIOUS — UNCONFIRMED | review_ml_ai_disagreement |
| ≤20% (Strong Safe) | No rule flags, agrees | SAFE | ai_supported_ml |
| ≤20% (Strong Safe) | Finds high risk or rule flags | SUSPICIOUS — UNCONFIRMED | review_rule_or_ai_risk |
| 20%–85% (Borderline, ML=vishing) | Agrees | VISHING | ai_supported_ml |
| 20%–85% (Borderline, ML=vishing) | Questions ML | SUSPICIOUS — UNCONFIRMED | review_ml_ai_disagreement |
| 20%–85% (Borderline, ML=safe) | Finds high risk | EXERCISE CAUTION | ai_escalated_borderline_safe |
| 20%–85% (Borderline, ML=safe) | Agrees safe | SAFE | ai_supported_ml |

This ML-first verdict design ensures that the LLM never overrides the ML model's numerical probability. Instead, the LLM serves as an advisory layer that can escalate uncertain cases but cannot unilaterally downgrade a high-confidence vishing prediction. This design principle is critical because LLMs are susceptible to hallucination and inconsistent reasoning, whereas calibrated ML models provide stable, reproducible probability estimates (Sim & Kim, 2025).

### 4.6.2 RAG Scam Library

The Retrieval-Augmented Generation (RAG) module provides contextual evidence to the LLM by retrieving historically similar scam transcripts from a persistent ChromaDB vector store. The scam library is built from the project's training dataset (`english_dataset_final_v2.csv`), where all vishing-labelled transcripts are embedded using the all-MiniLM-L6-v2 model (384-dimensional, CPU-friendly, approximately 80MB).

Each embedded transcript is also classified heuristically into a scam type category based on keyword patterns in the text. This classification enables the system to inform users not just that a call is suspicious, but what type of scam it most closely resembles.

**Table 4.12: Heuristic Scam Type Classification**

| Scam Type | Detection Keywords | Example Phrase |
| :--- | :--- | :--- |
| Bank Impersonation | bank, account number, credit card, PIN | "Your bank account has been suspended" |
| OTP Fraud | OTP, one time password, verification code | "Please provide the OTP sent to your phone" |
| Tech Support Scam | tech support, microsoft, virus, malware | "Your computer has been infected with a virus" |
| Government Impersonation | tax, LHDN, revenue, customs | "LHDN has issued a warrant for your arrest" |
| Prize / Lottery Scam | prize, winner, lottery, congratulation | "Congratulations, you have been selected" |
| Authority Threat Scam | police, arrest, warrant, legal action | "Legal action will be taken against you" |
| Investment Fraud | investment, crypto, bitcoin, trading | "Guaranteed 200% returns on Bitcoin" |
| General Vishing | (fallback) | Other suspicious patterns |

### 4.6.3 Audio Transcription via Whisper ASR

The system supports audio file uploads through a dedicated `/api/transcribe` endpoint. Uploaded files are validated for format (.wav, .mp3, .m4a, .ogg, .flac, .webm) and size (maximum 25MB), then transcribed using OpenAI's Whisper base model loaded locally. The Whisper model is lazy-loaded on first use to reduce startup time when audio transcription is not needed.

**Table 4.13: File Validation and Secure Upload Process**

| Validation Step | Action Taken | Error Response |
| :--- | :--- | :--- |
| File Type Check | Verifies extension against allowed set. | HTTP 400 "Unsupported format" |
| File Size Limit | Restricts uploads to maximum 25 MB. | HTTP 413 "File too large" |
| Temporary Storage | Written to OS temp directory, deleted after transcription. | Ensures no persistent storage of audio data. |
| Whisper Loading | Lazy-loaded on first transcription request. | HTTP 500 "Whisper not installed" if unavailable. |

### 4.6.4 Per-User Concurrency Guard

To prevent system overload from duplicate analysis submissions (e.g., a user rapidly clicking "Analyze" multiple times), the backend implements a per-user asyncio lock. If a user submits a second analysis request while the first is still processing, the system immediately returns HTTP 429 "Analysis already in progress" rather than queuing multiple concurrent LLM calls. This guard is particularly important because the LLM inference step can take several seconds, and queuing multiple calls would degrade response times for all users.

## 4.7 Project Structure and Version Control

### 4.7.1 Project Directory Structure

**Table 4.14: Project Directory and File Structure Description**

| Directory | Contents | Purpose |
| :--- | :--- | :--- |
| `frontend/src/` | React.js components, pages, hooks, API clients, CSS | User-facing dashboard application |
| `backend/` | FastAPI app, inference engine, hybrid engine, RAG, auth, database | All server-side logic and ML inference |
| `backend/agents/` | CrewAI agent definitions for LLM reasoning | Agentic AI layer configuration |
| `models/` | `svm_model.pkl`, `svm_model_metadata.json` | Active production SVM artefact and its evaluation metadata |
| `models/legacy/` | SVM v1/v2, LR, RF, vectorizer, and neural network artefacts | Archived experimental models kept for documentation and comparison |
| `data/` | `english_dataset_final_v2.csv`, `scam_library/` (ChromaDB) | Training dataset and RAG vector store |
| `notebooks/` | Jupyter notebooks for training, evaluation, and analysis | Experiment documentation and reproducibility |
| `tests/` | Test scripts and benchmark cases | Automated verification |
| `docs/` | ML training metrics, threshold documentation | Technical documentation |

### 4.7.2 Version Control with Git and GitHub

**Table 4.15: Git and GitHub Usage for Version Control**

| Action | Git Command | Purpose |
| :--- | :--- | :--- |
| Initialisation | `git init` | Starts tracking the project directory. |
| Feature Branching | `git checkout -b feature/hybrid-engine` | Isolates Phase 2 development from the stable main branch. |
| Committing | `git commit -m "Integrate RAG + LLM cascade"` | Saves snapshots with descriptive messages for audit trail. |
| Tagging | `git tag v3.0-fyp2` | Marks the FYP2 release version for reproducibility. |

### 4.7.3 Version History and Iterative Enhancements

**Table 4.16: Version History and Iterative Feature Enhancements**

| Version | Key Features Implemented | Focus Area |
| :--- | :--- | :--- |
| **v1.0 (FYP1)** | Streamlit prototype, TF-IDF + SVM/LR/RF baselines, lightweight neural network, session authentication, leakage-safe evaluation. | Baseline ML Pipeline |
| **v2.0 (FYP2)** | React.js + FastAPI migration, JWT auth, Supabase integration, brute-force protection, rate limiting, SVM v3 with FeatureUnion and lemmatization, XAI keyword extraction, suspicious phrase detection. | Full-Stack & Security |
| **v3.0 (FYP2)** | Hybrid ML + LLM engine, ChromaDB RAG scam library, Ollama agent reasoning, divergence detection, per-user concurrency guard, audio transcription via Whisper, risk-band stratification, comprehensive audit logging. | Hybrid Intelligence |

## 4.8 Summary

This chapter has documented the complete system development lifecycle of the ShieldGuard Vishing Detection System across three iterative versions. Version 1 established the full-stack architecture with enterprise-grade security controls, migrating from the FYP1 Streamlit prototype to a scalable React.js + FastAPI platform. Version 2 hardened the ML inference pipeline with research-backed asymmetric thresholds, exact train-deploy preprocessing alignment, and multi-layered explainability features. Version 3 introduced the Hybrid ML + LLM detection engine — a novel layered cascade that combines the precision and speed of classical TF-IDF + SVM classification with the contextual reasoning of RAG-enhanced agentic AI, while ensuring the ML model remains the authoritative source of numerical probability. The development process demonstrates a systematic progression from prototype to production-grade system, with each version building upon validated foundations established in the previous iteration. Together, these versions deliver a defensible, transparent, and near-real-time vishing detection platform suitable for both academic evaluation and practical deployment.

---

## Citations Used in Chapter 4 (Download Links)

1. **Phang, Y. H., et al. (2024).**
   - **Title:** VishGuard: Defending Against Vishing.
   - **Source:** IEEE Xplore — search "VishGuard Defending Against Vishing 2024"
   - **Usage:** Justifies layered detection architectures and real-time inference requirements.

2. **Ma, Z. et al. (2025).**
   - **Title:** TeleAntiFraud-28k: An Audio-Text Slow-Thinking Dataset for Telecom Fraud Detection.
   - **Download:** [https://arxiv.org/abs/2402.13781](https://arxiv.org/abs/2402.13781)
   - **Usage:** Supports train-deploy mismatch concerns and the need for robust preprocessing.

3. **Moussavou Boussougou, M. N. E., & Park, D. J. (2023).**
   - **Title:** FastText Word Embedding for Korean Voice Phishing Detection Using a CNN-BiLSTM.
   - **Download:** [https://ieeexplore.ieee.org/document/10106037](https://ieeexplore.ieee.org/document/10106037)
   - **Usage:** Justifies the need for robust n-gram features and subword-level representations.

4. **Sim, J., & Kim, S. (2025).**
   - **Title:** Detecting Voice Phishing with Precision: Fine-Tuning Small Language Models.
   - **Source:** Search on Google Scholar for the exact title.
   - **Usage:** Supports the positioning of LLMs as advisory (not authoritative) layers due to hallucination risk.

5. **Provost, F., & Fawcett, T. (2001).**
   - **Title:** Robust Classification for Imprecise Environments.
   - **Download:** [https://link.springer.com/article/10.1023/A:1007601015854](https://link.springer.com/article/10.1023/A:1007601015854)
   - **Usage:** Research basis for shifting the vishing decision boundary to 0.80 to reduce alert fatigue.

6. **Chow, C. K. (1970).**
   - **Title:** On Optimum Recognition Error and Reject Tradeoff.
   - **Source:** IEEE Transactions on Information Theory.
   - **Usage:** Foundation for the asymmetric reject-option threshold design.

7. **Chichwadia, N., & Mpekoa, N. (2024).**
   - **Title:** Detecting Vishing and Smishing Using Machine Learning.
   - **Source:** Search on Google Scholar for the exact title.
   - **Usage:** Referenced in literature review; supports classical ML baselines for phishing detection.

8. **Rajeswari, R., & Prabhu, S. (2025).**
   - **Title:** Artificial Intelligence in Phishing Detection and Analysis: A Foundational Review.
   - **Source:** Search on Google Scholar for the exact title.
   - **Usage:** Supports evaluation methodology and security-aware metric selection.
