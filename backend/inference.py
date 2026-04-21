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
import numpy as np
import tensorflow as tf


# ═══════════════════════════════════════════════
# VISHING PATTERNS (exact copy)
# ═══════════════════════════════════════════════
VISHING_PATTERNS = [
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
]


def detect_suspicious_phrases(text: str) -> list:
    """Detect suspicious phrases using regex patterns. VERBATIM from streamlit_app.py."""
    found = []
    for pat in VISHING_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if m.group() not in found:
                found.append(m.group())
    return found


def build_highlighted_transcript(text: str, phrases: list) -> str:
    """Build transcript with <mark> highlighted phrases. VERBATIM from streamlit_app.py."""
    result = text
    for p in sorted(phrases, key=len, reverse=True):
        result = re.sub(re.escape(p),
                        f'<mark class="hlt">{p}</mark>',
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
        feature_names, X = _get_feature_names_and_matrix(m, text)
        return explain_prediction(m, X, feature_names)
    except Exception:
        return []


# ═══════════════════════════════════════════════
# HELPERS (exact copy)
# ═══════════════════════════════════════════════
def insufficient_evidence(text: str, confidence: float,
                           min_words: int = 5, min_conf: float = 0.70):
    """Check if evidence is insufficient. VERBATIM from streamlit_app.py."""
    if len(text.strip().split()) < min_words:
        return True, "Transcript too short — provide more context for reliable analysis"
    if confidence < min_conf:
        return True, f"Confidence below threshold ({int(confidence*100)}% < 70%)"
    return False, ""


def run_inference(text: str, model_choice: str, models: dict, nn_model):
    """
    Run ML inference. Same logic as streamlit_app.py.
    Takes models dict and nn_model as parameters instead of globals.
    """
    if model_choice == "Neural Network":
        prob  = float(nn_model.predict(tf.constant([text]), verbose=0).reshape(-1)[0])
        label = "vishing" if prob >= 0.5 else "safe"
        conf  = prob if label == "vishing" else 1.0 - prob
    else:
        m     = models[model_choice]
        label = m.predict([text])[0]
        conf  = float(np.max(m.predict_proba([text]))) if hasattr(m, "predict_proba") else 0.5
    return label, conf


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
