"""
inference.py — ML inference and explainability for ShieldGuard backend
=======================================================================
All functions are extracted VERBATIM from streamlit_app.py.
The only change: functions take models as parameters instead of globals.

[v2 update] get_explanation and explain_prediction now support the improved
SVM pipeline which uses a FeatureUnion (char_wb + word TF-IDF) instead of
a single TF-IDF step. Feature names are gathered from both transformers and
concatenated to match the combined coefficient vector.
"""

import re
import html
import unicodedata
import numpy as np
import tensorflow as tf

# NLTK lemmatizer — must match the training pipeline exactly
import nltk
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
from nltk.stem import WordNetLemmatizer

_lemmatizer = WordNetLemmatizer()


# ═══════════════════════════════════════════════
# VISHING PATTERNS (exact copy)
# ═══════════════════════════════════════════════
VISHING_PATTERNS = [
    # --- Original patterns ---
    r"account.{0,15}(suspend|block|freeze|close|terminat)",
    r"(verify|confirm).{0,15}(account|identity|detail|information)",
    r"(urgent|immediately|right now|act now|limited time|within \d+ hour)",
    r"(OTP|one.time.password|one time pin|passcode)",
    r"(bank|credit card|debit card).{0,20}(number|detail|info)",
    r"(call back|press \d|dial \d|stay on the line)",
    r"(refund|reward|prize|winner|congratulation|selected|chosen)",
    r"(social security|ic number|passport|nric|mykad)",
    r"(suspicious|unauthorized|unusual|fraudulent).{0,20}(activity|transaction|access|login)",
    r"do not (tell|share|inform|disclose).{0,20}(anyone|anyone else|family|police|authority)",
    r"(legal action|arrested|lawsuit|court order|warrant)",
    r"transfer.{0,20}(fund|money|amount|rm|ringgit|dollar)",
    r"(verify|confirm).{0,10}(now|immediately|urgently|today)",
    r"your (account|card|loan|credit).{0,20}(will be|is being|has been).{0,10}(block|suspend|close|flag)",
    # --- Extended patterns: Tech Support Scams ---
    r"(anydesk|teamviewer|remote.{0,10}access|remote.{0,10}desktop|install.{0,15}software)",
    r"(computer|device|laptop|phone).{0,20}(virus|hack|breach|infect|compromis)",
    r"microsoft.{0,20}(support|security|team|certif)",
    r"(windows|apple|google).{0,20}(techni|support|warn|alert)",
    # --- Extended patterns: Cryptocurrency / Investment Scams ---
    r"(bitcoin|crypto|ethereum|usdt|wallet|blockchain).{0,20}(transfer|send|invest|earn|profit)",
    r"(investment|return|profit|guaranteed).{0,10}(\d+\s*%|percent|risk.free)",
    r"withdraw.{0,20}(fund|earning|profit|crypto|bitcoin)",
    # --- Extended patterns: Government / Authority Impersonation ---
    r"(police|enforcement|custom|immigration|lhdn|irb|inland.revenue).{0,20}(case|invest|action|detain)",
    r"(interpol|fbi|cia|ministry|jabatan|department).{0,20}(notice|order|action|warrant)",
    r"(fine|penalty|compound).{0,20}(pay|settle|rm|ringgit|dollar|immediately)",
    # --- Extended patterns: Isolation / Secrecy ---
    r"do not (hang up|end the call|put.{0,5}phone.{0,5}down)",
    r"(keep.{0,10}confidential|do not.{0,10}discuss|do not.{0,10}mention).{0,20}(call|case|matter)",
]


def detect_suspicious_phrases(text: str) -> list:
    """Detect suspicious phrases using regex patterns. VERBATIM from streamlit_app.py."""
    found = []
    for pat in VISHING_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group() not in found:
                found.append(m.group())
    return found


