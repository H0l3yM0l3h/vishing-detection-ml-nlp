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
| ML Classifier | TF-IDF (FeatureUnion: char+word) + SVM | Fast classification (99.4% accuracy) |
| RAG Search | ChromaDB + MiniLM-L6-v2 | Historical scam pattern matching |
| Multi-Agent LLM | CrewAI + Ollama (Llama 3.2 3B) | Verdict reasoning with 4 AI agents |

## Features

- **Advanced Machine Learning Engine**: Evaluates linguistic patterns, emotional tone, and urgency indicators to detect scams.
- **RAG + LLM Context Search**: Cross-references local vector databases of known scam scripts (ChromaDB) and generates natural language explanations via Ollama.
- **Deep Neural Network Validation**: Second-stage verification routing high-risk transcripts through an optimized multi-layer perceptron.
- **Real-Time System Health**: Live health monitoring (`/api/health`) tracks connectivity and loaded ML models via a reactive polling hook.
- **V2 "Dark Tech Startup" UI**: Completely overhauled dark-mode interface (`#09090b` base) built with custom Shadcn-compatible components.
- **WebGL Interactive Elements**: Features high-performance WebGL shaders including an ethereal fluid background on the authentication page and interactive `LiquidMetalButton` components.
- **Professional Input Components**: Includes floating-label transcript inputs, drag-and-drop audio zones, and a scroll-gated Terms & Conditions dialog.
- **Local-First Audio Processing**: Client-side transcription using local instances of OpenAI's Whisper model via FastAPI.

## How It Works (System Flow)

The system uses a sequential hybrid cascade connecting classic Machine Learning with Generative AI (LLMs and Agents):

1. **Layer 1 (ML Classification):** The input transcript is first processed by a lightning-fast ML classifier (TF-IDF FeatureUnion + SVM). If the ML indicates the transcript is likely safe, it returns a fast verdict. If it detects potential risk, it triggers the LLM cascade.
2. **Layer 2 (RAG Search):** The transcript is embedded and searched against a ChromaDB vector database of past vishing calls. The top similar cases are retrieved as context.
3. **Layer 3 (Multi-Agent Reasoning):** Using **CrewAI**, 4 distinct agents analyze the data sequentially:
   - **Technical Auditor:** Validates the initial ML flag.
   - **Pattern Detective:** Classifies the scam type using the transcript and RAG results.
   - **Psychology Profiler:** Detects social engineering tactics (Fear, Urgency, Authority).
   - **Safety Guardian:** Consolidates the findings into a final user-friendly verdict and actionable steps.
4. **Cross-Check:** The final LLM verdict is cross-checked against the initial ML result. If there's a strong disagreement (Divergence Detection), the resulting verdict is flagged as "Suspicious — Unconfirmed".

## Codebase Guide (Where to Look)

To understand how the hybrid AI architecture is implemented, check out these core files in the `backend/` folder:

- `backend/hybrid_engine.py`: The heart of the system. This file acts as the orchestrator, taking the ML output, running the RAG query, invoking the CrewAI agents, and performing the final cross-check logic.
- `backend/inference.py`: Shows how the classical ML models are invoked. Also contains `get_explanation` which extracts the top TF-IDF keywords (supports both v1 single-vectorizer and v2 FeatureUnion pipelines).
- `backend/rag_module.py`: Handles ChromaDB vector storage and similarity search.
- `backend/agents/agent_definitions.py` & `backend/agents/crew.py`: Contains the CrewAI setup—where the LLM persona prompts, tasks, and sequential workflow are defined.
- `frontend/src/components/results/`: Look here for the React components that visualize the analysis, specifically how the hybrid cascade outputs are parsed into the UI.
- `notebooks/02_improved_ml_training.py`: The v2 ML training pipeline with all improvements.

### Example: How the Models and Agents are Called

Here is a simplified snippet demonstrating the flow inside `hybrid_engine.py`:

```python
from inference import run_inference
from rag_module import query_similar_scams
from agents.crew import run_crew

# 1. Classical ML Inference
# Returns a label (e.g., 'vishing') and a confidence score (e.g., 0.94)
ml_label, ml_score = run_inference(transcript, "SVM", models, nn_model)

# 2. Threshold Check
if ml_score >= 0.45:
    # 3. RAG Retrieval (Look up past scams)
    similar_cases = query_similar_scams(transcript, n_results=2)
    
    # 4. Multi-Agent Reasoning (Run the CrewAI agents sequentially)
    final_result = run_crew({
        "transcript": transcript,
        "ml_score": ml_score,
        "ml_label": ml_label,
        "similar_cases": similar_cases
    })
```

## ML Model — v2 Improvements (2026-04-22)

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
