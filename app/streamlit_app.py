import streamlit as st
from pathlib import Path
import joblib
import numpy as np
from tensorflow.keras.models import load_model

# ===============================
# CACHED MODEL LOADING
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

@st.cache_resource
def load_resources():
    vectorizer = joblib.load(MODELS_DIR / "vectorizer.pkl")
    models = {
        "SVM": joblib.load(MODELS_DIR / "svm_model.pkl"),
        "Logistic Regression": joblib.load(MODELS_DIR / "logistic_regression_model.pkl"),
        "Random Forest": joblib.load(MODELS_DIR / "rf_model.pkl"),
    }
    nn_model = load_model(MODELS_DIR / "neural_network.h5")
    return vectorizer, models, nn_model

vectorizer, models, nn_model = load_resources()

# ===============================
# EXPLAINABILITY
# ===============================
def explain_prediction(model, vectorizer, X, top_n=5):
    feature_names = vectorizer.get_feature_names_out()
    coef = model.coef_[0]
    indices = X.nonzero()[1]

    contributions = {
        feature_names[i]: coef[i]
        for i in indices
    }

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

    st.title("🎯 Vishing Detection Using ML & NLP")

    st.info(
        "Models trained on **KorCCVi**. "
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

    if st.button("🔍 Analyze"):
        if not text.strip():
            st.warning("Please enter a transcript.")
            return

        # ===============================
        # MODEL INFERENCE (FIXED)
        # ===============================
        if model_choice == "Neural Network":
            X = vectorizer.transform([text])
            probs = nn_model.predict(X.toarray(), verbose=0)
            pred = np.argmax(probs)
            confidence = float(np.max(probs))
            label = "vishing" if pred == 1 else "safe"

        else:
            model = models[model_choice]
            label = model.predict([text])[0]  # ✅ RAW TEXT
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
            X = vectorizer.transform([text])
            st.subheader("🔍 Explanation")
            for term, weight in explain_prediction(models[model_choice], vectorizer, X):
                st.write(f"- **{term}** ({weight:.3f})")
