"""
models_loader.py — ML model loading for ShieldGuard backend
=============================================================
Extracted from streamlit_app.py. Uses the same loading calls
(joblib.load, tf.keras.models.load_model) with no changes.
"""

from pathlib import Path
import joblib
from tensorflow.keras.models import load_model


def load_all_models(models_dir: str | Path) -> tuple:
    """
    Load all ML models from disk.

    Parameters
    ----------
    models_dir : path to the models/ directory

    Returns
    -------
    (vectorizer, ml_models_dict, nn_model)
    """
    models_dir = Path(models_dir)

    vectorizer = joblib.load(models_dir / "vectorizer.pkl")

    ml_models = {
        "SVM":                 joblib.load(models_dir / "svm_model.pkl"),
        "Logistic Regression": joblib.load(models_dir / "logistic_regression_model.pkl"),
        "Random Forest":       joblib.load(models_dir / "rf_model.pkl"),
    }

    nn_model = load_model(models_dir / "neural_network.keras", compile=False)

    return vectorizer, ml_models, nn_model


def load_whisper():
    """Load Whisper base model for audio transcription."""
    import whisper
    return whisper.load_model("base")
