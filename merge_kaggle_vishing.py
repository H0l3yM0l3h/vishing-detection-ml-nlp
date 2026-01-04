import pandas as pd
from pathlib import Path

BASE_VISHING = Path("data/english_dataset_final.csv")
KAGGLE_VISHING = Path("data/vishing_transcripts_kaggle_audio.csv")
OUTPUT = Path("data/english_dataset_with_kaggle_vishing.csv")

print("[*] Loading datasets...")

df_base = pd.read_csv(BASE_VISHING)
df_kaggle = pd.read_csv(KAGGLE_VISHING)

assert set(df_base.columns) == {"transcript", "label"}
assert set(df_kaggle.columns) == {"transcript", "label"}

print(f"Base dataset: {len(df_base)}")
print(f"Kaggle vishing: {len(df_kaggle)}")

df_all = pd.concat([df_base, df_kaggle], ignore_index=True)
df_all = df_all.sample(frac=1, random_state=42).reset_index(drop=True)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df_all.to_csv(OUTPUT, index=False, encoding="utf-8")

print("\n[✓] Saved:", OUTPUT)
print("\nClass distribution:")
print(df_all["label"].value_counts())
