"""
models_loader.py — ML model loading for ShieldGuard backend
=============================================================
Extracted from streamlit_app.py. Uses the same loading calls
(joblib.load, tf.keras.models.load_model) with no changes.

[v3 update - 2026-04-29]
  Active model layout:

    models/
      svm_model.pkl            <- PROMOTED: SVM v3
                                  (FeatureUnion char+word TF-IDF, C=2.0,
                                   Lemmatization, train-only augmentation,
                                   validation-tuned threshold=0.80)
      svm_model_metadata.json  <- v3 training metrics and threshold metadata
      neural_network.keras     <- Unchanged

    models/legacy/
      svm_model_v1.pkl         <- Original baseline SVM
      logistic_regression_model_v1.pkl
      rf_model_v1.pkl
      vectorizer_v1.pkl        <- Standalone TF-IDF (v1 only)
      neural_network_v1.h5

  NOTE: The v3 SVM pipeline embeds its own FeatureUnion (char_wb + word
  TF-IDF) internally, so vectorizer.pkl is no longer required at inference
  time.  The vectorizer is loaded optionally below for any downstream code
  that may still reference it; a warning is logged if the file is absent.
"""

import logging
from pathlib import Path

import joblib
from tensorflow.keras.models import load_model

logger = logging.getLogger(__name__)


def load_all_models(models_dir: str | Path) -> tuple:
    """
    Load all ML models from disk.

    Parameters
    ----------
    models_dir : path to the models/ directory

    Returns
    -------
    tuple: (vectorizer, ml_models_dict, nn_model)

      vectorizer    : standalone TfidfVectorizer or None if not present
      ml_models_dict: {"SVM": <pipeline>}
      nn_model      : Keras neural network
    """
    models_dir = Path(models_dir)

    # --- Vectorizer (optional in v3 - baked into SVM FeatureUnion) -----------
    vectorizer_path = models_dir / "vectorizer.pkl"
    if vectorizer_path.exists():
        vectorizer = joblib.load(vectorizer_path)
    else:
        logger.warning(
            "vectorizer.pkl not found in %s. "
            "This is expected for the v3 SVM pipeline which embeds its own "
            "FeatureUnion. Returning None for vectorizer.",
            models_dir,
        )
        vectorizer = None

    # --- Primary ML model (SVM v3) -------------------------------------------
    ml_models = {
        "SVM": joblib.load(models_dir / "svm_model.pkl"),
    }

    # --- Legacy models (Logistic Regression, Random Forest) ------------------
    # These were moved to models/legacy/ in v2. Load them from legacy/ if
    # present so existing API endpoints that reference them do not crash.
    legacy_dir = models_dir / "legacy"
    for name, filename in [
        ("Logistic Regression", "logistic_regression_model_v1.pkl"),
        ("Random Forest",       "rf_model_v1.pkl"),
    ]:
        legacy_path = legacy_dir / filename
        if legacy_path.exists():
            ml_models[name] = joblib.load(legacy_path)
            logger.info("Loaded legacy model '%s' from %s", name, legacy_path)
        else:
            logger.warning(
                "Legacy model '%s' not found at %s — skipping.", name, legacy_path
            )

    # --- Neural Network ------------------------------------------------------
    nn_model = load_model(models_dir / "neural_network.keras", compile=False)

    return vectorizer, ml_models, nn_model


def load_whisper():
    """Load Whisper base model for audio transcription."""
    import whisper
    return whisper.load_model("base")
