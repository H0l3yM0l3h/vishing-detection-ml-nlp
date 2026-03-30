"""
crew.py — CrewAI crew assembly and execution for ShieldGuard Phase 2
=====================================================================
Assembles the 4 agents into a sequential crew and runs analysis.
"""

import json
import re
from crewai import Task, Crew, Process

from agents.agent_definitions import (
    create_technical_auditor,
    create_pattern_detective,
    create_psychology_profiler,
    create_safety_guardian,
)
from llm_config import check_ollama_available


def _build_audit_prompt(case_file: dict) -> str:
    return (
        f"Analyze this call transcript that was flagged by our ML vishing detection model.\n\n"
        f"ML MODEL VERDICT: {case_file['ml_label'].upper()}\n"
        f"ML CONFIDENCE SCORE: {case_file['ml_score']:.1%}\n"
        f"FLAGGED KEYWORDS: {', '.join(case_file.get('flagged_keywords', []))}\n\n"
        f"TRANSCRIPT:\n\"{case_file['transcript'][:2000]}\"\n\n"
        f"Based on the transcript content and sentence structure, is the ML flag "
        f"VALID or is it likely a FALSE POSITIVE? Explain your reasoning in 2-3 sentences."
    )


def _build_pattern_prompt(case_file: dict) -> str:
    similar_text = ""
    for i, sc in enumerate(case_file.get("similar_cases", []), 1):
        similar_text += (
            f"\nSimilar Case {i}: {sc['scam_type']} "
            f"(similarity: {sc['similarity']:.0%})\n"
            f"Preview: {sc['text_preview'][:150]}...\n"
        )

    return (
        f"Classify this call transcript into a specific scam type.\n\n"
        f"TRANSCRIPT:\n\"{case_file['transcript'][:2000]}\"\n\n"
        f"SIMILAR HISTORICAL CASES FROM OUR DATABASE:{similar_text if similar_text else ' None found.'}\n\n"
        f"Classify this call as one of: Bank Impersonation, OTP Fraud, Tech Support Scam, "
        f"Government Impersonation, Authority Threat, Prize/Lottery Scam, Refund Scam, "
        f"Investment Fraud, or General Vishing.\n"
        f"State the scam type and explain in 2-3 sentences why this classification fits."
    )


def _build_psych_prompt(case_file: dict) -> str:
    return (
        f"Analyze this call transcript for social engineering manipulation tactics.\n\n"
        f"TRANSCRIPT:\n\"{case_file['transcript'][:2000]}\"\n\n"
        f"Identify which of these tactics are present:\n"
        f"- URGENCY: Time pressure (within 24 hours, immediately, right now)\n"
        f"- AUTHORITY: Impersonating officials (bank security, police, government)\n"
        f"- FEAR: Threats of consequences (account suspended, legal action, arrest)\n"
        f"- ISOLATION: Preventing help-seeking (do not tell anyone, keep confidential)\n"
        f"- RECIPROCITY: Offering rewards (refund, prize, you've been selected)\n\n"
        f"For each tactic found, quote the specific phrase from the transcript that "
        f"demonstrates it. List ONLY the tactics that are actually present."
    )


def _build_guardian_prompt(case_file: dict) -> str:
    return (
        f"You are writing a safety advisory for a non-technical user about a phone call "
        f"they received. Based on all the analysis from the team:\n\n"
        f"ML MODEL says: {case_file['ml_label'].upper()} ({case_file['ml_score']:.0%} confidence)\n"
        f"Use the Technical Auditor's validation, Pattern Detective's classification, "
        f"and Psychology Profiler's tactic analysis from previous agents.\n\n"
        f"Write your response in this EXACT format:\n"
        f"VERDICT: [HANG UP NOW / EXERCISE CAUTION / CALL APPEARS SAFE]\n"
        f"SCAM_TYPE: [the classified scam type]\n"
        f"TACTICS: [comma-separated list of detected tactics]\n"
        f"EXPLANATION: [2-3 simple sentences explaining why this call is dangerous or safe. "
        f"Use plain language a grandparent would understand. No technical terms.]\n"
        f"ACTION_STEPS:\n"
        f"- [action step 1]\n"
        f"- [action step 2]\n"
        f"- [action step 3]\n"
    )


