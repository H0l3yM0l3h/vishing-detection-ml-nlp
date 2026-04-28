# ==============================================================================
# CELL 1 - SHIELDGUARD ML V3 TRAINING FOR LIMITED DATASETS
# ==============================================================================
# Purpose:
#   Train the main vishing detector properly for a limited transcript dataset.
#
# Key methodology fixes over v2:
#   1. Split the real dataset before augmentation to avoid near-duplicate leakage.
#   2. Apply EDA and hard-negative examples only to the training split.
#   3. Tune the production decision threshold on a validation split.
#   4. Keep the clean test split untouched for final reporting.
#   5. Save model metadata and validation metrics for documentation.
#
# Usage:
#   cd D:\FYP1\VishingDetection
#   .\.venv\Scripts\python.exe notebooks\03_limited_dataset_svm_training.py
# ==============================================================================

import json
import os
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

import joblib
import matplotlib.pyplot as plt
import nltk
import numpy as np
import pandas as pd
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)


# ==============================================================================
# CELL 2 - CONFIG
# ==============================================================================

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
random.seed(RANDOM_SEED)

BASE_DIR = Path.cwd().parent if Path.cwd().name.lower() == "notebooks" else Path.cwd()
DATA_PATH = BASE_DIR / "data" / "english_dataset_final_v2.csv"
MODEL_DIR = BASE_DIR / "models"
DOCS_DIR = BASE_DIR / "docs"
NOTEBOOK_DIR = BASE_DIR / "notebooks"

MODEL_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "svm_model.pkl"
METADATA_PATH = MODEL_DIR / "svm_model_metadata.json"
METRICS_PATH = DOCS_DIR / "ml_training_v3_metrics.json"


# ==============================================================================
# CELL 3 - PREPROCESSING
# ==============================================================================

lemmatizer = WordNetLemmatizer()


def normalize_english(text: str) -> str:
    text = str(text)
    text = text.replace("\u200b", " ")
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def lemmatize_text(text: str) -> str:
    tokens = text.split()
    tokens = [lemmatizer.lemmatize(token, pos="v") for token in tokens]
    tokens = [lemmatizer.lemmatize(token, pos="n") for token in tokens]
    return " ".join(tokens)


def preprocess_text(text: str) -> str:
    return lemmatize_text(normalize_english(text))


# ==============================================================================
# CELL 4 - LIMITED-DATA TRAIN-ONLY AUGMENTATION
# ==============================================================================

HARD_NEGATIVE_SAFE = [
    "This is your dentist clinic calling to confirm your appointment tomorrow at 10am. If you need to reschedule, please call us back at our official number.",
    "Hello, this is your clinic reminding you that your appointment is scheduled for next Tuesday. No payment or password is required.",
    "This is the school office calling to remind parents about the meeting on Friday at 3pm. No action is required.",
    "Your pharmacy prescription is ready for pickup. Please bring your ID when you collect it during opening hours.",
    "This is customer support following up on your recent feedback. We have resolved the issue and no account details are needed.",
    "Your parcel will be delivered tomorrow between 9am and 12pm. You do not need to press anything or provide payment.",
    "This is your bank branch confirming whether you made a recent card transaction. Please call the number printed on your card if you need help.",
    "This is your bank calling to confirm whether you made a recent purchase. If not, call the official number printed on the back of your card.",
    "This is a bank fraud prevention reminder. We will never ask for your OTP, TAC, PIN, or password during this call.",
    "Your card transaction alert is for awareness only. For assistance, hang up and contact the bank through the official app or branch hotline.",
    "This is your bank appointment reminder for a branch visit. Please bring identification, but do not share passwords or verification codes by phone.",
    "A bank staff member is following up on your support ticket. They will not ask you to transfer money or reveal your OTP.",
    "This is a legitimate bank service survey. You may decline the call, and no personal banking details are required.",
    "This is a legitimate appointment reminder from the hospital. Please arrive fifteen minutes early and bring your appointment card.",
    "Hello, your vehicle service appointment is confirmed for Monday morning. Call our official service centre number if you want to reschedule.",
    "This is the university administration calling about your document collection. Please visit the student office during business hours.",
    "Your subscription renewal receipt has been emailed to you. Contact our official helpdesk if you have questions.",
    "This is a reminder that your insurance policy review is scheduled next week. We will not ask for OTP or banking password over the phone.",
    "The delivery department is calling to confirm your address landmark only. We will not ask for card details or payment codes.",
    "Hello, this is the library. Your reserved book is available for collection by Friday.",
    "This is the repair technician confirming the visit window for your appliance repair. No online banking details are required.",
    "Your order has shipped and the tracking link was sent by email. You can ignore this call if you already received the notification.",
]

