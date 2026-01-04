import pandas as pd
from pathlib import Path
import re

# ===============================
# CONFIG
# ===============================

# FTC robocall dataset (SCAM ONLY)
FTC_DIR = Path(
    r"data\robocall-audio-dataset-ver-0.1\robocall-audio-dataset-ver-0.1"
)
FTC_METADATA = FTC_DIR / "metadata.csv"

# Existing SAFE dataset (may contain non-English)
SAFE_DATASET = Path(r"data\cleaned_dataset.csv")

# Output
OUTPUT_CSV = Path(r"data\english_dataset.csv")

MIN_CHARS = 10

# Simple English heuristic:
# keeps Latin characters, digits, and common punctuation
ENGLISH_REGEX = re.compile(r"^[A-Za-z0-9\s.,!?'\-]+$")

# ===============================
# LOAD FTC ROBOSCAM DATA (VISHING)
# ===============================

print("[*] Loading FTC robocall dataset...")
df_ftc = pd.read_csv(FTC_METADATA)

required_cols = {"transcript", "language"}
if not required_cols.issubset(df_ftc.columns):
    raise ValueError("FTC metadata missing required columns")

# English only
df_ftc = df_ftc[df_ftc["language"] == "en"].copy()

# Clean transcripts
df_ftc["transcript"] = df_ftc["transcript"].astype(str).str.strip()
df_ftc = df_ftc[df_ftc["transcript"].str.len() >= MIN_CHARS]

# Label
df_ftc["label"] = "vishing"
df_ftc = df_ftc[["transcript", "label"]].drop_duplicates()

print(f"[+] FTC vishing samples (EN): {len(df_ftc)}")

# ===============================
# LOAD SAFE DATA (ENGLISH ONLY)
# ===============================

print("[*] Loading safe dataset...")
df_safe = pd.read_csv(SAFE_DATASET)

if "transcript" not in df_safe.columns:
    raise ValueError("Safe dataset must contain 'transcript' column")

# Clean
df_safe["transcript"] = df_safe["transcript"].astype(str).str.strip()
df_safe = df_safe[df_safe["transcript"].str.len() >= MIN_CHARS]

# Keep ENGLISH ONLY
df_safe = df_safe[
    df_safe["transcript"].apply(
        lambda x: bool(ENGLISH_REGEX.match(x))
    )
]

# Label
df_safe["label"] = "safe"
df_safe = df_safe[["transcript", "label"]].drop_duplicates()

print(f"[+] Safe samples (EN): {len(df_safe)}")

# ===============================
# MERGE & SAVE
# ===============================

print("[*] Merging datasets...")
df_final = pd.concat([df_ftc, df_safe], ignore_index=True)
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df_final.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print("\n[✓] Final dataset written to:", OUTPUT_CSV)
print("\nClass distribution:")
print(df_final["label"].value_counts())