def _parse_guardian_output(raw_output: str) -> dict:
    """Parse the Safety Guardian's structured output into a dict."""
    result = {
        "verdict": "UNCERTAIN",
        "scam_type": "Unknown",
        "tactics": [],
        "explanation": "",
        "action_steps": [],
    }

    # Handle CrewAI output objects
    text = str(raw_output)

    # Parse VERDICT
    m = re.search(r"VERDICT:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["verdict"] = m.group(1).strip()

    # Parse SCAM_TYPE
    m = re.search(r"SCAM_TYPE:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        result["scam_type"] = m.group(1).strip()

    # Parse TACTICS
    m = re.search(r"TACTICS:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        tactics_str = m.group(1).strip()
        result["tactics"] = [t.strip() for t in tactics_str.split(",") if t.strip()]

    # Parse EXPLANATION
    m = re.search(r"EXPLANATION:\s*(.+?)(?:ACTION_STEPS|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        result["explanation"] = m.group(1).strip()

    # Parse ACTION_STEPS
    steps = re.findall(r"^-\s*(.+)$", text, re.MULTILINE)
    # Only grab steps that appear after ACTION_STEPS
    action_idx = text.upper().find("ACTION_STEPS")
    if action_idx >= 0:
        action_text = text[action_idx:]
        steps = re.findall(r"^-\s*(.+)$", action_text, re.MULTILINE)
    result["action_steps"] = steps[:5]  # max 5 steps

    return result


def run_crew(case_file: dict, model: str = "llama3.2:3b") -> dict:
    """
    Assemble and run the 4-agent vishing analysis crew.

    Parameters
    ----------
    case_file : dict with keys:
        transcript, ml_score, ml_label, flagged_keywords, similar_cases
    model : Ollama model tag

    Returns
    -------
    dict with: verdict, scam_type, tactics, explanation, action_steps
    """
    # Build LLM string for CrewAI 1.x: "ollama/model_name"
    llm_str = f"ollama/{model}"

    if not check_ollama_available():
        return {
            "verdict": "LLM UNAVAILABLE",
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
        # Create agents with string-based LLM identifier
        auditor = create_technical_auditor(llm_str)
        detective = create_pattern_detective(llm_str)
        profiler = create_psychology_profiler(llm_str)
        guardian = create_safety_guardian(llm_str)

        # Create tasks
        audit_task = Task(
            description=_build_audit_prompt(case_file),
            expected_output=(
                "A validation statement: ML flag CONFIRMED or UNCERTAIN, "
                "with 2-3 sentences of reasoning."
            ),
            agent=auditor,
        )

        pattern_task = Task(
            description=_build_pattern_prompt(case_file),
            expected_output=(
                "A scam type classification with 2-3 sentences explaining "
                "why this classification fits the transcript."
            ),
            agent=detective,
        )

        psych_task = Task(
            description=_build_psych_prompt(case_file),
            expected_output=(
                "A list of social engineering tactics detected, with "
                "specific quotes from the transcript for each."
            ),
            agent=profiler,
        )

        guardian_task = Task(
            description=_build_guardian_prompt(case_file),
            expected_output=(
                "A structured response with VERDICT, SCAM_TYPE, TACTICS, "
                "EXPLANATION, and ACTION_STEPS in the exact format requested."
            ),
            agent=guardian,
        )

        # Assemble crew
        crew = Crew(
            agents=[auditor, detective, profiler, guardian],
            tasks=[audit_task, pattern_task, psych_task, guardian_task],
            process=Process.sequential,
            verbose=False,
        )

        # Run the crew
        result = crew.kickoff()

        # Parse the final output from Safety Guardian
        return _parse_guardian_output(result)

    except Exception as e:
        return {
            "verdict": "ANALYSIS ERROR",
            "scam_type": "Unknown",
            "tactics": [],
            "explanation": f"AI analysis encountered an error: {str(e)[:200]}. The ML model result is still valid.",
            "action_steps": [
                "Review the ML model's verdict above",
                "If flagged as vishing, do not share personal information",
                "Contact your bank directly using official numbers",
            ],
        }
