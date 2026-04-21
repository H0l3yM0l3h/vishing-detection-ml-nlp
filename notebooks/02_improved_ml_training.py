# ==============================================================================
# CELL 1 — HEADER & CHANGELOG
# ==============================================================================
# 02_improved_ml_training.py
# Phase 1 — Improved Machine Learning Pipeline for Vishing Detection (FYP2)
# ==============================================================================
#
# HOW TO USE:
#   Option A — Run as script   : python notebooks/02_improved_ml_training.py
#   Option B — Paste into Jupyter: Copy each CELL block as one notebook cell.
#
# BASELINE REFERENCE (from 01_baseline_text_classification.ipynb):
#   SVM Accuracy: 0.9851 | Balanced Acc: 0.9831 | F1-macro: 0.9809
#
# CHANGELOG — What is New in v2 vs v1 Baseline:
#
#   No.  Improvement                Section   Why It Helps
#   ---  -------------------------  --------  ----------------------------------
#    1   LEMMATIZATION              Cell 3    Normalizes word forms
#        NLTK WordNetLemmatizer               e.g. scammed/scams -> scam
#
#    2   EDA DATA AUGMENTATION      Cell 4    Generates valid new 'safe'
#        Synonym Replacement                  transcripts (not fake TF-IDF vecs)
#        (minority class only)
#
#    3   FEATURE UNION              Cell 6    Char-level (spelling patterns)
#        char_wb TF-IDF (3-5)                 + word bigrams (semantic phrases)
#        + word TF-IDF (1-2)
#
#    4   K-FOLD CROSS-VALIDATION    Cell 7    5 different splits prove model
#        StratifiedKFold, k=5                 is not a lucky 70/30 split
#
#    5   GRIDSEARCH TUNING          Cell 8    Finds optimal SVM C parameter
#        GridSearchCV on C                    for this exact dataset
#
# NOTE ON SMOTE:
#   SMOTE was considered but NOT applied. Reason: SMOTE generates synthetic
#   TF-IDF vectors, not real English sentences. NLP researchers flag this as
#   producing linguistically incoherent synthetic data. Instead, this pipeline
#   uses class_weight="balanced" and EDA synonym replacement, both of which
#   are academically accepted methods for text classification.
#
# ==============================================================================


# ==============================================================================
# CELL 2 — ENVIRONMENT SETUP AND IMPORTS
# ==============================================================================

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONUTF8"]           = "1"
os.environ["PYTHONIOENCODING"]     = "utf-8"

import re
import random
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter

# NLTK — Lemmatization and EDA Synonym Replacement
import nltk
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
nltk.download("punkt",   quiet=True)

from nltk.stem   import WordNetLemmatizer
from nltk.corpus import wordnet

# Scikit-learn
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    GridSearchCV,
    cross_val_score,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline                import Pipeline, FeatureUnion
from sklearn.svm                     import LinearSVC
from sklearn.calibration             import CalibratedClassifierCV
from sklearn.linear_model            import LogisticRegression
from sklearn.ensemble                import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    accuracy_score,
    f1_score,
    balanced_accuracy_score,
)
import joblib

print("=" * 60)
print("  FYP2 - ML Training Pipeline v2")
print("=" * 60)
print("All imports loaded.")
print()


# ==============================================================================
# CELL 3 — LOAD DATASET
# (Identical to v1 — no changes to loading logic)
# ==============================================================================

BASE_DIR  = Path.cwd().parent if Path.cwd().name.lower() == "notebooks" else Path.cwd()
DATA_PATH = BASE_DIR / "data" / "english_dataset_final_v2.csv"

df = pd.read_csv(DATA_PATH)
df["transcript"] = df["transcript"].astype(str)
df["label"]      = df["label"].astype(str).str.lower().str.strip()

print("Dataset loaded:", DATA_PATH)
print("Total rows    :", len(df))
print("Label counts  :")
print(df["label"].value_counts())
print()


