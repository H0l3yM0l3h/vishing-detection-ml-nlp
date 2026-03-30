"""Full integration test for all Phase 2 modules."""
import os
os.environ["HF_HOME"] = r"d:\FYP1\.hf_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"d:\FYP1\.hf_cache\sentence_transformers"

import sys
sys.path.insert(0, r"d:\FYP1\VishingDetection\app")

print("=== Phase 2 Module Tests ===\n")

# 1. LLM Config
from llm_config import check_ollama_available, get_available_models
ollama_ok = check_ollama_available()
models = get_available_models()
print(f"[1] llm_config: Ollama={ollama_ok}, Models={models}")

# 2. RAG Module (already tested above)
from rag_module import ensure_scam_library, query_similar_scams
count = ensure_scam_library()
print(f"[2] rag_module: {count} entries indexed")

# 3. Agent Definitions
from agents.agent_definitions import (
    create_technical_auditor, create_pattern_detective,
    create_psychology_profiler, create_safety_guardian,
)
print("[3] agent_definitions: All 4 agents importable")

# 4. Crew
from agents.crew import run_crew
print("[4] crew: Import OK")

# 5. Hybrid Engine
from hybrid_engine import run_hybrid_analysis
print("[5] hybrid_engine: Import OK")

print("\n=== All imports passed! ===\n")

# 6. Test hybrid engine with ML-only path (score < 0.45)
result_low = run_hybrid_analysis(
    transcript="Hello, how are you today?",
    model_choice="SVM",
    ml_label="safe",
    ml_score=0.30,
    top_keywords=[],
)
print(f"[6] Low-score test: source={result_low['source']}, verdict={result_low['verdict']}")
assert result_low["source"] == "ml_only", "Should be ML-only for low scores"

# 7. Test hybrid engine with high score (triggers RAG + LLM)
print("\n[7] High-score test (will trigger RAG + LLM)...")
result_high = run_hybrid_analysis(
    transcript="Your bank account has been suspended. Verify your OTP now or face legal action.",
    model_choice="SVM",
    ml_label="vishing",
    ml_score=0.94,
    top_keywords=[("verify", 0.8), ("account", 0.7), ("suspended", 0.6)],
    suspicious_phrases=["account has been suspended", "verify your OTP"],
)
print(f"    source={result_high['source']}")
print(f"    verdict={result_high['verdict']}")
print(f"    scam_type={result_high.get('scam_type')}")
print(f"    tactics={result_high.get('tactic')}")
print(f"    similar_cases={len(result_high.get('similar_cases', []))} found")
if result_high.get("explanation"):
    print(f"    explanation={result_high['explanation'][:150]}...")

print("\n=== All tests passed! ===")
