"""
benchmark.py — ShieldGuard Speed & Accuracy Verification
=========================================================
Measures:
  1. ML inference latency  (target: < 200ms per call)
  2. Accuracy on 10 labelled vishing + safe samples
  3. New threshold logic verification (VISHING_THRESHOLD=0.75, REJECT=0.80)
  4. Optional: full /api/analyze round-trip timing (requires backend running)

Usage (from project root):
    .venv\\Scripts\\activate
    python tests/benchmark.py
    python tests/benchmark.py --api   # also runs live HTTP timing
"""

import sys
import time
import argparse
import os
from pathlib import Path

# ── Ensure backend modules are importable ──────────────────────────────────────
_BACKEND = str(Path(__file__).resolve().parent.parent / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

# ── Colours for terminal output ────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

OK   = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}!{RESET}"

SEP = f"{CYAN}{'─'*68}{RESET}"


# ══════════════════════════════════════════════════════════════════════════════
# TEST CASES — 10 labelled samples
# Format: (label, expected_verdict, transcript)
# ══════════════════════════════════════════════════════════════════════════════
TEST_CASES = [
    # ── Clear VISHING (high confidence expected) ──────────────────────────────
    ("vishing", "vishing",
     "This is the bank security department. Your account has been suspended due to suspicious "
     "unauthorized activity. You must verify your details and OTP immediately or legal action "
     "will be taken. Do not tell anyone about this call. Press 1 now."),

    ("vishing", "vishing",
     "Hello, I am calling from LHDN Inland Revenue. There is a warrant for your arrest due to "
     "unpaid taxes. You must settle fine immediately via Bitcoin transfer to avoid detention. "
     "Do not hang up or inform family members."),

    ("vishing", "vishing",
     "Your Microsoft Windows computer has been infected with a dangerous virus. Please install "
     "AnyDesk immediately so our certified technical support team can remotely remove the threat. "
     "Your banking credentials are at risk."),

    ("vishing", "vishing",
     "Congratulations! You have been selected as our lucky prize winner. To claim your reward, "
     "please confirm your credit card number and NRIC immediately. Offer expires within 24 hours."),

    ("vishing", "vishing",
     "This is Interpol. We have detected suspicious activity linked to your account involving "
     "money laundering. To avoid arrest, transfer funds of RM 5000 to our secure account now. "
     "Do not discuss this matter with anyone."),

    # ── Clear SAFE (should NOT be flagged at 0.75 threshold) ──────────────────
    ("safe", "safe",
     "Hello, this is a courtesy call from the pharmacy. Your prescription is ready for pickup. "
     "Please bring your MyKad when you collect it. Our opening hours are 9am to 6pm. Have a great day."),

    ("safe", "safe",
     "Hi, I am calling from the school administration to remind you that the parent-teacher "
     "meeting is scheduled for next Friday at 3pm. No action is required from your side."),

    ("safe", "safe",
     "This is your dentist clinic calling to confirm your appointment tomorrow at 10am. "
     "If you need to reschedule, please call us back at our official number. See you soon."),

    ("safe", "safe",
     "Good afternoon, I am calling from the delivery department. Your parcel has arrived at the "
     "hub and will be delivered tomorrow between 9am and 12pm. You do not need to do anything."),

    ("safe", "safe",
     "Hello, this is customer service following up on your recent feedback. We have resolved the "
     "issue you raised last week. Is there anything else we can help you with today?"),
]

# ── Borderline: should trigger INCONCLUSIVE (low confidence) ─────────────────
BORDERLINE_CASES = [
    ("borderline", "inconclusive",
     "Hi, I need to verify your account details for our records update."),
    ("borderline", "inconclusive",
     "Please call us back regarding your loan application status."),
]


def _fmt_ms(seconds: float) -> str:
    ms = seconds * 1000
    color = GREEN if ms < 200 else (YELLOW if ms < 500 else RED)
    return f"{color}{ms:.1f}ms{RESET}"