# ═══════════════════════════════════════════════
# TEXT PREPROCESSING (must mirror training pipeline)
# ═══════════════════════════════════════════════
# CRITICAL: The active SVM model was trained on text that was first
# passed through normalize_english() then lemmatize_text().
# If inference skips these steps, the TF-IDF features will not
# match what the model learned, causing severe accuracy loss.
# These functions are mirrored from the v3 limited-dataset training pipeline.
# ═══════════════════════════════════════════════
def _normalize_english(s: str) -> str:
    """ASCII normalization — identical to training pipeline."""
    s = str(s)
    s = s.replace("\u200b", " ")
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2018", "'").replace("\u2019", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-"))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _lemmatize_text(s: str) -> str:
    """Lemmatize tokens — identical to training pipeline."""
    tokens = s.split()
    tokens = [_lemmatizer.lemmatize(w, pos="v") for w in tokens]
    tokens = [_lemmatizer.lemmatize(w, pos="n") for w in tokens]
    return " ".join(tokens)


def preprocess_text(text: str) -> str:
    """Apply the same preprocessing chain used during active SVM training."""
    return _lemmatize_text(_normalize_english(text))


def build_highlighted_transcript(text: str, phrases: list) -> str:
    """Build transcript with <mark> highlighted phrases. VERBATIM from streamlit_app.py."""
    result = html.escape(text)
    for p in sorted(phrases, key=len, reverse=True):
        safe_phrase = html.escape(p)
        result = re.sub(re.escape(safe_phrase),
                        f'<mark class="hlt">{safe_phrase}</mark>',
                        result, flags=re.IGNORECASE)
    return result


# ═══════════════════════════════════════════════
# EXPLAINABILITY (exact copy)
# ═══════════════════════════════════════════════
def _get_coef_from_svm(m):
    """
    Extract the coefficient vector from a CalibratedClassifierCV SVM pipeline.
    Works for both v1 (Pipeline > CalibratedSVC) and
    v2 (Pipeline > CalibratedClassifierCV wrapping LinearSVC).
    """
    clf_step = m.named_steps["clf"]
    # CalibratedClassifierCV: grab coef from the first calibrated sub-estimator
    if hasattr(clf_step, "calibrated_classifiers_"):
        inner = clf_step.calibrated_classifiers_[0].estimator
        # inner may itself be a LinearSVC directly
        if hasattr(inner, "coef_"):
            return inner.coef_[0]
        # or a Pipeline whose last step is LinearSVC
        if hasattr(inner, "named_steps"):
            last = list(inner.named_steps.values())[-1]
            if hasattr(last, "coef_"):
                return last.coef_[0]
    # Fallback for bare LinearSVC / LogisticRegression in pipeline
    if hasattr(clf_step, "coef_"):
        return clf_step.coef_[0]
    raise ValueError("Cannot extract coefficients from model structure.")


def _get_feature_names_and_matrix(m, text: str):
    """
    Return (feature_names, sparse_X) for the given pipeline and raw text.

    Supports two pipeline structures:
      v1 — Pipeline([('tfidf', TfidfVectorizer), ('clf', ...)])
      v2 — Pipeline([('features', FeatureUnion([('char', ...), ('word', ...)])), ('clf', ...)])
    """
    feat_step = m.named_steps.get("features") or m.named_steps.get("tfidf")

    if feat_step is None:
        raise ValueError("Pipeline has no 'features' or 'tfidf' step.")

    # v2: FeatureUnion with named transformers
    if hasattr(feat_step, "transformer_list"):
        X = feat_step.transform([text])
        # Concatenate feature names from every named transformer
        all_names = []
        for name, transformer in feat_step.transformer_list:
            if hasattr(transformer, "get_feature_names_out"):
                all_names.extend([
                    f"[{name}] {fn}"
                    for fn in transformer.get_feature_names_out()
                ])
        return np.array(all_names), X

    # v1: single TfidfVectorizer
    X = feat_step.transform([text])
    return feat_step.get_feature_names_out(), X


def explain_prediction(model, X, feature_names, top_n=5):
    """
    Extract the top TF-IDF feature contributions for the predicted class.
    Compatible with both v1 (single TF-IDF) and v2 (FeatureUnion) pipelines.
    """
    try:
        coef = _get_coef_from_svm(model)
    except Exception:
        return []
    limit    = min(len(feature_names), len(coef))
    indices  = [i for i in X.nonzero()[1] if i < limit]
    contribs = {feature_names[i]: float(coef[i]) for i in indices}
    return sorted(contribs.items(), key=lambda x: abs(x[1]), reverse=True)[:top_n]


