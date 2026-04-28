"""
agent_definitions.py — CrewAI agent definitions for ShieldGuard Phase 2
========================================================================
Defines the 2 specialist agents that form the vishing analysis crew.

[v3.2 Speed Optimisation]
  Consolidated from 4 agents to 2 agents to halve LLM round-trips:
    Agent A — Forensic Analyst (merges Technical Auditor + Pattern Detective)
    Agent B — Safety Guardian  (merges Psychology Profiler + Safety Guardian)

  This reduces total LLM calls from 4 → 2, cutting hybrid analysis time
  by roughly 50% without losing any analytical capability. Each agent
  now covers two complementary roles in a single prompt.

CrewAI 1.x uses string-based LLM identifiers: "ollama/model_name"
"""

from crewai import Agent


def create_forensic_analyst(llm_str: str) -> Agent:
    """Agent A — Validates ML flag AND classifies scam type in one pass."""
    return Agent(
        role="Forensic Analyst",
        goal=(
            "Validate whether the ML model's vishing flag is justified "
            "based on the transcript content and flagged keywords. Then "
            "classify the call into a specific scam type (Bank Impersonation, "
            "OTP Fraud, Tech Support Scam, Government Impersonation, "
            "Authority Threat, Prize Scam, Refund Scam, Investment Fraud, "
            "or General Vishing) using the transcript and similar historical cases."
        ),
        backstory=(
            "You are a cybersecurity forensics expert who validates ML "
            "detection systems AND investigates fraud patterns. You examine "
            "the actual transcript to confirm whether the ML flag is a true "
            "positive or false positive, and you classify the scam methodology "
            "by comparing against known attack patterns."
        ),
        llm=llm_str,
        verbose=False,
        allow_delegation=False,
    )


def create_safety_guardian(llm_str: str) -> Agent:
    """Agent B — Detects tactics AND produces final user-facing verdict."""
    return Agent(
        role="Safety Guardian",
        goal=(
            "Identify the social engineering tactics present in the call "
            "(URGENCY, AUTHORITY, FEAR, ISOLATION, RECIPROCITY), then "
            "consolidate all findings into a clear, simple verdict and "
            "explanation that any non-technical user can understand. "
            "Produce specific action steps the user should take."
        ),
        backstory=(
            "You are a consumer protection specialist and behavioral "
            "psychologist who detects manipulation tactics in phone scams "
            "and translates findings into plain-language safety advisories. "
            "You understand that urgency creates panic, authority creates "
            "compliance, fear overrides rational thinking, and isolation "
            "prevents help-seeking. Every verdict you write could save "
            "someone from losing their life savings."
        ),
        llm=llm_str,
        verbose=False,
        allow_delegation=False,
    )


# ── Legacy compatibility aliases (if any code still references old names) ────
create_technical_auditor   = create_forensic_analyst
create_pattern_detective   = create_forensic_analyst
create_psychology_profiler = create_safety_guardian
