from pathlib import Path
import whisper
import pandas as pd

AUDIO_DIR = Path("data/raw_audio/safe_chunks")
OUTPUT_CSV = Path("data/safe_transcripts_en.csv")

MODEL_NAME = "base"

print("[*] Loading Whisper model...")
model = whisper.load_model(MODEL_NAME)

rows = []

audio_files = sorted(AUDIO_DIR.glob("*.wav"))
print(f"[*] Found {len(audio_files)} SAFE audio chunks")

for audio in audio_files:
    print(f"Transcribing: {audio.name}")
    result = model.transcribe(str(audio), language="en")

    text = result.get("text", "").strip()
    if len(text) < 10:
        continue

    rows.append({
        "transcript": text,
        "label": "safe"
    })

df = pd.DataFrame(rows)
df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")

print(f"\n[✓] Saved SAFE transcripts to: {OUTPUT_CSV}")
print("Samples:", len(df))
