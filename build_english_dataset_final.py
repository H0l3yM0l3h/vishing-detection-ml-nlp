import pandas as pd
from pathlib import Path

# ===============================
# CONFIG
# ===============================

VISHING_CSV = Path("data/english_dataset.csv")          # 826 vishing
SAFE_CSV = Path("data/safe_transcripts_all.csv")       # 137 safe (merged)
OUTPUT_CSV = Path("data/english_dataset_final.csv")

# ===============================
# LOAD DATA
# ===============================

print("[*] Loading datasets...")

df_vishing = pd.read_csv(VISHING_CSV)
df_safe = pd.read_csv(SAFE_CSV)

# Sanity checks
assert set(df_vishing.columns) == {"transcript", "label"}
assert set(df_safe.columns) == {"transcript", "label"}

print(f"Vishing samples: {len(df_vishing)}")
print(f"Safe samples: {len(df_safe)}")

# ===============================
# MERGE & SHUFFLE
# ===============================

df_final = pd.concat([df_vishing, df_safe], ignore_index=True)
df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

# ===============================
# SAVE
# ===============================

OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df_final.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print("\n[✓] Final dataset saved to:", OUTPUT_CSV)
print("\nClass distribution:")
print(df_final["label"].value_counts())
