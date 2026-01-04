from pathlib import Path
import whisper
import pandas as pd

AUDIO_DIR = Path("data/raw_audio/PhishingVoiceDataset/NonPhishing")
OUTPUT_CSV = Path("data/safe_transcripts_kaggle.csv")

print("[*] Loading Whisper model...")
model = whisper.load_model("base")

rows = []
audio_files = sorted(AUDIO_DIR.glob("*.mp3"))

print(f"[*] Found {len(audio_files)} Kaggle SAFE audio files")

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

print("\n[✓] Saved:", OUTPUT_CSV)
print("Samples:", len(df))