# ==============================================================================
# CELL 4 — ENHANCED TEXT PREPROCESSING
# [NEW v2] Lemmatization added on top of original ASCII normalization.
#
# normalize_english() — unchanged from v1 (prevents Windows cp1252 crashes)
# lemmatize_text()    — NEW: collapses different word forms to their root
#                       e.g. "scammed", "scamming", "scams"  -> "scam"
#                            "banking", "banks"              -> "bank"
#                            "suspended", "suspending"       -> "suspend"
#
# WHY LEMMATIZATION MATTERS:
#   Vishing transcripts repeat the same concepts with different conjugations.
#   Lemmatization reduces TF-IDF vocabulary size and concentrates feature
#   weight on the root concept rather than splitting it across word forms.
#   This leads to a denser, more informative feature matrix for the SVM.
# ==============================================================================

lemmatizer = WordNetLemmatizer()


def normalize_english(s):
    """
    Original ASCII normalization from v1 — kept unchanged.
    Prevents .keras save crashes on Windows cp1252 encoding.
    """
    s = str(s)
    s = s.replace("\u200b", " ")
    s = unicodedata.normalize("NFKC", s)
    s = (s.replace("\u2018", "'").replace("\u2019", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-"))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def lemmatize_text(s):
    """
    [NEW v2] Lemmatize each token to its base/root form.

    Two passes are applied:
      Pass 1 (verb)  — "running" -> "run", "suspended" -> "suspend"
      Pass 2 (noun)  — "accounts" -> "account", "banks" -> "bank"

    Running both passes ensures verb and noun forms are both collapsed.
    """
    tokens = s.split()
    tokens = [lemmatizer.lemmatize(w, pos="v") for w in tokens]
    tokens = [lemmatizer.lemmatize(w, pos="n") for w in tokens]
    return " ".join(tokens)


# Apply normalization then lemmatization
df["clean_text"] = (
    df["transcript"]
    .apply(normalize_english)
    .apply(lemmatize_text)
)

# Remove empty rows and exact duplicates
df = df[df["clean_text"].str.len() > 0].reset_index(drop=True)
df = df.drop_duplicates(subset=["clean_text", "label"]).reset_index(drop=True)

print("[v2] Enhanced preprocessing complete.")
print("     Normalization + Lemmatization applied.")
print("     Label counts after dedup:")
print(df["label"].value_counts())
print()


# ==============================================================================
# CELL 5 — EDA: EASY DATA AUGMENTATION
# [NEW v2] Synonym replacement on the minority ('safe') class only.
#
# DESIGN DECISIONS:
#   - SMOTE is NOT used because it generates synthetic TF-IDF vectors,
#     not real English text. Reversed, these vectors produce grammatically
#     incoherent sentences that do not represent real phone calls.
#   - EDA instead generates valid English by replacing words with real
#     WordNet synonyms (e.g. "alert" -> "alarm", "notify" -> "inform").
#   - Augmentation is applied ONLY to the 'safe' minority class.
#   - AUG_RATIO = 0.40 means 40% extra 'safe' samples are generated.
#
# ACADEMIC REFERENCE:
#   Wei & Zou (2019). "EDA: Easy Data Augmentation Techniques for Boosting
#   Performance on Text Classification Tasks." EMNLP-IJCNLP 2019.
# ==============================================================================

RANDOM_SEED       = 42
AUG_RATIO         = 0.40   # Generate 40% more 'safe' samples
SYNONYM_SWAP_RATE = 0.10   # Replace 10% of words per sentence

random.seed(RANDOM_SEED)


def get_synonyms(word):
    """Return a deduplicated list of WordNet synonym strings for a token."""
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            candidate = lemma.name().replace("_", " ")
            if candidate.lower() != word.lower():
                synonyms.add(candidate.lower())
    return list(synonyms)


def eda_synonym_replace(sentence, swap_rate=SYNONYM_SWAP_RATE):
    """
    Easy Data Augmentation — Synonym Replacement.

    Steps:
      1. Split sentence into word tokens.
      2. Randomly select (swap_rate x length) tokens.
      3. For each selected token, look up WordNet synonyms.
      4. If synonyms exist, replace with a random synonym.
      5. Rejoin tokens into a new sentence string.

    Result: A slightly different but semantically valid English sentence.
    """
    words     = sentence.split()
    n_swap    = max(1, int(len(words) * swap_rate))
    indices   = random.sample(range(len(words)), min(n_swap, len(words)))
    new_words = words.copy()

    for i in indices:
        syns = get_synonyms(words[i])
        if syns:
            new_words[i] = random.choice(syns)

    return " ".join(new_words)


# Separate the two classes
safe_df    = df[df["label"] == "safe"].copy()
vishing_df = df[df["label"] == "vishing"].copy()

n_to_generate = int(len(safe_df) * AUG_RATIO)

print("Generating", n_to_generate, "augmented 'safe' samples via EDA ...")

aug_rows = []
for _, row in safe_df.sample(n_to_generate, random_state=RANDOM_SEED).iterrows():
    aug_text = eda_synonym_replace(row["clean_text"])
    aug_rows.append({
        "transcript": aug_text,
        "label":      "safe",
        "clean_text": aug_text,
    })

aug_df       = pd.DataFrame(aug_rows)
df_augmented = pd.concat([df, aug_df], ignore_index=True).reset_index(drop=True)

print()
print("[v2] EDA Augmentation complete.")
print("     Original 'safe'    count :", len(safe_df))
print("     Original 'vishing' count :", len(vishing_df))
print("     New 'safe' generated     :", len(aug_rows))
print("     Final label counts:")
print(df_augmented["label"].value_counts())
print()


# ==============================================================================
# CELL 6 — TRAIN / TEST SPLIT (Stratified 75/25)
# [CHANGE v2] Switched from GroupShuffleSplit (n_splits=1) to stratified
#             train_test_split at 75/25.
#             The K-Fold CV in Cell 7 operates only on X_train internally.
#
# WHY STRATIFY:
#   Ensures the exact class ratio is preserved in both splits, preventing
#   an accidental imbalance in the held-out test set.
# ==============================================================================

X = df_augmented["clean_text"].values
y = df_augmented["label"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.25,
    random_state=RANDOM_SEED,
    stratify=y,
)

print("[v2] Train / Test split (stratified 75/25) complete.")
print("     Train :", Counter(y_train))
print("     Test  :", Counter(y_test))
print()


# ==============================================================================
# CELL 7 — FEATURE ENGINEERING: FeatureUnion (char + word TF-IDF)
# [NEW v2] Combines two complementary TF-IDF vectorizers into one matrix.
#
# VECTORIZER 1 — char_wb (n = 3 to 5):
#   Retained from v1. Excellent for catching morphological patterns,
#   misspellings, and character-level phishing markers.
#
# VECTORIZER 2 — word bigrams (n = 1 to 2):
#   NEW in v2. Captures multi-word semantic phrases critical to vishing:
#   "bank account", "credit card", "urgent action", "act immediately".
#   These phrases are invisible to character-level vectorizers.
#
# FeatureUnion concatenates both matrices horizontally:
#   [char features | word features] = one combined vector per sample.
#
# sublinear_tf = True:
#   Applies log(1 + tf) so extremely common filler words ("the", "a")
#   do not dominate and overpower meaningful phishing keywords.
# ==============================================================================

char_tfidf = TfidfVectorizer(
    analyzer     = "char_wb",
    ngram_range  = (3, 5),
    min_df       = 2,
    max_df       = 0.95,
    max_features = 25000,
    sublinear_tf = True,
)

word_tfidf = TfidfVectorizer(
    analyzer     = "word",
    ngram_range  = (1, 2),
    min_df       = 2,
    max_df       = 0.95,
    max_features = 15000,
    sublinear_tf = True,
)

combined_features = FeatureUnion([
    ("char", char_tfidf),
    ("word", word_tfidf),
])

print("[v2] FeatureUnion configured.")
print("     char_wb TF-IDF  : n-grams (3-5), 25,000 features")
print("     word    TF-IDF  : n-grams (1-2), 15,000 features")
print("     Combined space  : up to 40,000 dimensions")
print()


# ==============================================================================
# CELL 8 — K-FOLD CROSS-VALIDATION (k = 5)
# [NEW v2] StratifiedKFold with n_splits = 5.
#
# HOW IT WORKS:
#   X_train is divided into 5 equal folds. The model trains on 4 folds and
#   tests on the 5th, rotating through all 5 combinations. This produces
#   5 independent F1 scores. We report the mean and standard deviation.
#
# WHY IT MATTERS:
#   - Mean score proves stable average performance across all data partitions.
#   - Low standard deviation proves the model is not overfitting to one split.
#   - Academic reviewers use this to confirm the 98%+ result is genuine.
#
# MODELS BENCHMARKED:
#   SVM (Calibrated LinearSVC)  — primary production model
#   Logistic Regression         — linear comparison baseline
# ==============================================================================

print("=" * 60)
print("  CELL 8: K-FOLD CROSS-VALIDATION (k = 5)")
print("=" * 60)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

cv_models = {
    "SVM (Calibrated)": Pipeline([
        ("features", combined_features),
        ("clf", CalibratedClassifierCV(
            LinearSVC(
                class_weight = "balanced",
                random_state = RANDOM_SEED,
                max_iter     = 3000,
            ),
            method = "sigmoid",
            cv     = 3,
        )),
    ]),
    "Logistic Regression": Pipeline([
        ("features", combined_features),
        ("clf", LogisticRegression(
            class_weight = "balanced",
            max_iter     = 3000,
            random_state = RANDOM_SEED,
        )),
    ]),
}

cv_results = {}

for name, model in cv_models.items():
    print()
    print("  Running 5-fold CV for:", name)
    scores = cross_val_score(
        model, X_train, y_train, cv=skf, scoring="f1_macro", n_jobs=-1
    )
    cv_results[name] = scores
    print("    Fold F1-macro scores :", np.round(scores, 4))
    print("    Mean                 :", round(scores.mean(), 4))
    print("    Std                  :", round(scores.std(), 4), " (lower = more stable)")

print()
print("[v2] K-Fold Cross-Validation complete.")
print()


# ==============================================================================
# CELL 9 — HYPERPARAMETER TUNING: GridSearchCV (SVM C parameter)
# [NEW v2] Automated grid search to find the optimal regularization value C.
#
# WHAT IS C:
#   The SVM regularization parameter C controls the margin/error trade-off.
#   Low  C -> large margin, accepts more errors (may underfit)
#   High C -> small margin, penalizes all errors (may overfit)
#   Finding the optimal C for 1,785 transcripts requires systematic search.
#
# STRATEGY:
#   Step 1 — GridSearchCV is run on a raw LinearSVC (no calibration wrapper)
#             to avoid nested pipeline parameter naming complications.
#   Step 2 — The best C found is then used to train the final
#             CalibratedClassifierCV so predict_proba() is available
#             for the ShieldGuard hybrid engine.
#
# GRID: C in {0.05, 0.1, 0.5, 1.0, 5.0, 10.0}
#       6 values x 5 folds = 30 total training fits
# ==============================================================================

print("=" * 60)
print("  CELL 9: HYPERPARAMETER TUNING — GridSearchCV (SVM)")
print("=" * 60)

param_grid = {
    "clf__C": [0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
}

raw_svm_pipeline = Pipeline([
    ("features", combined_features),
    ("clf", LinearSVC(
        class_weight = "balanced",
        random_state = RANDOM_SEED,
        max_iter     = 3000,
    )),
])

grid_cv = GridSearchCV(
    raw_svm_pipeline,
    param_grid,
    cv      = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
    scoring = "f1_macro",
    n_jobs  = -1,
    verbose = 1,
)

print()
print("  Fitting GridSearchCV (6 C-values x 5 folds = 30 total fits) ...")
grid_cv.fit(X_train, y_train)

best_C     = grid_cv.best_params_["clf__C"]
best_score = grid_cv.best_score_

print()
print("  GridSearchCV complete.")
print("  Best C value       :", best_C)
print("  Best F1-macro (CV) :", round(best_score, 4))

print()
print("  Full Grid Results:")
grid_results_df = pd.DataFrame(grid_cv.cv_results_)
display_cols = ["param_clf__C", "mean_test_score", "std_test_score", "rank_test_score"]
print(grid_results_df[display_cols].sort_values("rank_test_score").to_string(index=False))
print()


# ==============================================================================
# CELL 10 — FINAL MODEL TRAINING (Best Hyperparameters)
# Trains the final production SVM using:
#   - best_C from GridSearchCV
#   - CalibratedClassifierCV (so predict_proba() works in the hybrid engine)
#   - Full FeatureUnion (char_wb TF-IDF + word TF-IDF)
# ==============================================================================

print("=" * 60)
print("  CELL 10: FINAL MODEL — Training with Best Parameters")
print("=" * 60)

final_svm = Pipeline([
    ("features", combined_features),
    ("clf", CalibratedClassifierCV(
        LinearSVC(
            C            = best_C,
            class_weight = "balanced",
            random_state = RANDOM_SEED,
            max_iter     = 3000,
        ),
        method = "sigmoid",
        cv     = 3,
    )),
])

final_svm.fit(X_train, y_train)
pred_final = final_svm.predict(X_test)

acc  = accuracy_score(y_test, pred_final)
bacc = balanced_accuracy_score(y_test, pred_final)
f1m  = f1_score(y_test, pred_final, average="macro")

print()
print("  Classification Report (v2 Final SVM, C =", best_C, "):")
print(classification_report(y_test, pred_final, digits=4))
print("  Accuracy     :", round(acc,  4))
print("  Balanced Acc :", round(bacc, 4))
print("  F1-macro     :", round(f1m,  4))
print()


# ==============================================================================
# CELL 11 — COMPARISON TABLE: Baseline v1 vs Improved v2
# Reports the delta improvement from all 5 changes combined.
# Baseline values are taken from 01_baseline_text_classification.ipynb output.
# ==============================================================================

print("=" * 60)
print("  CELL 11: COMPARISON — Baseline v1 vs Improved v2")
print("=" * 60)

baseline_v1 = {
    "Accuracy":     0.9851,
    "Balanced Acc": 0.9831,
    "F1-macro":     0.9809,
}

improved_v2 = {
    "Accuracy":     round(acc,  4),
    "Balanced Acc": round(bacc, 4),
    "F1-macro":     round(f1m,  4),
}

comparison_df = pd.DataFrame({
    "Metric":      list(baseline_v1.keys()),
    "Baseline v1": list(baseline_v1.values()),
    "Improved v2": list(improved_v2.values()),
})
comparison_df["Delta"] = (
    comparison_df["Improved v2"] - comparison_df["Baseline v1"]
).round(4)
comparison_df["Result"] = comparison_df["Delta"].apply(
    lambda d: "Improved" if d > 0 else ("Lower" if d < 0 else "Same")
)

print()
print(comparison_df.to_string(index=False))
print()


# ==============================================================================
# CELL 12 — VISUALIZATIONS
# Produces three charts and saves them to the notebooks/ directory.
#   12A — Confusion Matrix
#   12B — K-Fold CV per-fold line plot
#   12C — GridSearch C-value vs F1-macro
# ==============================================================================

SAVE_DIR = BASE_DIR / "notebooks"

# --- 12A: Confusion Matrix ---------------------------------------------------

cm   = confusion_matrix(y_test, pred_final, labels=["safe", "vishing"])
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["safe", "vishing"])

fig, ax = plt.subplots(figsize=(6, 5))
disp.plot(ax=ax, colorbar=False)
ax.set_title("Confusion Matrix — SVM v2 (C=" + str(best_C) + ", FeatureUnion, Lemma+EDA)")
plt.tight_layout()
plt.savefig(SAVE_DIR / "confusion_matrix_v2.png", dpi=150)
plt.show()
print("Confusion matrix saved -> confusion_matrix_v2.png")

# --- 12B: K-Fold CV Per-Fold Line Plot ---------------------------------------

fig, ax = plt.subplots(figsize=(9, 4))
fold_x = range(1, 6)
colors = ["#4C72B0", "#DD8452"]

for (name, scores), color in zip(cv_results.items(), colors):
    ax.plot(
        fold_x, scores,
        marker    = "o",
        linewidth = 2,
        color     = color,
        label     = name + "  (mean=" + str(round(scores.mean(), 4)) + ", std=" + str(round(scores.std(), 4)) + ")",
    )

ax.axhline(
    y         = 0.9809,
    color     = "grey",
    linestyle = "--",
    linewidth = 1.2,
    label     = "Baseline v1 SVM (single split F1 = 0.9809)",
)
ax.set_xlabel("Fold Number")
ax.set_ylabel("F1-macro Score")
ax.set_title("5-Fold Cross-Validation — F1-macro per Fold (v2)\nLower std deviation = more stable model")
ax.set_xticks(list(fold_x))
ax.set_ylim(0.88, 1.01)
ax.legend(loc="lower right")
plt.tight_layout()
plt.savefig(SAVE_DIR / "kfold_results_v2.png", dpi=150)
plt.show()
print("K-Fold CV chart saved -> kfold_results_v2.png")

# --- 12C: GridSearch C-value vs F1-macro -------------------------------------

c_values    = grid_results_df["param_clf__C"].astype(float).values
mean_scores = grid_results_df["mean_test_score"].values

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(c_values, mean_scores, marker="s", color="#2ca02c", linewidth=2)
ax.axvline(
    x         = best_C,
    color     = "red",
    linestyle = "--",
    linewidth = 1.5,
    label     = "Best C = " + str(best_C) + "  (F1 = " + str(round(best_score, 4)) + ")",
)
ax.set_xscale("log")
ax.set_xlabel("C (Regularization Strength — log scale)")
ax.set_ylabel("Mean F1-macro (5-fold CV)")
ax.set_title("GridSearchCV — SVM C Hyperparameter Tuning")
ax.legend()
plt.tight_layout()
plt.savefig(SAVE_DIR / "gridsearch_c_f1_v2.png", dpi=150)
plt.show()
print("GridSearch chart saved -> gridsearch_c_f1_v2.png")
print()


# ==============================================================================
# CELL 13 — SAVE IMPROVED MODEL
# Saves as svm_model_v2.pkl — separate from original svm_model.pkl so the
# production backend is NOT overwritten until the model is manually promoted.
#
# To promote to production after validation:
#   Rename models/svm_model_v2.pkl to models/svm_model.pkl
# ==============================================================================

MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

save_path = MODEL_DIR / "svm_model_v2.pkl"
joblib.dump(final_svm, save_path)

print("=" * 60)
print("  CELL 13: MODEL SAVED")
print("=" * 60)
print()
print("Improved model saved ->", save_path)
print("Contains: FeatureUnion (char_wb + word) + CalibratedSVM (C =", best_C, ")")
print()
print("To promote v2 to production:")
print("   Rename  models/svm_model_v2.pkl  ->  models/svm_model.pkl")
print()


# ==============================================================================
# CELL 14 — SMOKE TEST: Verify predict_proba() compatibility
# Loads the saved model and confirms it returns valid probability scores.
# The ShieldGuard hybrid engine (inference.py) calls predict_proba() on
# the SVM, so this check must pass before the model can be promoted.
# ==============================================================================

print("=" * 60)
print("  CELL 14: SMOKE TEST — predict_proba() compatibility check")
print("=" * 60)

loaded_model = joblib.load(save_path)

test_samples = [
    "Hello, this is a reminder that your appointment is scheduled for tomorrow at 10 AM.",
    "This is the bank security department. Your account has been suspended due to suspicious activity. Please provide your PIN immediately.",
]

preds  = loaded_model.predict(test_samples)
probas = loaded_model.predict_proba(test_samples)

print()
print("  Sample 1 (Safe appointment reminder):")
print("    Prediction :", preds[0])
print("    Confidence : safe =", round(probas[0][0], 4), ",  vishing =", round(probas[0][1], 4))

print()
print("  Sample 2 (Bank impersonation vishing):")
print("    Prediction :", preds[1])
print("    Confidence : safe =", round(probas[1][0], 4), ",  vishing =", round(probas[1][1], 4))

print()
print("Smoke test passed — predict_proba() is functional.")
print()
print("=" * 60)
print("  Training Pipeline v2 Complete.")
print("=" * 60)
