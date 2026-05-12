"""
models_loader.py — ML model loading for ShieldGuard backend
=============================================================
Loads the production SVM model used by the deployed FastAPI app.

[v3 update - 2026-04-29]
  Active model layout:

    models/
      svm_model.pkl            <- PROMOTED: SVM v3
                                  (FeatureUnion char+word TF-IDF, C=2.0,
                                   Lemmatization, train-only augmentation,
                                   validation-tuned threshold=0.80)
      svm_model_metadata.json  <- v3 training metrics and threshold metadata

    models/legacy/
      svm_model_v1.pkl         <- Original baseline SVM
      logistic_regression_model_v1.pkl
      rf_model_v1.pkl
      vectorizer_v1.pkl        <- Standalone TF-IDF (v1 only)
      neural_network_v1.h5
      neural_network.keras
      svm_model_v2.pkl

  NOTE: The v3 SVM pipeline embeds its own FeatureUnion (char_wb + word
  TF-IDF) internally, so vectorizer.pkl is no longer required at inference
  time.  Legacy LR/RF/NN artifacts are kept for documentation and comparison,
  but they are not loaded by the deployed application.
"""

import logging
from pathlib import Path

import joblib

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
      nn_model      : None; legacy neural networks are not loaded in production
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

    nn_model = None

    return vectorizer, ml_models, nn_model


# NOTE: load_whisper() was removed in v3.4 (2026-05-05).
# Whisper transcription is now handled by Groq API (whisper-large-v3-turbo).
# No local PyTorch model loading is required.
