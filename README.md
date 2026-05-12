# ShieldGuard — AI-Powered Vishing Detection System

> Hybrid ML + LLM + RAG multi-agent system for detecting voice phishing (vishing) attacks.

## Quick Start

**Backend** (Terminal 1):
```powershell
cd backend
..\.venv\Scripts\activate
python main.py
```

**Frontend** (Terminal 2):
```powershell
cd frontend
npm install
npm run dev
```

**Open:** http://localhost:5173

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------| 
| ML Classifier | TF-IDF (FeatureUnion: char+word) + calibrated SVM v3 | Fast ML-first classification (98.88% clean-test accuracy) |
| RAG Search | ChromaDB + MiniLM-L6-v2 | Historical scam pattern matching |
| AI Reviewer | Groq API (Llama 3.3 70B) + structured prompts | Explanation and ML disagreement review without overriding strong ML evidence |

## Features

- **Final Production SVM Engine**: Evaluates linguistic patterns, urgency indicators, and scam phrases using the selected SVM v3 classifier.
- **RAG + LLM Context Search**: Cross-references local vector databases of known scam scripts (ChromaDB) and generates natural language explanations via Groq API (Llama 3.3 70B).
- **Model Selection Rationale**: LR, RF, and NN were evaluated during experimentation, but SVM v3 was selected for deployment because it gives the best balance of accuracy, speed, and explainability.
- **Real-Time System Health**: Live health monitoring (`/api/health`) tracks connectivity and loaded ML models via a reactive polling hook.
- **V2 "Dark Tech Startup" UI**: Completely overhauled dark-mode interface (`#09090b` base) built with custom Shadcn-compatible components.
- **WebGL Interactive Elements**: Features high-performance WebGL shaders including an ethereal fluid background on the authentication page and interactive `LiquidMetalButton` components.
- **Professional Input Components**: Includes floating-label transcript inputs, drag-and-drop audio zones, and a scroll-gated Terms & Conditions dialog.
- **Local-First Audio Processing**: Audio transcription powered by OpenAI’s Whisper Large v3 Turbo model via the Groq API for ultra-fast, high-accuracy speech-to-text.

- **Admin Analytics Dashboard**: Dedicated `/admin` page with KPI cards, verdict donut chart, 7-day detection trend, confidence histogram, and top-user leaderboard — powered by Recharts and Supabase audit logs.

## How It Works (System Flow)

The system uses an ML-first hybrid cascade. The machine learning model owns the numeric risk score and primary verdict; the LLM layer reviews and explains the result without silently replacing strong ML evidence.

1. **Layer 1 (ML Classification):** The input transcript is first processed by a calibrated SVM using TF-IDF FeatureUnion features. It returns `P(vishing)`, `P(safe)`, an ML label, and TF-IDF feature signals.
2. **Layer 2 (RAG Search):** The transcript is embedded and searched against a ChromaDB vector database of past vishing calls. The top similar cases are retrieved as context.
3. **Layer 3 (AI Review):** Groq API (Llama 3.3 70B) prompts produce structured advisory fields: scam type, tactics, plain-language explanation, action steps, and whether the AI supports or questions the ML result.
4. **ML-first cross-check:** Strong ML results are preserved. If AI/rules disagree with ML, the system flags the case as `SUSPICIOUS - UNCONFIRMED` instead of letting the LLM silently overwrite the model.

## Codebase Guide (Where to Look)

To understand how the hybrid AI architecture is implemented, check out these core files in the `backend/` folder:

