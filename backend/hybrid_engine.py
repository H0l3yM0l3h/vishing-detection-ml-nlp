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
AI_REVIEW_MIN_PROB = 0.20
STRONG_SAFE_PROB = 0.20
STRONG_VISHING_PROB = 0.85
DEFAULT_LLM_MODEL = "llama3.2:3b"


async def run_hybrid_analysis(
    transcript: str,
    model_choice: str,
    ml_label: str,
    ml_score: float,
    top_keywords: list,
    suspicious_phrases: list | None = None,
    vishing_probability: float | None = None,
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
    vishing_probability = (
        float(vishing_probability)
        if vishing_probability is not None
        else (float(ml_score) if ml_label == "vishing" else 1.0 - float(ml_score))
    )

    if vishing_probability <= STRONG_SAFE_PROB and not suspicious_phrases:
        return {
            "verdict": ml_label,
            "confidence": ml_score,
            "source": "ml_only",
            "ml_label": ml_label,
            "vishing_probability": vishing_probability,
            "ai_status": "skipped_strong_ml_safe",
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
        "vishing_probability": vishing_probability,
        "ml_model": model_choice,
        "flagged_keywords": keyword_list,
        "suspicious_phrases": suspicious_phrases or [],
        "similar_cases": similar_cases,
    }

    # ── STEP 4: Run CrewAI agents ────────────────
    crew_result = await run_crew(case_file, model=llm_model)

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

    final_verdict, divergence_flag, ai_status = _ml_first_verdict(
        ml_label=ml_label,
        vishing_probability=vishing_probability,
        suspicious_phrases=suspicious_phrases or [],
        crew_result=crew_result,
    )

    return {
        "verdict": final_verdict,
        "confidence": ml_score,
        "source": "hybrid",
        "ml_label": ml_label,
        "vishing_probability": vishing_probability,
        "ai_status": ai_status,
        "ai_verdict": crew_result.get("verdict"),
        "ai_risk_level": crew_result.get("risk_level"),
        "ai_alignment": crew_result.get("ml_alignment"),
        "explanation": crew_result.get("explanation"),
        "tactic": crew_result.get("tactics", []),
        "scam_type": crew_result.get("scam_type"),
        "similar_cases": similar_cases,
        "action_steps": crew_result.get("action_steps", []),
        "divergence_flag": divergence_flag,
    }


def _ml_first_verdict(
    ml_label: str,
    vishing_probability: float,
    suspicious_phrases: list,
    crew_result: dict,
) -> tuple[str, bool, str]:
    """
    Convert AI advisory into a final verdict without letting AI override ML.

    Rules:
      - Strong ML vishing remains vishing unless AI questions it, then review.
      - Strong ML safe remains safe unless rules/AI find risk, then caution.
      - Borderline ML uses AI to choose caution vs safe review.
      - LLM unavailable/error never replaces the ML verdict.
    """
    ai_verdict = str(crew_result.get("verdict", "")).upper()
    ai_risk = str(crew_result.get("risk_level", "")).lower()
    ai_alignment = str(crew_result.get("ml_alignment", "")).lower()

    if ai_verdict in {"LLM UNAVAILABLE", "ANALYSIS ERROR"}:
        return ml_label, False, "unavailable"

    ai_says_safe = "CALL APPEARS SAFE" in ai_verdict or ai_risk == "low"
    ai_says_high_risk = "HANG UP NOW" in ai_verdict or ai_risk == "high"
    ai_questions_ml = ai_alignment == "questions_ml"
    has_rule_flags = bool(suspicious_phrases)

    if vishing_probability >= STRONG_VISHING_PROB:
        if ai_says_safe or ai_questions_ml:
            return "SUSPICIOUS - UNCONFIRMED", True, "review_ml_ai_disagreement"
        return "vishing", False, "ai_supported_ml"

    if vishing_probability <= STRONG_SAFE_PROB:
        if has_rule_flags or ai_says_high_risk:
            return "SUSPICIOUS - UNCONFIRMED", True, "review_rule_or_ai_risk"
        return "safe", False, "ai_supported_ml"

    if ml_label == "vishing":
        if ai_says_safe or ai_questions_ml:
            return "SUSPICIOUS - UNCONFIRMED", True, "review_ml_ai_disagreement"
        return "vishing", False, "ai_supported_ml"

    if ai_says_high_risk or has_rule_flags:
        return "EXERCISE CAUTION", False, "ai_escalated_borderline_safe"

    if ai_says_safe:
        return "safe", False, "ai_supported_ml"

    return "INCONCLUSIVE", False, "needs_more_evidence"