HARD_POSITIVE_VISHING = [
    "Your bank account has been suspended. Provide your OTP immediately or your card will be blocked.",
    "This is the police department. A warrant has been issued and you must transfer money now to avoid arrest.",
    "Your computer has a virus. Install remote access software and tell us your banking credentials.",
    "Do not tell anyone about this call. Verify your account number and password now.",
    "Press 1 immediately to stop legal action on your social security number.",
    "You won a prize. Confirm your credit card number and identity number to claim it today.",
]


def get_synonyms(word: str) -> list[str]:
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            candidate = lemma.name().replace("_", " ").lower()
            if candidate != word.lower() and candidate.isascii():
                synonyms.add(candidate)
    return list(synonyms)


def eda_synonym_replace(sentence: str, swap_rate: float = 0.08) -> str:
    words = sentence.split()
    if len(words) < 6:
        return sentence
    n_swap = max(1, int(len(words) * swap_rate))
    indices = random.sample(range(len(words)), min(n_swap, len(words)))
    new_words = words.copy()
    for idx in indices:
        syns = get_synonyms(words[idx])
        if syns:
            new_words[idx] = random.choice(syns)
    return " ".join(new_words)


def augment_training_split(train_df: pd.DataFrame) -> pd.DataFrame:
    safe_df = train_df[train_df["label"] == "safe"].copy()
    n_safe_aug = int(len(safe_df) * 0.50)

    aug_rows = []
    for _, row in safe_df.sample(n_safe_aug, random_state=RANDOM_SEED).iterrows():
        aug_text = eda_synonym_replace(row["clean_text"])
        aug_rows.append({"transcript": aug_text, "label": "safe", "clean_text": aug_text, "source": "eda_safe"})

    for text in HARD_NEGATIVE_SAFE:
        clean = preprocess_text(text)
        aug_rows.append({"transcript": text, "label": "safe", "clean_text": clean, "source": "hard_negative_safe"})

    for text in HARD_POSITIVE_VISHING:
        clean = preprocess_text(text)
        aug_rows.append({"transcript": text, "label": "vishing", "clean_text": clean, "source": "hard_positive_vishing"})

    augmented = pd.concat([train_df, pd.DataFrame(aug_rows)], ignore_index=True)
    augmented = augmented.drop_duplicates(subset=["clean_text", "label"]).reset_index(drop=True)
    return augmented


# ==============================================================================
# CELL 5 - MODEL FACTORY
# ==============================================================================


def build_features() -> FeatureUnion:
    char_tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=2,
        max_df=0.95,
        max_features=30000,
        sublinear_tf=True,
    )
    word_tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
        max_features=20000,
        sublinear_tf=True,
        stop_words="english",
    )
    return FeatureUnion([("char", char_tfidf), ("word", word_tfidf)])


def build_calibrated_svm(c_value: float) -> Pipeline:
    return Pipeline(
        [
            ("features", build_features()),
            (
                "clf",
                CalibratedClassifierCV(
                    LinearSVC(
                        C=c_value,
                        class_weight="balanced",
                        random_state=RANDOM_SEED,
                        max_iter=5000,
                    ),
                    method="sigmoid",
                    cv=3,
                ),
            ),
        ]
    )


def vishing_probabilities(model: Pipeline, texts) -> np.ndarray:
    proba = model.predict_proba(texts)
    classes = list(model.classes_)
    return proba[:, classes.index("vishing")]


def labels_from_threshold(vishing_probs: np.ndarray, threshold: float) -> np.ndarray:
    return np.where(vishing_probs >= threshold, "vishing", "safe")


