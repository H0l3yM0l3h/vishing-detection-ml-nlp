"""
crew.py — Direct async Ollama execution for ShieldGuard Phase 2
=================================================================
[v3.3 Speed Optimisation] Replaced CrewAI with direct Ollama HTTP calls.

Why this is faster:
  - CrewAI adds ~5-10s of framework overhead per run (agent init, delegation,
    LangChain middleware, output parsing, memory management).
  - Direct HTTP calls to Ollama's /api/generate endpoint eliminate all of this.
  - asyncio.gather() runs both prompts TRULY in parallel if Ollama supports
    concurrent requests (OLLAMA_NUM_PARALLEL >= 2).
  - Even without parallel Ollama, the overhead reduction alone saves 5-10s.

Architecture:
  Prompt 1 (Forensic):  ML validation + scam classification     ─┐
  Prompt 2 (Guardian):  Tactic detection + verdict + actions     ─┤ parallel
                                                                  ↓
  Final parse + cross-check                                      → result
"""

import json
import re
import asyncio
import httpx

from llm_config import check_ollama_available, OLLAMA_BASE_URL, MODEL_PRESETS, DEFAULT_MODEL


# ── Ollama generation ────────────────────────────────────────────────────────
async def _ollama_generate(prompt: str, model: str, timeout: float = 60.0) -> str:
    """
    Call Ollama's /api/generate endpoint directly.
    Returns the generated text, or an empty string on failure.
    """
    preset = MODEL_PRESETS.get(model, {"num_ctx": 4096, "temperature": 0.1, "num_predict": 512})
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": preset.get("temperature", 0.1),
            "num_ctx":     preset.get("num_ctx", 4096),
            "num_predict": preset.get("num_predict", 512),
        },
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "")
    except Exception as e:
        print(f"[Crew] Ollama call failed: {e}")
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
    Run the 2-agent analysis using direct Ollama HTTP calls.

    Flow:
      1. Forensic prompt → Ollama (ML validation + scam classification)
      2. Guardian prompt → Ollama (uses forensic output + produces verdict)
      Total: 2 LLM calls (down from 4 in CrewAI), zero framework overhead.

    Parameters
    ----------
    case_file : dict with transcript, ml_score, ml_label, etc.
    model     : Ollama model tag (default: llama3.2:3b)

    Returns
    -------
    dict with: verdict, scam_type, tactics, explanation, action_steps
    """
    if not check_ollama_available():
        return {
            "verdict": "LLM UNAVAILABLE",
            "risk_level": "medium",
            "ml_alignment": "insufficient_evidence",
            "scam_type": "Unknown",
            "tactics": [],
            "explanation": (
                "The AI analysis engine (Ollama) is not reachable. "
                "The result shown is based on ML model analysis only. "
                "Start Ollama to enable full hybrid analysis."
            ),
            "action_steps": [
                "Review the ML model's verdict and confidence score",
                "If flagged as vishing, exercise caution",
                "Start Ollama for full AI-powered analysis",
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
    Async pipeline: Forensic → Guardian (sequential, but each is a fast
    direct HTTP call with zero framework overhead).
    """
    # Step 1: Forensic analysis
    forensic_prompt = _build_forensic_prompt(case_file)
    forensic_output = await _ollama_generate(forensic_prompt, model, timeout=45.0)

    if not forensic_output.strip():
        forensic_output = f"ML flag {case_file['ml_label'].upper()} at {case_file['ml_score']:.0%} confidence."

    # Step 2: Guardian verdict (uses forensic output as context)
    guardian_prompt = _build_guardian_prompt(case_file, forensic_output)
    guardian_output = await _ollama_generate(guardian_prompt, model, timeout=45.0)

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