def run_ml_benchmark():
    print(f"\n{SEP}")
    print(f"{BOLD}PHASE 1 — Loading ML models{RESET}")
    print(SEP)

    from models_loader import load_all_models
    from inference import (
        run_inference, insufficient_evidence,
        VISHING_THRESHOLD, REJECT_THRESHOLD,
    )

    MODELS_DIR = Path(_BACKEND).parent / "models"
    t0 = time.perf_counter()
    vectorizer, models, nn_model = load_all_models(MODELS_DIR)
    load_time = time.perf_counter() - t0
    print(f"  Models loaded in {_fmt_ms(load_time)}  ({len(models)} classical + 1 neural network)")
    print(f"  Active thresholds: VISHING_THRESHOLD={VISHING_THRESHOLD}, REJECT_THRESHOLD={REJECT_THRESHOLD}")

    # ── Threshold logic verification ──────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"{BOLD}PHASE 2 — Threshold Logic Verification{RESET}")
    print(SEP)
    insuf_true,  _ = insufficient_evidence("hello", 0.60)
    insuf_false, _ = insufficient_evidence("The bank called and asked for my OTP number.", 0.95)
    insuf_short, _ = insufficient_evidence("Hi", 0.99)
    print(f"  {OK if insuf_true  else FAIL}  Conf 0.60 < 0.80 → INCONCLUSIVE  [{insuf_true}]")
    print(f"  {OK if not insuf_false else FAIL}  Conf 0.95 ≥ 0.80 → CONCLUSIVE   [{not insuf_false}]")
    print(f"  {OK if insuf_short else FAIL}  Short text (2 words) → INCONCLUSIVE [{insuf_short}]")

    # ── Accuracy & speed benchmark ────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"{BOLD}PHASE 3 — Accuracy & Speed (10 labelled samples, MODEL=SVM){RESET}")
    print(SEP)

    correct, total = 0, 0
    latencies = []

    for i, (true_label, expected_verdict, transcript) in enumerate(TEST_CASES, 1):
        t0 = time.perf_counter()
        label, conf = run_inference(transcript, "SVM", models, nn_model)
        insuf, _ = insufficient_evidence(transcript, conf, label=label)
        latency = time.perf_counter() - t0
        latencies.append(latency)

        final_verdict = "inconclusive" if insuf else label
        match = (final_verdict == expected_verdict)
        correct += int(match)
        total += 1

        icon = OK if match else FAIL
        conf_str = f"{int(conf*100)}%"
        print(f"  {icon}  [{i:02d}] expected={expected_verdict:12s} got={final_verdict:12s} "
              f"conf={conf_str:5s}  {_fmt_ms(latency)}")

    accuracy = correct / total * 100
    avg_lat  = sum(latencies) / len(latencies)
    max_lat  = max(latencies)

    print(f"\n  Accuracy : {GREEN if accuracy >= 90 else RED}{accuracy:.0f}%{RESET}  ({correct}/{total} correct)")
    print(f"  Avg latency : {_fmt_ms(avg_lat)}")
    print(f"  Max latency : {_fmt_ms(max_lat)}")

    # ── Borderline / INCONCLUSIVE verification ────────────────────────────────
    print(f"\n{SEP}")
    print(f"{BOLD}PHASE 4 — Borderline / INCONCLUSIVE Test{RESET}")
    print(SEP)
    for true_label, expected_verdict, transcript in BORDERLINE_CASES:
        label, conf = run_inference(transcript, "SVM", models, nn_model)
        insuf, reason = insufficient_evidence(transcript, conf)
        final = "inconclusive" if insuf else label
        match = (final == expected_verdict) or insuf  # accept inconclusive OR explicit match
        icon = OK if match else WARN
        print(f"  {icon}  conf={int(conf*100)}%  verdict={final:12s}  \"{transcript[:60]}...\"")

    print()
    return accuracy, avg_lat


def run_api_benchmark(base_url: str = "http://localhost:8000"):
    """Live HTTP round-trip test against the running FastAPI backend."""
    import requests

    print(f"\n{SEP}")
    print(f"{BOLD}PHASE 5 — Live API Round-Trip Timing (requires backend){RESET}")
    print(SEP)

    # Try to get a token
    try:
        r = requests.post(f"{base_url}/api/auth/login",
                          json={"username": "test_bench", "password": "TestBench@123!"},
                          timeout=5)
        if r.status_code not in (200, 401):
            print(f"  {WARN}  Cannot reach backend at {base_url}. Start the server first.")
            return
        if r.status_code == 401:
            # Try register
            r2 = requests.post(f"{base_url}/api/auth/register",
                               json={"username": "test_bench", "password": "TestBench@123!"},
                               timeout=5)
            if r2.status_code not in (200, 409):
                print(f"  {WARN}  Registration failed — skipping live API test.")
                return
            r = requests.post(f"{base_url}/api/auth/login",
                              json={"username": "test_bench", "password": "TestBench@123!"},
                              timeout=5)
        token = r.json().get("token", "")
    except Exception as e:
        print(f"  {WARN}  Backend not reachable: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    vishing_transcript = TEST_CASES[0][2]  # Known vishing
    safe_transcript    = TEST_CASES[5][2]  # Known safe

    for label, transcript in [("VISHING", vishing_transcript), ("SAFE", safe_transcript)]:
        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{base_url}/api/analyze",
                json={"transcript": transcript, "model_choice": "SVM", "input_mode": "text"},
                headers=headers,
                timeout=120,
            )
            latency = time.perf_counter() - t0
            if resp.status_code == 200:
                data = resp.json()
                verdict = data.get("verdict", "?")
                conf    = data.get("confidence", 0)
                source  = data.get("source", "?")
                print(f"  {OK}  [{label:7s}] verdict={verdict:30s} conf={int(conf*100)}%  "
                      f"source={source:7s}  {_fmt_ms(latency)}")
            else:
                print(f"  {FAIL}  [{label:7s}] HTTP {resp.status_code}: {resp.text[:80]}")
        except Exception as e:
            print(f"  {FAIL}  [{label}] Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ShieldGuard speed & accuracy benchmark")
    parser.add_argument("--api", action="store_true",
                        help="Also run live HTTP timing against running backend")
    parser.add_argument("--url", default="http://localhost:8000",
                        help="Backend base URL (default: http://localhost:8000)")
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}{'═'*68}{RESET}")
    print(f"{BOLD}{CYAN}  ShieldGuard — Benchmark & Verification Suite{RESET}")
    print(f"{BOLD}{CYAN}{'═'*68}{RESET}")

    accuracy, avg_lat = run_ml_benchmark()

    if args.api:
        run_api_benchmark(args.url)

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"{BOLD}SUMMARY{RESET}")
    print(SEP)
    acc_col = GREEN if accuracy >= 90 else RED
    lat_col = GREEN if avg_lat < 0.2 else (YELLOW if avg_lat < 0.5 else RED)
    print(f"  ML Accuracy  : {acc_col}{accuracy:.0f}%{RESET}")
    print(f"  Avg Latency  : {lat_col}{avg_lat*1000:.1f}ms{RESET}")
    print(f"  Status       : {''+GREEN+'READY FOR USER TESTING'+RESET if accuracy >= 90 and avg_lat < 0.5 else RED+'NEEDS REVIEW'+RESET}")
    print(f"\n{SEP}\n")
