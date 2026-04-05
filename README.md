# ShieldGuard — AI-Powered Vishing Detection System

> Hybrid ML + LLM + RAG multi-agent system for detecting voice phishing (vishing) attacks.

## Quick Start

**Backend** (Terminal 1):
```powershell
cd backend
..\\.venv\Scripts\activate
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
| ML Classifier | TF-IDF + SVM/LR/RF/NN | Fast classification (98.5% accuracy) |
| RAG Search | ChromaDB + MiniLM-L6-v2 | Historical scam pattern matching |
| Multi-Agent LLM | CrewAI + Ollama (Llama 3.2 3B) | Verdict reasoning with 4 AI agents |

## How It Works (System Flow)

The system uses a sequential hybrid cascade connecting classic Machine Learning with Generative AI (LLMs and Agents):

1. **Layer 1 (ML Classification):** The input transcript is first processed by a lightning-fast ML classifier (e.g. TF-IDF + SVM). If the ML indicates the transcript is likely safe, it returns a fast verdict. If it detects potential risk, it triggers the LLM cascade.
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
- `backend/inference.py`: Shows how the classical ML models are invoked.
- `backend/rag_module.py`: Handles ChromaDB vector storage and similarity search.
- `backend/agents/agent_definitions.py` & `backend/agents/crew.py`: Contains the CrewAI setup—where the LLM persona prompts, tasks, and sequential workflow are defined.
- `frontend/src/components/results/`: Look here for the React components that visualize the analysis, specifically how the hybrid cascade outputs are parsed into the UI.

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

## Documentation

See [LLMContext.md](LLMContext.md) for the complete system documentation.