def evaluate_at_threshold(name: str, y_true, vishing_probs, threshold: float) -> dict:
    y_pred = labels_from_threshold(vishing_probs, threshold)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=["safe", "vishing"], zero_division=0
    )
    return {
        "split": name,
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "safe_precision": round(float(precision[0]), 4),
        "safe_recall": round(float(recall[0]), 4),
        "safe_f1": round(float(f1[0]), 4),
        "vishing_precision": round(float(precision[1]), 4),
        "vishing_recall": round(float(recall[1]), 4),
        "vishing_f1": round(float(f1[1]), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=["safe", "vishing"]).tolist(),
    }


# ==============================================================================
# CELL 6 - LOAD, SPLIT, AND TRAIN
# ==============================================================================

print("=" * 72)
print("ShieldGuard ML v3 - leakage-safe SVM training")
print("=" * 72)

df = pd.read_csv(DATA_PATH)
df["transcript"] = df["transcript"].astype(str)
df["label"] = df["label"].astype(str).str.lower().str.strip()
df = df[df["label"].isin(["safe", "vishing"])].copy()
df["clean_text"] = df["transcript"].apply(preprocess_text)
df["source"] = "dataset"
df = df[df["clean_text"].str.len() > 0]
df = df.drop_duplicates(subset=["clean_text", "label"]).reset_index(drop=True)

print("Dataset:", DATA_PATH)
print("Rows after clean/dedup:", len(df))
print("Labels:", Counter(df["label"]))

train_df, test_df = train_test_split(
    df,
    test_size=0.20,
    random_state=RANDOM_SEED,
    stratify=df["label"],
)
train_df, val_df = train_test_split(
    train_df,
    test_size=0.20,
    random_state=RANDOM_SEED,
    stratify=train_df["label"],
)

train_aug = augment_training_split(train_df)

print("Train real:", Counter(train_df["label"]))
print("Validation real:", Counter(val_df["label"]))
print("Test real:", Counter(test_df["label"]))
print("Train after augmentation:", Counter(train_aug["label"]))

raw_pipeline = Pipeline(
    [
        ("features", build_features()),
        (
            "clf",
            LinearSVC(
                class_weight="balanced",
                random_state=RANDOM_SEED,
                max_iter=5000,
            ),
        ),
    ]
)

grid = GridSearchCV(
    raw_pipeline,
    param_grid={"clf__C": [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]},
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED),
    scoring="f1_macro",
    n_jobs=-1,
    verbose=1,
)

grid.fit(train_aug["clean_text"].values, train_aug["label"].values)
best_c = float(grid.best_params_["clf__C"])
print("Best C:", best_c)
print("Best CV F1-macro:", round(float(grid.best_score_), 4))

model = build_calibrated_svm(best_c)
model.fit(train_aug["clean_text"].values, train_aug["label"].values)


# ==============================================================================
# CELL 7 - VALIDATION THRESHOLD TUNING
# ==============================================================================

val_probs = vishing_probabilities(model, val_df["clean_text"].values)
threshold_rows = []
for threshold in np.arange(0.35, 0.91, 0.01):
    metric = evaluate_at_threshold("validation", val_df["label"].values, val_probs, threshold)
    # Favor macro F1, then vishing recall, then safe recall.
    score = metric["f1_macro"] + 0.02 * metric["vishing_recall"] + 0.01 * metric["safe_recall"]
    threshold_rows.append((score, threshold, metric))

threshold_rows.sort(key=lambda item: item[0], reverse=True)
best_threshold = float(threshold_rows[0][1])
validation_metrics = threshold_rows[0][2]

print("Best validation threshold:", round(best_threshold, 2))
print("Validation metrics:", json.dumps(validation_metrics, indent=2))


# ==============================================================================
# CELL 8 - CLEAN TEST EVALUATION AND CHARTS
# ==============================================================================

test_probs = vishing_probabilities(model, test_df["clean_text"].values)
test_metrics = evaluate_at_threshold("test", test_df["label"].values, test_probs, best_threshold)
test_pred = labels_from_threshold(test_probs, best_threshold)

print("Test metrics:", json.dumps(test_metrics, indent=2))
print()
print(classification_report(test_df["label"].values, test_pred, digits=4))

