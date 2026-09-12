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
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"  # Groq model ID (v3.4)


async def run_hybrid_analysis(
    transcript: str,
    model_choice: str,
    ml_label: str,
    ml_score: float,
    top_keywords: list,
    suspicious_phrases: list | None = None,
    vishing_probability: float | None = None,
    payment_accounts: int = 0,
    known_scam_identifiers: int = 0,
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

    # ── STEP 5: Reconcile ML and AI ──────────────
    # NOTE: a divergence pre-computation used to sit here, deriving
    # `divergence_flag` and `final_verdict` from a simpler keyword comparison.
    # Both values were then immediately overwritten by _ml_first_verdict()
    # below, so the block had no effect on any response. It has been removed
    # rather than left in place looking authoritative.
    final_verdict, divergence_flag, ai_status = _ml_first_verdict(
        ml_label=ml_label,
        vishing_probability=vishing_probability,
        suspicious_phrases=suspicious_phrases or [],
        crew_result=crew_result,
        payment_accounts=payment_accounts,
        known_scam_identifiers=known_scam_identifiers,
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


# Canonical verdict strings. Previously the same logical verdict was spelled
# two different ways (ASCII hyphen vs em dash) in the same request path.
VERDICT_SUSPICIOUS = "SUSPICIOUS — UNCONFIRMED"
VERDICT_CAUTION    = "EXERCISE CAUTION"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"


def _ml_first_verdict(
    ml_label: str,
    vishing_probability: float,
    suspicious_phrases: list,
    crew_result: dict,
    payment_accounts: int = 0,
    known_scam_identifiers: int = 0,
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

    # A database hit is fact, not inference: this exact account or number has
    # fraud reports filed against it. It therefore outranks every other signal,
    # including a confident "safe" from the classifier, and is the one case
    # where non-ML evidence may raise the verdict outright.
    if known_scam_identifiers > 0:
        return "vishing", False, "confirmed_scam_identifier"

    if ai_verdict in {"LLM UNAVAILABLE", "ANALYSIS ERROR"}:
        return ml_label, False, "unavailable"

    # Token-based matching rather than exact-phrase matching.
    #
    # The prompt asks the model to reply with "CALL APPEARS SAFE" or "HANG UP
    # NOW", but an LLM does not always comply exactly — in practice it returns
    # "SAFE", "Legitimate call", "Appears safe" and so on. The previous
    # `"CALL APPEARS SAFE" in ai_verdict` test failed on every one of those,
    # silently discarding a clear AI judgement.
    ai_says_safe = (
        any(w in ai_verdict for w in ("SAFE", "LEGITIMATE", "BENIGN", "NO RISK", "GENUINE"))
        or ai_risk == "low"
    )
    ai_says_high_risk = (
        any(w in ai_verdict for w in ("HANG UP", "VISHING", "SCAM", "FRAUD", "PHISH"))
        or ai_risk == "high"
    )
    ai_questions_ml = ai_alignment == "questions_ml"

    # A single keyword match is weak evidence and should not, on its own,
    # override a safe verdict from both the classifier and the AI reviewer.
    #
    # The regex layer matches surface strings, so a legitimate call saying
    # "there is nothing you need to do right now" trips the urgency pattern on
    # "right now". Requiring corroboration — two or more distinct flags, or an
    # AI risk signal — keeps the rule layer useful as a tripwire without
    # letting one ambiguous phrase dominate two stronger signals.
    #
    # This threshold applies only in the borderline band. Strong ML verdicts
    # are handled above and are unaffected.
    rule_flag_count = len(suspicious_phrases)
    has_rule_flags = rule_flag_count >= 2

    # "SAFE" is a substring of "NOT SAFE" / "UNSAFE"; make sure a negated
    # verdict is never read as reassurance.
    if any(w in ai_verdict for w in ("NOT SAFE", "UNSAFE", "NOT LEGITIMATE")):
        ai_says_safe = False
        ai_says_high_risk = True

    if vishing_probability >= STRONG_VISHING_PROB:
        if ai_says_safe or ai_questions_ml:
            return VERDICT_SUSPICIOUS, True, "review_ml_ai_disagreement"
        return "vishing", False, "ai_supported_ml"

    if vishing_probability <= STRONG_SAFE_PROB:
        if has_rule_flags or ai_says_high_risk:
            return VERDICT_SUSPICIOUS, True, "review_rule_or_ai_risk"
        return "safe", False, "ai_supported_ml"

    if ml_label == "vishing":
        if ai_says_safe or ai_questions_ml:
            return VERDICT_SUSPICIOUS, True, "review_ml_ai_disagreement"
        return "vishing", False, "ai_supported_ml"

    if ai_says_high_risk or has_rule_flags:
        return VERDICT_CAUTION, False, "ai_escalated_borderline_safe"

    # ── Corroboration override ──────────────────────────────────────────
    # The classifier is not sharply calibrated in the middle of its range, so
    # a real scam can land at p≈0.71-0.73 and fall through as "safe". A
    # parcel-customs scam demanding a transfer to a "clearance account" did
    # exactly that.
    #
    # A payment account extracted from the call is independent, behavioural
    # evidence: being asked to send money to an account during an unsolicited
    # call is the defining action of a transfer scam, and no legitimate caller
    # in the reference set does it. Measured across the sample library, a
    # payment account appears in 2 of 3 scam calls and 0 of 3 genuine calls,
    # including the two hard negatives (a real bank fraud alert and an
    # appointment reminder).
    #
    # NOT used for this: similarity to the RAG corpus. That index contains
    # only vishing examples, so every transcript matches something and the
    # score carries no discriminating information — the genuine bank call
    # scores 0.6501, HIGHER than the parcel scam's 0.5708. Using it as
    # corroboration would flag exactly the calls the system must not flag.
    #
    # The escalation stops at "suspicious, unconfirmed". The ML layer declined
    # to commit, so claiming "vishing" would overstate the evidence; refusing
    # to flag it at all understates it.
    if payment_accounts > 0:
        return VERDICT_SUSPICIOUS, True, "review_payment_request_borderline_ml"

    if ai_says_safe:
        return "safe", False, "ai_supported_ml"

    # Nothing contradicts the ML verdict: no rule flags, no AI risk signal, no
    # AI challenge to the classification. Defer to ML rather than returning
    # INCONCLUSIVE.
    #
    # This branch previously returned INCONCLUSIVE, which produced a visibly
    # wrong result on ordinary benign calls. The production model is not
    # sharply calibrated in the middle of its range — genuinely safe calls land
    # around p(vishing) 0.5-0.65 — so an ordinary customer-service call fell
    # into the borderline band, and if the LLM's wording did not match the
    # expected phrase exactly the user was told the call was "inconclusive"
    # even though every signal available said safe.
    #
    # "Inconclusive" is reserved for a genuine absence of evidence (handled by
    # insufficient_evidence() before this function is reached) or a real
    # conflict between layers. Declining to commit when all layers agree is not
    # caution, it is a failure to answer the question the user asked.
    return ml_label, False, "ml_verdict_uncontested"
