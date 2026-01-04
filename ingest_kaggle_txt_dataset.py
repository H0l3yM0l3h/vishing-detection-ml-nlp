from pathlib import Path
import pandas as pd

BASE_DIR = Path("data/raw_text/archive3")

FILES = {
    "English_Scam.txt": "vishing",
    "English_NonScam.txt": "safe"
}

rows = []

for fname, label in FILES.items():
    path = BASE_DIR / fname
    print(f"[*] Loading {fname}")

    with open(path, encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if len(text) < 20:
                continue
            rows.append({
                "transcript": text,
                "label": label
            })

df = pd.DataFrame(rows)
out = Path("data/kaggle_txt_transcripts.csv")
df.to_csv(out, index=False, encoding="utf-8")

print(f"\n[✓] Saved: {out}")
print(df["label"].value_counts())