cm = confusion_matrix(test_df["label"].values, test_pred, labels=["safe", "vishing"])
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["safe", "vishing"])
fig, ax = plt.subplots(figsize=(6, 5))
disp.plot(ax=ax, colorbar=False)
ax.set_title(f"SVM v3 Clean Test Confusion Matrix (threshold={best_threshold:.2f})")
plt.tight_layout()
plt.savefig(NOTEBOOK_DIR / "confusion_matrix_v3.png", dpi=150)
plt.close(fig)

grid_results_df = pd.DataFrame(grid.cv_results_)
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(
    grid_results_df["param_clf__C"].astype(float),
    grid_results_df["mean_test_score"],
    marker="o",
)
ax.set_xscale("log")
ax.set_xlabel("C")
ax.set_ylabel("Mean CV F1-macro")
ax.set_title("SVM v3 GridSearchCV")
ax.axvline(best_c, color="red", linestyle="--", label=f"Best C={best_c}")
ax.legend()
plt.tight_layout()
plt.savefig(NOTEBOOK_DIR / "gridsearch_c_f1_v3.png", dpi=150)
plt.close(fig)


# ==============================================================================
# CELL 9 - TARGETED SANITY CASES
# ==============================================================================

targeted_cases = [
    ("safe", "dentist appointment", "This is your dentist clinic calling to confirm your appointment tomorrow at 10am. If you need to reschedule, please call us back at our official number. See you soon."),
    ("safe", "bank callback safe", "This is your bank calling to confirm whether you made a purchase. If not, call the number on the back of your card."),
    ("safe", "delivery reminder", "Good afternoon, your parcel will arrive tomorrow between 9am and 12pm. You do not need to do anything."),
    ("vishing", "otp threat", "Your account is suspended. Tell me the OTP now or your card will be blocked."),
    ("vishing", "legal transfer", "This is the police department. You must transfer money now to avoid arrest and legal action."),
    ("vishing", "remote access", "Your computer is infected. Install AnyDesk immediately and give us your banking credentials."),
]

targeted_results = []
for expected, name, text in targeted_cases:
    clean = preprocess_text(text)
    prob = float(vishing_probabilities(model, [clean])[0])
    got = "vishing" if prob >= best_threshold else "safe"
    targeted_results.append(
        {
            "case": name,
            "expected": expected,
            "got": got,
            "vishing_probability": round(prob, 4),
            "pass": got == expected,
        }
    )

print("Targeted sanity checks:")
print(pd.DataFrame(targeted_results).to_string(index=False))


# ==============================================================================
# CELL 10 - SAVE PRODUCTION MODEL AND METADATA
# ==============================================================================

joblib.dump(model, MODEL_PATH)

metadata = {
    "model_version": "svm_v3_limited_dataset",
    "trained_at": pd.Timestamp.utcnow().isoformat(),
    "dataset_path": str(DATA_PATH.relative_to(BASE_DIR)),
    "dataset_rows_after_cleaning": int(len(df)),
    "label_counts_after_cleaning": dict(Counter(df["label"])),
    "split_counts": {
        "train_real": dict(Counter(train_df["label"])),
        "validation_real": dict(Counter(val_df["label"])),
        "test_real": dict(Counter(test_df["label"])),
        "train_after_augmentation": dict(Counter(train_aug["label"])),
    },
    "methodology": [
        "real dataset split before augmentation",
        "EDA synonym augmentation applied only to training safe class",
        "hard-negative safe examples added only to training split",
        "FeatureUnion char_wb TF-IDF plus word TF-IDF with English stop words",
        "LinearSVC with class_weight=balanced and sigmoid calibration",
        "threshold tuned on validation split and final metrics reported on clean test split",
    ],
    "best_c": best_c,
    "best_cv_f1_macro": round(float(grid.best_score_), 4),
    "decision_threshold": round(best_threshold, 4),
    "validation_metrics": validation_metrics,
    "test_metrics": test_metrics,
    "targeted_sanity_checks": targeted_results,
}

METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
METRICS_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

print("Saved model:", MODEL_PATH)
print("Saved metadata:", METADATA_PATH)
print("Saved metrics report:", METRICS_PATH)
print("Done.")
