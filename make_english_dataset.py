#!/usr/bin/env python3
import os
import re
import json
import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

# Whisper import (openai-whisper)
import whisper


# -----------------------------
# Helpers: column detection
# -----------------------------
FILENAME_CANDIDATES = [
    "filename", "file", "filepath", "path", "audio", "audio_file", "wav", "recording"
]

LABEL_CANDIDATES = [
    "label", "class", "category", "is_scam", "scam", "spam", "robocall", "type", "call_type"
]

def normalize_col(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower())

def detect_column(df: pd.DataFrame, candidates):
    cols = list(df.columns)
    norm_map = {c: normalize_col(c) for c in cols}

    # direct match
    for c in cols:
        if norm_map[c] in candidates:
            return c

    # contains candidate token
    for c in cols:
        for cand in candidates:
            if cand in norm_map[c]:
                return c

    return None

def guess_audio_column(df: pd.DataFrame):
    # Try name-based detection first
    col = detect_column(df, FILENAME_CANDIDATES)
    if col:
        return col

    # Fallback: find a column that looks like it contains filenames
    for c in df.columns:
        sample = df[c].dropna().astype(str).head(50).tolist()
        if not sample:
            continue
        hits = sum(1 for x in sample if re.search(r"\.(wav|mp3|m4a|flac)$", x.strip().lower()))
        if hits >= max(3, len(sample)//4):
            return c
    return None

def guess_label_column(df: pd.DataFrame):
    col = detect_column(df, LABEL_CANDIDATES)
    if col:
        return col

    # fallback: choose low-cardinality column (common for labels)
    best = None
    best_unique = 10**9
    for c in df.columns:
        nunique = df[c].nunique(dropna=True)
        if 1 < nunique <= 20 and nunique < best_unique:
            best_unique = nunique
            best = c
    return best


# -----------------------------
# Helpers: label mapping
# -----------------------------
def map_to_project_label(raw_label: str) -> str | None:
    """
    Map dataset labels into {vishing, safe}.
    Returns None if the row should be ignored.
    """
    if raw_label is None or (isinstance(raw_label, float) and pd.isna(raw_label)):
        return None

    s = str(raw_label).strip().lower()

    # Numeric labels (common cases)
    # You can flip these if your dataset defines it differently, but many datasets use:
    # 1 = scam/robocall, 0 = legit
    if re.fullmatch(r"[01]", s):
        return "vishing" if s == "1" else "safe"

    # Typical text labels
    vishing_keywords = [
        "scam", "fraud", "spam", "robocall", "illegal", "spoof", "phish", "vish", "malicious"
    ]
    safe_keywords = [
        "legit", "legitimate", "ham", "normal", "genuine", "safe", "non_scam", "not_scam"
    ]

    if any(k in s for k in vishing_keywords):
        return "vishing"
    if any(k in s for k in safe_keywords):
        return "safe"

    # If labels are something like "A"/"B" or unknown categories, ignore safely
    return None


# -----------------------------
# Whisper transcription
# -----------------------------
def transcribe_file(model, audio_path: Path, language="en"):
    # whisper returns a dict with 'text' and segment info
    result = model.transcribe(str(audio_path), language=language, fp16=False)
    text = (result.get("text") or "").strip()
    # normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text

def main():
    parser = argparse.ArgumentParser(description="Create english_dataset.csv (transcript,label) from robocall dataset.")
    parser.add_argument("--dataset_dir", type=str, required=True, help="Path to dataset folder containing metadata.csv and audio-wav-16khz/")
    parser.add_argument("--audio_dir", type=str, default="audio-wav-16khz", help="Relative audio folder inside dataset_dir")
    parser.add_argument("--metadata", type=str, default="metadata.csv", help="Metadata CSV filename inside dataset_dir")
    parser.add_argument("--out_csv", type=str, default="english_dataset.csv", help="Output CSV filename")
    parser.add_argument("--whisper_model", type=str, default="small", help="tiny|base|small|medium|large")
    parser.add_argument("--max_rows", type=int, default=0, help="For quick tests: limit rows (0 = all)")
    parser.add_argument("--min_chars", type=int, default=10, help="Drop transcripts shorter than this many chars")
    parser.add_argument("--cache_jsonl", type=str, default="transcripts_cache.jsonl", help="Cache transcripts to resume safely")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir).resolve()
    audio_dir = (dataset_dir / args.audio_dir).resolve()
    meta_path = (dataset_dir / args.metadata).resolve()
    out_path = (dataset_dir / args.out_csv).resolve()
    cache_path = (dataset_dir / args.cache_jsonl).resolve()

    if not meta_path.exists():
        raise FileNotFoundError(f"metadata not found: {meta_path}")
    if not audio_dir.exists():
        raise FileNotFoundError(f"audio dir not found: {audio_dir}")

    # Load metadata
    df = pd.read_csv(meta_path)
    df.columns = [c.strip() for c in df.columns]

    audio_col = guess_audio_column(df)
    label_col = guess_label_column(df)

    print("\n--- Detected columns ---")
    print("Audio column:", audio_col)
    print("Label column:", label_col)
    if audio_col is None or label_col is None:
        print("\nColumns in metadata.csv:")
        for c in df.columns:
            print(" -", c)
        raise RuntimeError("Could not auto-detect audio/label columns. Rename columns or edit candidates in script.")

    # Prepare rows
    df = df[[audio_col, label_col]].copy()
    df.rename(columns={audio_col: "audio_ref", label_col: "raw_label"}, inplace=True)

    # Map labels
    df["label"] = df["raw_label"].apply(map_to_project_label)
    before = len(df)
    df = df[df["label"].isin(["vishing", "safe"])].copy()
    after = len(df)
    print(f"\nLabel-mapped rows kept: {after}/{before} (ignored {before-after} irrelevant/unknown rows)")

    # Resolve audio path
    def resolve_audio_path(x):
        x = str(x).strip()
        p = Path(x)
        if p.is_absolute() and p.exists():
            return p
        # Try inside audio_dir (common case: filename only)
        candidate = audio_dir / p.name
        if candidate.exists():
            return candidate
        # Try if metadata already includes relative path under dataset_dir
        candidate2 = dataset_dir / p
        if candidate2.exists():
            return candidate2
        return None

    df["audio_path"] = df["audio_ref"].apply(resolve_audio_path)
    missing = df["audio_path"].isna().sum()
    if missing:
        print(f"\nWARNING: {missing} rows have missing audio files. They will be dropped.")
        df = df[df["audio_path"].notna()].copy()

    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows).copy()
        print(f"\nMax rows enabled: using first {len(df)} rows")

    # Load cache if exists (resume)
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    cache[obj["audio_path"]] = obj["transcript"]
                except Exception:
                    continue
        print(f"\nLoaded cache entries: {len(cache)}")

    # Load whisper
    print(f"\nLoading Whisper model: {args.whisper_model}")
    model = whisper.load_model(args.whisper_model)

    transcripts = []
    kept_labels = []

    # Transcribe
    print("\nTranscribing...")
    with open(cache_path, "a", encoding="utf-8") as cache_f:
        for _, row in tqdm(df.iterrows(), total=len(df)):
            ap = str(row["audio_path"])
            label = row["label"]

            if ap in cache:
                text = cache[ap]
            else:
                try:
                    text = transcribe_file(model, Path(ap), language="en")
                except Exception as e:
                    # Skip bad files safely
                    continue
                cache_f.write(json.dumps({"audio_path": ap, "transcript": text}, ensure_ascii=False) + "\n")
                cache_f.flush()

            if text and len(text) >= args.min_chars:
                transcripts.append(text)
                kept_labels.append(label)

    out_df = pd.DataFrame({"transcript": transcripts, "label": kept_labels})

    # Drop duplicates (common when calls repeat or metadata duplicates)
    out_df.drop_duplicates(subset=["transcript", "label"], inplace=True)

    # Save final
    out_df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"\nSaved: {out_path}")
    print(out_df["label"].value_counts())

if __name__ == "__main__":
    main()
