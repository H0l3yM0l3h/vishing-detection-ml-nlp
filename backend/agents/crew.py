"""
crew.py — Direct async Groq execution for ShieldGuard Phase 2
================================================================
[v3.4 — 2026-05-05] Migrated from Ollama HTTP to Groq Cloud API.

Why Groq is faster than local Ollama:
  - Groq's custom LPU (Language Processing Unit) hardware delivers
    500+ tokens/second — 10-50x faster than CPU-based Ollama.
  - 70B model (llama-3.3-70b-versatile) replaces local 3B model,
    providing significantly better reasoning and JSON compliance.
  - Network round-trip (~50ms) is negligible vs. the 15-30s saved
    on local inference.

Architecture:
  Prompt 1 (Forensic):  ML validation + scam classification     ─┐
  Prompt 2 (Guardian):  Tactic detection + verdict + actions     ─┤ sequential
                                                                  ↓
  Final parse + cross-check                                      → result
"""

import json
import re
import asyncio

from llm_config import check_groq_available, _get_groq_client, MODEL_PRESETS, DEFAULT_MODEL


# ── Groq generation ─────────────────────────────────────────────────────────
async def _groq_generate(prompt: str, model: str, timeout: float = 60.0) -> str:
    """
    Call Groq's chat completions API.
    Returns the generated text, or an empty string on failure.
    """
    preset = MODEL_PRESETS.get(model, {"max_tokens": 512, "temperature": 0.1})

    try:
        client = _get_groq_client()
        if client is None:
            return ""

        # Run the synchronous Groq SDK call in a thread pool to avoid
        # blocking the asyncio event loop
        def _sync_call():
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cybersecurity vishing detection expert. "
                            "Analyze transcripts and return structured results. "
                            "Be concise and precise."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=preset.get("temperature", 0.1),
                max_tokens=preset.get("max_tokens", 512),
            )
            return response.choices[0].message.content or ""

        return await asyncio.to_thread(_sync_call)

    except Exception as e:
        print(f"[Crew] Groq call failed: {e}")
    return ""


# ── Prompt builders ──────────────────────────────────────────────────────────
def _build_forensic_prompt(case_file: dict) -> str:
    """Combined prompt for ML validation + scam type classification."""
    similar_text = ""
    for i, sc in enumerate(case_file.get("similar_cases", []), 1):
        similar_text += (
            f"\nSimilar Case {i}: {sc['scam_type']} "
            f"(similarity: {sc['similarity']:.0%})\n"
            f"Preview: {sc['text_preview'][:150]}...\n"
        )

    return (
        f"Analyze this call transcript flagged by our ML vishing detection model.\n\n"
        f"ML VERDICT: {case_file['ml_label'].upper()}\n"
        f"ML CONFIDENCE: {case_file['ml_score']:.1%}\n"
        f"FLAGGED KEYWORDS: {', '.join(case_file.get('flagged_keywords', []))}\n\n"
        f"TRANSCRIPT:\n\"{case_file['transcript'][:2000]}\"\n\n"
        f"SIMILAR CASES:{similar_text if similar_text else ' None.'}\n\n"
        f"1. Is the ML flag VALID or FALSE POSITIVE? (1-2 sentences)\n"
        f"2. Classify as: Bank Impersonation, OTP Fraud, Tech Support Scam, "
        f"Government Impersonation, Authority Threat, Prize/Lottery Scam, "
        f"Refund Scam, Investment Fraud, General Vishing, or Legitimate Call. "
        f"(1-2 sentences why)\n"
    )


def _build_guardian_prompt(case_file: dict, forensic_output: str) -> str:
    """Combined prompt for tactic detection + final verdict."""
    return (
        f"You are writing a safety advisory for a non-technical user.\n\n"
        f"ML MODEL: {case_file['ml_label'].upper()} ({case_file['ml_score']:.0%})\n"
        f"ML P(VISHING): {case_file.get('vishing_probability', case_file['ml_score']):.0%}\n"
        f"FORENSIC ANALYSIS:\n{forensic_output[:800]}\n\n"
        f"TRANSCRIPT:\n\"{case_file['transcript'][:1500]}\"\n\n"
        f"Identify present tactics: URGENCY, AUTHORITY, FEAR, ISOLATION, RECIPROCITY\n\n"
        f"Return ONLY valid JSON. Choose exactly one allowed value for each enum field:\n"
        f'{{"verdict":"HANG UP NOW",'
        f'"risk_level":"high",'
        f'"ml_alignment":"supports_ml",'
        f'"scam_type":"type",'
        f'"tactics":["URGENCY"],'
        f'"explanation":"2-3 simple sentences",'
        f'"action_steps":["step 1","step 2","step 3"]}}\n'
    )


