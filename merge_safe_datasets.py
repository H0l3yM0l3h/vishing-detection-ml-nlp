import pandas as pd
from pathlib import Path

SAFE1 = Path("data/safe_transcripts_en.csv")
SAFE2 = Path("data/safe_transcripts_kaggle.csv")
OUTPUT = Path("data/safe_transcripts_all.csv")

print("[*] Loading SAFE datasets...")

df1 = pd.read_csv(SAFE1)
df2 = pd.read_csv(SAFE2)

print(f"SAFE from call-center chunks: {len(df1)}")
print(f"SAFE from Kaggle: {len(df2)}")

df = pd.concat([df1, df2], ignore_index=True)
df = df.drop_duplicates(subset="transcript")

df.to_csv(OUTPUT, index=False, encoding="utf-8")

print("\n[✓] Merged SAFE dataset saved to:", OUTPUT)
print("Total SAFE samples:", len(df))
