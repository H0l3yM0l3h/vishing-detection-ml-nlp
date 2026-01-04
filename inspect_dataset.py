import pandas as pd

df = pd.read_csv("data/english_dataset_final_v2.csv")

print("HEAD:")
print(df.head(5))

print("\nTAIL:")
print(df.tail(5))

print("\nEmpty transcripts:", df["transcript"].isna().sum())
print("Very short (<10 chars):", (df["transcript"].str.len() < 10).sum())

print("\nClass distribution:")
print(df["label"].value_counts())

print("\nTOTAL SAMPLES:", len(df))
