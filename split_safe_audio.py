from pathlib import Path
import subprocess

INPUT_DIR = Path("data/raw_audio/safe_long")
OUTPUT_DIR = Path("data/raw_audio/safe_chunks")

SEGMENT_SECONDS = 15

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

audio_files = list(INPUT_DIR.glob("*.mp3"))
print(f"Found {len(audio_files)} SAFE long audio files")

for audio in audio_files:
    out_pattern = OUTPUT_DIR / f"{audio.stem}_%05d.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(audio),
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(out_pattern)
    ]

    subprocess.run(cmd, check=True)

print("Splitting complete.")
