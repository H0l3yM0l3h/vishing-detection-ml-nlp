import streamlit as st
from pathlib import Path
import joblib
import numpy as np
import tensorflow as tf 
from tensorflow.keras.models import load_model

# ===============================
# CACHED MODEL LOADING
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

@st.cache_resource
def load_resources():
    # keep this if your app uses it elsewhere
    vectorizer = joblib.load(MODELS_DIR / "vectorizer.pkl")

    models = {
        "SVM": joblib.load(MODELS_DIR / "svm_model.pkl"),
        "Logistic Regression": joblib.load(MODELS_DIR / "logistic_regression_model.pkl"),
        "Random Forest": joblib.load(MODELS_DIR / "rf_model.pkl"),
    }

    # you can load .h5 or .keras, either is fine
    nn_model = load_model(MODELS_DIR / "neural_network.keras")
    return vectorizer, models, nn_model

vectorizer, models, nn_model = load_resources()

# ===============================
# EXPLAINABILITY
# ===============================
def explain_prediction(model, X, feature_names, top_n=5):
    """
    model: LR pipeline or Calibrated SVM
    X: sparse vector from the matching tfidf
    feature_names: from the matching tfidf
    """
    # --- get coef aligned with the model ---
    if hasattr(model, "named_steps"):
        # Logistic Regression pipeline
        clf = model.named_steps["clf"]
        coef = clf.coef_[0]
    else:
        # CalibratedClassifierCV (SVM)
        base = model.calibrated_classifiers_[0].estimator
        clf = base.named_steps["clf"]
        coef = clf.coef_[0]

    # --- only use indices that exist in both feature_names and coef ---
    limit = min(len(feature_names), len(coef))
    indices = X.nonzero()[1]
    indices = [i for i in indices if i < limit]

    contributions = {feature_names[i]: float(coef[i]) for i in indices}

    return sorted(
        contributions.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:top_n]

# ===============================
# INSUFFICIENT EVIDENCE HELPER
# ===============================
def insufficient_evidence(text, confidence, min_words=5, min_conf=0.70):
    word_count = len(text.strip().split())
    if word_count < min_words:
        return True, "Input too short for reliable analysis"
    if confidence < min_conf:
        return True, "Model confidence below reliable threshold"
    return False, ""

# ===============================
# MAIN APP RENDER
# ===============================
def render_app():
    st.set_page_config(page_title="Vishing Detection", layout="centered")

    st.title(" Vishing Detection Using ML & NLP")

    st.info(
        "Models trained on English Dataset. "
        "Other languages are for demonstration only."
    )

    model_choice = st.selectbox(
        "Select model",
        ["SVM", "Logistic Regression", "Random Forest", "Neural Network"]
    )

    text = st.text_area(
        "Paste call transcript",
        height=180,
        placeholder="This is the bank security department..."
    )

    if st.button(" Analyze"):
        if not text.strip():
            st.warning("Please enter a transcript.")
            return

        # ===============================
        # MODEL INFERENCE (FIXED)
        # ===============================
        if model_choice == "Neural Network":
            # ✅ FIX: feed tf.string tensor, not numpy object/list
            x_nn = tf.constant([text])  # shape (1,), dtype string
            prob = float(nn_model.predict(x_nn, verbose=0).reshape(-1)[0])

            label = "vishing" if prob >= 0.5 else "safe"
            confidence = prob if label == "vishing" else 1.0 - prob

        else:
            model = models[model_choice]
            label = model.predict([text])[0]
            confidence = (
                float(np.max(model.predict_proba([text])))
                if hasattr(model, "predict_proba")
                else 0.5
            )

        # ===============================
        # RESULT LOGIC
        # ===============================
        is_insufficient, reason = insufficient_evidence(text, confidence)

        if is_insufficient:
            st.warning(f"⚠️ Insufficient evidence — {reason}")
        else:
            if label == "vishing":
                st.error(f"⚠️ VISHING — Confidence: {confidence:.2%}")
            else:
                st.success(f"✅ SAFE — Confidence: {confidence:.2%}")

        # ===============================
        # EXPLANATION (LINEAR MODELS ONLY)
        # ===============================
        if model_choice in ["SVM", "Logistic Regression"] and not is_insufficient:
            st.subheader("🔍 Explanation")

            if model_choice == "Logistic Regression":
                # ✅ use TF-IDF INSIDE LR pipeline
                lr_model = models["Logistic Regression"]
                tfidf = lr_model.named_steps["tfidf"]
                X = tfidf.transform([text])
                feature_names = tfidf.get_feature_names_out()
                expl_model = lr_model

            else:
                # ✅ use TF-IDF INSIDE calibrated SVM pipeline
                svm_model = models["SVM"]
                base = svm_model.calibrated_classifiers_[0].estimator
                tfidf = base.named_steps["tfidf"]
                X = tfidf.transform([text])
                feature_names = tfidf.get_feature_names_out()
                expl_model = svm_model

            for term, weight in explain_prediction(expl_model, X, feature_names, top_n=5):
                st.write(f"- **{term}** ({weight:.3f})")