# ── Output parser ────────────────────────────────────────────────────────────
def _parse_guardian_output(raw_output: str) -> dict:
    """Parse the Safety Guardian's structured output into a dict."""
    result = {
        "verdict": "UNCERTAIN",
        "risk_level": "medium",
        "ml_alignment": "insufficient_evidence",
        "scam_type": "Unknown",
        "tactics": [],
        "explanation": "",
        "action_steps": [],
    }

    text = str(raw_output)
    json_text = text.strip()
    if json_text.startswith("```"):
        json_text = re.sub(r"^```(?:json)?\s*", "", json_text, flags=re.IGNORECASE)
        json_text = re.sub(r"\s*```$", "", json_text)

    try:
        parsed = json.loads(json_text)
        result["verdict"] = str(parsed.get("verdict") or result["verdict"]).strip()
        result["risk_level"] = str(parsed.get("risk_level") or result["risk_level"]).strip().lower()
        result["ml_alignment"] = str(parsed.get("ml_alignment") or result["ml_alignment"]).strip().lower()
        if "|" in result["verdict"]:
            result["verdict"] = "UNCERTAIN"
        if "|" in result["risk_level"]:
            result["risk_level"] = "medium"
        if "|" in result["ml_alignment"]:
            result["ml_alignment"] = "insufficient_evidence"
        result["scam_type"] = str(parsed.get("scam_type") or result["scam_type"]).strip()
        tactics = parsed.get("tactics") or []
        if isinstance(tactics, str):
            tactics = [t.strip() for t in tactics.split(",") if t.strip()]
        result["tactics"] = tactics[:8] if isinstance(tactics, list) else []
        steps = parsed.get("action_steps") or []
        result["action_steps"] = steps[:5] if isinstance(steps, list) else []
        result["explanation"] = str(parsed.get("explanation") or "").strip()
        return result
    except Exception:
        pass

    m = re.search(r"VERDICT:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["verdict"] = m.group(1).strip()

    m = re.search(r"RISK_LEVEL:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["risk_level"] = m.group(1).strip().lower()

    m = re.search(r"ML_ALIGNMENT:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["ml_alignment"] = m.group(1).strip().lower()

    m = re.search(r"SCAM_TYPE:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["scam_type"] = m.group(1).strip()

    m = re.search(r"TACTICS:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        tactics_str = m.group(1).strip()
        result["tactics"] = [t.strip() for t in tactics_str.split(",") if t.strip()]

    m = re.search(r"EXPLANATION:\s*(.+?)(?:ACTION_STEPS|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        result["explanation"] = m.group(1).strip()

    action_idx = text.upper().find("ACTION_STEPS")
    if action_idx >= 0:
        action_text = text[action_idx:]
        steps = re.findall(r"^-\s*(.+)$", action_text, re.MULTILINE)
        result["action_steps"] = steps[:5]

    return result


# ── Main entry point ─────────────────────────────────────────────────────────
async def run_crew(case_file: dict, model: str = DEFAULT_MODEL) -> dict:
    """
    Run the 2-agent analysis using Groq Cloud API.

    Flow:
      1. Forensic prompt → Groq (ML validation + scam classification)
      2. Guardian prompt → Groq (uses forensic output + produces verdict)
      Total: 2 LLM calls, zero local compute overhead.

    Parameters
    ----------
    case_file : dict with transcript, ml_score, ml_label, etc.
    model     : Groq model ID (default: llama-3.3-70b-versatile)

    Returns
    -------
    dict with: verdict, scam_type, tactics, explanation, action_steps
    """
    if not check_groq_available():
        return {
            "verdict": "LLM UNAVAILABLE",
            "risk_level": "medium",
            "ml_alignment": "insufficient_evidence",
            "scam_type": "Unknown",
            "tactics": [],
            "explanation": (
                "The AI analysis engine (Groq API) is not reachable. "
                "The result shown is based on ML model analysis only. "
                "Check your GROQ_API_KEY in .env to enable full hybrid analysis."
            ),
            "action_steps": [
                "Review the ML model's verdict and confidence score",
                "If flagged as vishing, exercise caution",
                "Check Groq API key configuration for full AI-powered analysis",
            ],
        }

    try:
        return await _run_async_pipeline(case_file, model)
    except Exception as e:
        return {
            "verdict": "ANALYSIS ERROR",
            "risk_level": "medium",
            "ml_alignment": "insufficient_evidence",
            "scam_type": "Unknown",
            "tactics": [],
            "explanation": f"AI analysis error: {str(e)[:200]}. ML result is still valid.",
            "action_steps": [
                "Review the ML model's verdict above",
                "If flagged as vishing, do not share personal information",
                "Contact your bank directly using official numbers",
            ],
        }


async def _run_async_pipeline(case_file: dict, model: str) -> dict:
    """
    Async pipeline: Forensic → Guardian (sequential, each is an ultra-fast
    Groq API call with sub-second latency).
    """
    # Step 1: Forensic analysis
    forensic_prompt = _build_forensic_prompt(case_file)
    forensic_output = await _groq_generate(forensic_prompt, model, timeout=45.0)

    if not forensic_output.strip():
        forensic_output = f"ML flag {case_file['ml_label'].upper()} at {case_file['ml_score']:.0%} confidence."

    # Step 2: Guardian verdict (uses forensic output as context)
    guardian_prompt = _build_guardian_prompt(case_file, forensic_output)
    guardian_output = await _groq_generate(guardian_prompt, model, timeout=45.0)

    if not guardian_output.strip():
        return {
            "verdict": case_file["ml_label"].upper(),
            "risk_level": "medium",
            "ml_alignment": "insufficient_evidence",
            "scam_type": "Unknown",
            "tactics": [],
            "explanation": forensic_output[:300],
            "action_steps": ["Review the ML verdict", "Exercise caution if flagged"],
        }

    return _parse_guardian_output(guardian_output)
