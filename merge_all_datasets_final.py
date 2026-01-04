import pandas as pd

print("[*] Loading datasets...")

df_audio = pd.read_csv("data/english_dataset_with_kaggle_vishing.csv")
df_txt = pd.read_csv("data/kaggle_txt_transcripts.csv")

print("Audio-based dataset:", len(df_audio))
print("Text-only Kaggle dataset:", len(df_txt))

df = pd.concat([df_audio, df_txt], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

out_path = "data/english_dataset_final_v2.csv"
df.to_csv(out_path, index=False, encoding="utf-8")

print("\n[✓] Saved:", out_path)
print("\nClass distribution:")
print(df["label"].value_counts())
print("\nTOTAL SAMPLES:", len(df))
