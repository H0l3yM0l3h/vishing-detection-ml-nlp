import pandas as pd

INPUT = "data/english_dataset_final_v2.csv"
OUTPUT = "data/english_dataset_clean.csv"

df = pd.read_csv(INPUT)
before = len(df)

df = df.dropna(subset=["transcript"])
df = df[df["transcript"].str.len() >= 20]

after = len(df)

df.to_csv(OUTPUT, index=False, encoding="utf-8")

print("Before cleaning:", before)
print("After cleaning :", after)
print("\nClass distribution:")
print(df["label"].value_counts())