- `backend/hybrid_engine.py`: The heart of the system. This file keeps ML as the primary decision layer, runs RAG retrieval, invokes the Groq API reviewer, and performs the final cross-check logic.
- `backend/inference.py`: Shows how the classical ML model is invoked. Also contains `get_explanation` which extracts the top TF-IDF keywords from the FeatureUnion pipeline.
- `backend/rag_module.py`: Handles ChromaDB vector storage and similarity search.
- `backend/agents/crew.py`: Contains the Groq API prompt workflow that produces structured advisory JSON without overriding strong ML evidence.
- `frontend/src/components/results/`: Look here for the React components that visualize the analysis, specifically how the hybrid cascade outputs are parsed into the UI.
- `frontend/src/pages/AdminDashboard.jsx`: The admin analytics dashboard with Recharts charts and Supabase-backed aggregate statistics.
- `notebooks/03_limited_dataset_svm_training.py`: The v3 limited-dataset training pipeline with `CELL 1`, `CELL 2`, etc. comments for easy Jupyter copy/paste.

### Example: How the Models and Agents are Called

Here is a simplified snippet demonstrating the flow inside `hybrid_engine.py`:

```python
from inference import run_inference_detailed
from rag_module import query_similar_scams
from agents.crew import run_crew

# 1. Classical ML inference remains the primary verdict source.
ml_result = run_inference_detailed(transcript, "SVM", models, nn_model)

# 2. RAG retrieval adds past-case context for explanation.
similar_cases = query_similar_scams(transcript, n_results=2)

# 3. Groq API review returns advisory JSON only.
ai_review = await run_crew({
    "transcript": transcript,
    "ml_score": ml_result["confidence"],
    "ml_label": ml_result["label"],
    "similar_cases": similar_cases,
})
```

## Final Production ML Model - SVM v3 (2026-04-29)

The deployed app keeps only `models/svm_model.pkl` as the active runtime model. LR, RF, and NN artifacts are retained in `models/legacy/` for report evidence and examiner discussion, but they are no longer loaded by the production backend.

The final SVM classifier was selected because it offers the strongest practical balance for a user-facing vishing detector: high clean-test accuracy, millisecond-level inference, calibrated probabilities, and transparent TF-IDF feature explanations.

| Change | Detail | Impact |
|---|---|---|
| Split before augmentation | Real data is split into train/validation/test before synthetic examples are added | Prevents leakage into evaluation |
| Train-only augmentation | EDA synonym replacement is applied only to the safe training class | Improves minority-class coverage |
| Hard examples | Adds realistic safe bank/delivery/appointment reminders and vishing pressure scripts to training only | Reduces false positives on legitimate calls |
| Calibrated SVM | LinearSVC wrapped with probability calibration | Produces usable `P(vishing)` and `P(safe)` |
| Validation threshold tuning | Threshold selected on validation data, then locked for the clean test set | Keeps verdict logic aligned with measured performance |

**Clean held-out test result:** 98.88% accuracy, 98.69% macro F1, 99.20% balanced accuracy.

**Clean test confusion matrix:** safe `108/108` correct, vishing `245/249` correct.

Training assets:
- `notebooks/03_limited_dataset_svm_training.py`: copy/paste-ready Jupyter training script with `CELL 1`, `CELL 2`, etc. comments.
- `models/svm_model.pkl`: promoted production model.
- `models/svm_model_metadata.json`: threshold, metrics, and training notes.
- `docs/ml_training_v3_metrics.json`: validation/test metrics and sanity-check outputs.

## Previous ML Model - v2 Improvements (2026-04-22)

The SVM classifier was retrained with the following upgrades over the original baseline:

| Change | Detail | Impact |
|---|---|---|
| Lemmatization | NLTK WordNetLemmatizer (verb + noun pass) | Reduces vocabulary noise |
| EDA Augmentation | Synonym replacement on 'safe' minority class (40% extra samples) | Reduces class imbalance |
| FeatureUnion | char_wb TF-IDF (3-5 grams) + word TF-IDF (1-2 grams) | Captures spelling patterns AND semantic phrases |
| K-Fold CV | StratifiedKFold, k=5, all folds scored >0.98 | Proves model is not a lucky single split |
| GridSearchCV | Best C=10.0 found automatically | Optimal hyperparameters for this dataset |

**Result:** F1-macro improved from **0.9809 → 0.9936** (+1.27%)

## Documentation

See [LLMContext.md](LLMContext.md) for the complete system documentation.
