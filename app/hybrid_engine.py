"""
hybrid_engine.py — Central orchestrator for ShieldGuard Phase 2
================================================================
Connects the ML layer (Phase 1) with the RAG + CrewAI Agents (Phase 2)
in a layered cascade architecture.

Flow:
  1. ML inference (already done by caller) → receives score + keywords
  2. Threshold gate → skip LLM if score < 0.45
  3. RAG lookup → find similar historical scam cases
  4. CrewAI agents → reasoning, explanation, verdict
  5. Cross-check → flag ML vs LLM divergence
"""

from rag_module import query_similar_scams
from agents.crew import run_crew

# ── Configuration ────────────────────────────────
ML_THRESHOLD = 0.45        # Skip LLM if ML score below this
DIVERGENCE_THRESHOLD = 0.3  # Flag if ML and LLM strongly disagree
DEFAULT_LLM_MODEL = "llama3.2:3b"


def run_hybrid_analysis(
    transcript: str,
    model_choice: str,
    ml_label: str,
    ml_score: float,
    top_keywords: list,
    suspicious_phrases: list | None = None,
    llm_model: str = DEFAULT_LLM_MODEL,
) -> dict:
    """
    Run the full hybrid analysis cascade.

    Parameters
    ----------
    transcript         : cleaned transcript text
    model_choice       : ML model name used (e.g. "SVM")
    ml_label           : ML prediction ("vishing" or "safe")
    ml_score           : ML confidence score (0.0 - 1.0)
    top_keywords       : list of (keyword, weight) tuples from TF-IDF
    suspicious_phrases : list of regex-matched suspicious phrases
    llm_model          : Ollama model tag for LLM layer

    Returns
    -------
    dict with keys:
        verdict         : str — final verdict string
        confidence      : float — ML confidence score
        source          : str — "ml_only" or "hybrid"
        ml_label        : str — original ML prediction
        explanation     : str | None — LLM-generated explanation
        tactic          : list | None — detected social engineering tactics
        scam_type       : str | None — classified scam type
        similar_cases   : list | None — RAG results
        action_steps    : list | None — recommended actions
        divergence_flag : bool — True if ML and LLM disagree
    """

    # ── STEP 1: Threshold gate ───────────────────
    if ml_score < ML_THRESHOLD:
        return {
            "verdict": ml_label,
            "confidence": ml_score,
            "source": "ml_only",
            "ml_label": ml_label,
            "explanation": None,
            "tactic": None,
            "scam_type": None,
            "similar_cases": None,
            "action_steps": None,
            "divergence_flag": False,
        }

    # ── STEP 2: RAG lookup ───────────────────────
    similar_cases = []
    try:
        similar_cases = query_similar_scams(transcript, n_results=2)
    except Exception as e:
        print(f"[Hybrid] RAG query failed: {e}")

    # ── STEP 3: Build case file ──────────────────
    keyword_list = []
    if top_keywords:
        keyword_list = (
            [k for k, w in top_keywords]
            if isinstance(top_keywords[0], (list, tuple))
            else top_keywords
        )

    case_file = {
        "transcript": transcript,
        "ml_score": ml_score,
        "ml_label": ml_label,
        "ml_model": model_choice,
        "flagged_keywords": keyword_list,
        "suspicious_phrases": suspicious_phrases or [],
        "similar_cases": similar_cases,
    }

    # ── STEP 4: Run CrewAI agents ────────────────
    crew_result = run_crew(case_file, model=llm_model)

    # ── STEP 5: Cross-check divergence ───────────
    divergence_flag = False
    llm_verdict_lower = crew_result.get("verdict", "").lower()

    ml_says_vishing = ml_label == "vishing"
    llm_says_safe = any(w in llm_verdict_lower for w in ["safe", "legitimate", "benign"])
    llm_says_vishing = any(w in llm_verdict_lower for w in ["hang up", "vishing", "scam", "danger", "risk"])

    if ml_says_vishing and llm_says_safe:
        divergence_flag = True
    elif not ml_says_vishing and llm_says_vishing:
        divergence_flag = True

    # ── STEP 6: Build final result ───────────────
    final_verdict = crew_result.get("verdict", ml_label)
    if divergence_flag:
        final_verdict = "SUSPICIOUS — UNCONFIRMED"

    return {
        "verdict": final_verdict,
        "confidence": ml_score,
        "source": "hybrid",
        "ml_label": ml_label,
        "explanation": crew_result.get("explanation"),
        "tactic": crew_result.get("tactics", []),
        "scam_type": crew_result.get("scam_type"),
        "similar_cases": similar_cases,
        "action_steps": crew_result.get("action_steps", []),
        "divergence_flag": divergence_flag,
    }