def get_explanation(model_choice: str, text: str, models: dict):
    """
    Get TF-IDF feature explanation for SVM or Logistic Regression.

    [v2 update] Now automatically detects whether the pipeline uses a single
    TF-IDF vectorizer (v1) or a FeatureUnion (v2) and extracts feature names
    and the sparse matrix accordingly.
    """
    if model_choice not in ["SVM", "Logistic Regression"]:
        return []

    m = models.get(model_choice)
    if m is None:
        return []

    try:
        feature_names, X = _get_feature_names_and_matrix(m, preprocess_text(text))
        return explain_prediction(m, X, feature_names)
    except Exception:
        return []


# ═══════════════════════════════════════════════
# HELPERS (exact copy)
# ═══════════════════════════════════════════════
# ── Research-backed threshold configuration ──────────────────────────────────
# VISHING_THRESHOLD = 0.80
#   Justification: In cybersecurity classification (phishing / vishing detection),
#   the operational cost of a False Positive (falsely alarming a legitimate call)
#   is considered higher than a False Negative because it causes "Alert Fatigue".
#   Industry consensus (Provost & Fawcett, 2001; Openlayer, 2023) recommends
#   shifting the decision boundary from 0.50 up to 0.75-0.80 to prioritize
#   Precision over Recall in security-critical applications.
#
# REJECT_THRESHOLD (min_conf) = 0.80  — ASYMMETRIC APPLICATION
#   Justification: Based on Chow's Classification-with-Reject-Option rule
#   (C.K. Chow, 1970). This threshold is applied ASYMMETRICALLY:
#
#   - When the model leans VISHING (label == "vishing"):
#     The model's vishing probability must also be ≥ REJECT_THRESHOLD (0.80)
#     to emit a final vishing verdict. The active v3 model uses the same 0.80
#     value for the decision threshold and reject gate.
#
#   - When the model leans SAFE (label == "safe"):
#     No reject threshold is applied. Marking a call "safe" is a low-risk
#     decision  (the consequence of a False Negative is far less severe than
#     the consequence of a False Positive in user-facing applications).
#     The safe verdict is emitted directly, routing to LLM only if the
#     overall hybrid threshold (ML_THRESHOLD=0.45) is met.
#
#   This asymmetric design is consistent with cost-sensitive reject option
#   literature (Bartlett & Wegkamp, 2008; Geifman & El-Yaniv, 2017).
# ─────────────────────────────────────────────────────────────────────────────
VISHING_THRESHOLD = 0.80   # tuned on v3 validation split (see docs/ml_training_v3_metrics.json)
REJECT_THRESHOLD  = 0.80   # keep reject gate aligned with the validated production threshold
STRONG_SAFE_THRESHOLD = 0.20
STRONG_VISHING_THRESHOLD = 0.85


def insufficient_evidence(text: str, confidence: float,
                           min_words: int = 5, min_conf: float = REJECT_THRESHOLD,
                           label: str = "vishing"):
    """
    Check if evidence is insufficient using an asymmetric research-backed reject threshold.

    The reject threshold (REJECT_THRESHOLD = 0.80) is ONLY applied when the
    model has predicted 'vishing'. This is the correct asymmetric application
    of Chow's Reject Option (1970) for security-critical systems:

      - Vishing predictions below 0.80 confidence → INCONCLUSIVE (escalate to LLM)
      - Safe predictions → pass through directly (low-risk classification)

    Parameters
    ----------
    text       : raw transcript string
    confidence : model's confidence score for the predicted label
    min_words  : minimum number of words required for any verdict
    min_conf   : minimum confidence for conclusive VISHING verdict (default 0.80)
    label      : the predicted label from run_inference ('vishing' or 'safe')
    """
    if len(text.strip().split()) < min_words:
        return True, "Transcript too short — provide more context for reliable analysis"
    # Apply reject threshold only on vishing predictions (asymmetric Chow's rule)
    if label == "vishing" and confidence < min_conf:
        return True, (
            f"Vishing confidence ({int(confidence*100)}%) is below the 80% reliability threshold. "
            "The transcript has been escalated to the AI analysis layer for deeper review."
        )
    return False, ""


