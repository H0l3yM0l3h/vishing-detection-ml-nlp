import os
import pandas as pd
import whisper
from pathlib import Path

# Paths
AUDIO_DIR = Path("data/raw_audio/PhishingVoiceDataset/Phishing")
OUTPUT_CSV = Path("data/vishing_transcripts_kaggle_audio.csv")

print("[*] Loading Whisper model...")
model = whisper.load_model("base")  # base is fine for dataset building

rows = []

print("[*] Transcribing Kaggle PHISHING audio...")

for audio_file in AUDIO_DIR.rglob("*.mp3"):
    try:
        print(f"  - Transcribing: {audio_file.name}")
        result = model.transcribe(str(audio_file))
        text = result["text"].strip()

        if len(text) < 10:
            continue  # skip garbage / silence

        rows.append({
            "transcript": text,
            "label": "vishing"
        })

    except Exception as e:
        print(f"[!] Failed on {audio_file}: {e}")

df = pd.DataFrame(rows)
OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print(f"\n[✓] Saved: {OUTPUT_CSV}")
print(f"Samples: {len(df)}")