def run_inference(text: str, model_choice: str, models: dict, nn_model):
    """
    Run ML inference with research-backed precision thresholding.

    Decision logic:
      - VISHING_THRESHOLD (0.80): The model must achieve at least 80%
        probability of 'vishing' to emit a 'vishing' label. Below this,
        the safe label is returned instead. This reduces False Positives
        and minimizes alert fatigue (Provost & Fawcett, 2001).
      - REJECT_THRESHOLD (0.80): Checked downstream in insufficient_evidence().
        If final confidence < 0.80, the verdict is marked INCONCLUSIVE
        and escalated to the hybrid LLM layer (Chow's Reject Option, 1970).

    Takes models dict and nn_model as parameters instead of globals.
    """
    detail = run_inference_detailed(text, model_choice, models, nn_model)
    return detail["label"], detail["confidence"]

def run_inference_detailed(text: str, model_choice: str, models: dict, nn_model) -> dict:
    """
    Run ML inference and return calibrated ML-first fields.

    The LLM layer should consume these fields without replacing the ML
    probability. This keeps the classic ML/NLP model as the numeric source
    of truth while still allowing AI review for ambiguous cases.
    """
    clean_text = preprocess_text(text)
    vishing_prob = _predict_vishing_probability(clean_text, model_choice, models, nn_model)
    safe_prob = 1.0 - vishing_prob
    label = "vishing" if vishing_prob >= VISHING_THRESHOLD else "safe"
    confidence = vishing_prob if label == "vishing" else safe_prob

    if vishing_prob >= STRONG_VISHING_THRESHOLD:
        risk_band = "high"
    elif vishing_prob >= VISHING_THRESHOLD:
        risk_band = "elevated"
    elif vishing_prob <= STRONG_SAFE_THRESHOLD:
        risk_band = "low"
    else:
        risk_band = "review"

    return {
        "label": label,
        "confidence": float(confidence),
        "vishing_probability": float(vishing_prob),
        "safe_probability": float(safe_prob),
        "risk_band": risk_band,
        "model_choice": model_choice,
    }


def _predict_vishing_probability(clean_text: str, model_choice: str, models: dict, nn_model) -> float:
    """Return P(vishing) for the selected ML/NLP model."""
    if model_choice == "Neural Network":
        return float(nn_model.predict(tf.constant([clean_text]), verbose=0).reshape(-1)[0])

    m = models[model_choice]
    if hasattr(m, "predict_proba"):
        proba = m.predict_proba([clean_text])[0]
        classes = list(m.classes_)
        if "vishing" in classes:
            return float(proba[classes.index("vishing")])
        return float(np.max(proba))

    label = m.predict([clean_text])[0]
    return 1.0 if label == "vishing" else 0.0


# ═══════════════════════════════════════════════
# SAMPLE TRANSCRIPTS (for frontend sample buttons)
# ═══════════════════════════════════════════════
SAMPLE_VISHING = (
    "Hello, this is the Bank Security Department. We have detected suspicious and "
    "unauthorized activity on your account. Your account will be suspended within "
    "24 hours if you do not verify your details immediately. Please provide your "
    "account number, PIN, and the OTP that will be sent to your phone. Do not tell "
    "anyone about this call, including family members. If you fail to verify, legal "
    "action will be taken against you. Press 1 to speak with our security officer now."
)
SAMPLE_SAFE = (
    "Hello, I am calling from the customer service team. I noticed you recently placed "
    "an order with us and wanted to follow up to make sure everything arrived correctly. "
    "There is no urgency at all, this is just a courtesy call. If you have any questions "
    "about your order or need to make a return, please call us back at our official number "
    "listed on our website. Have a great day."
)
