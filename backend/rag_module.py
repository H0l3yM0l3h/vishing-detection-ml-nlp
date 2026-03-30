"""
rag_module.py — RAG layer for ShieldGuard Phase 2
===================================================
Uses ChromaDB + sentence-transformers to find historically similar
scam transcripts and provide contextual evidence to the LLM agents.

Embedding model: all-MiniLM-L6-v2 (384-dim, CPU-friendly, ~80MB)
Storage: data/scam_library/ (persistent ChromaDB)
"""

import hashlib
import os
from pathlib import Path

# Redirect HuggingFace cache to project area (avoids C: drive space issues)
_PROJECT_CACHE = str(Path(__file__).resolve().parent.parent / ".hf_cache")
os.environ.setdefault("HF_HOME", _PROJECT_CACHE)
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", os.path.join(_PROJECT_CACHE, "sentence_transformers"))

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer

# ── Paths ────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent.parent
DATA_DIR       = BASE_DIR / "data"
CHROMA_DIR     = DATA_DIR / "scam_library"
DATASET_PATH   = DATA_DIR / "english_dataset_final_v2.csv"

# ── Config ───────────────────────────────────────
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME  = "scam_transcripts"


# ── Lazy singletons ─────────────────────────────
_embed_model = None
_chroma_client = None
_collection = None


def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def _get_collection():
    global _chroma_client, _collection
    if _collection is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _make_id(text: str) -> str:
    """Deterministic ID from transcript text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────
# BUILD SCAM LIBRARY
# ─────────────────────────────────────────────────

def build_scam_library(csv_path: str | Path | None = None, force: bool = False):
    """
    Embed and store all vishing transcripts into ChromaDB.

    Parameters
    ----------
    csv_path : path to the CSV dataset (default: english_dataset_final_v2.csv)
    force    : if True, rebuild even if collection is already populated
    """
    csv_path = Path(csv_path) if csv_path else DATASET_PATH
    collection = _get_collection()

    # Skip if already populated (unless forced)
    if collection.count() > 0 and not force:
        return collection.count()

    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")

    # Read dataset
    df = pd.read_csv(csv_path)

    # Identify the text and label columns
    text_col = None
    label_col = None
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ("text", "transcript", "transcription", "message"):
            text_col = c
        if cl in ("label", "class", "category", "target"):
            label_col = c

    if text_col is None:
        # Fallback: use the first non-label column
        text_col = [c for c in df.columns if c.lower() not in ("label", "class", "category", "target")][0]
    if label_col is None:
        label_col = [c for c in df.columns if c.lower() in ("label", "class", "category", "target")][0]

    # Filter vishing rows only
    df_vishing = df[df[label_col].str.lower().str.strip() == "vishing"].copy()
    df_vishing = df_vishing.dropna(subset=[text_col])
    df_vishing = df_vishing.drop_duplicates(subset=[text_col])

    texts = df_vishing[text_col].astype(str).tolist()

    if not texts:
        return 0

    # Embed in batches
    model = _get_embed_model()
    batch_size = 64
    total_added = 0

    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        ids = [_make_id(t) for t in batch_texts]

        # Classify scam type heuristically from transcript content
        metadatas = []
        for t in batch_texts:
            scam_type = _classify_scam_type(t)
            metadatas.append({
                "scam_type": scam_type,
                "text_preview": t[:200],
            })

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=metadatas,
        )
        total_added += len(batch_texts)

    return total_added


def _classify_scam_type(text: str) -> str:
    """Simple heuristic scam type classification from transcript keywords."""
    t = text.lower()
    if any(w in t for w in ["bank", "account number", "credit card", "debit card", "pin"]):
        return "Bank Impersonation"
    if any(w in t for w in ["otp", "one time password", "verification code", "one-time"]):
        return "OTP Fraud"
    if any(w in t for w in ["tech support", "microsoft", "windows", "virus", "malware", "computer"]):
        return "Tech Support Scam"
    if any(w in t for w in ["tax", "irs", "lhdn", "revenue", "customs"]):
        return "Government Impersonation"
    if any(w in t for w in ["prize", "winner", "lottery", "congratulation", "reward"]):
        return "Prize / Lottery Scam"
    if any(w in t for w in ["police", "arrest", "warrant", "legal action", "court"]):
        return "Authority Threat Scam"
    if any(w in t for w in ["refund", "overpayment", "reimbursement"]):
        return "Refund Scam"
    if any(w in t for w in ["investment", "crypto", "bitcoin", "trading", "stock"]):
        return "Investment Fraud"
    return "General Vishing"


# ─────────────────────────────────────────────────
# QUERY SIMILAR SCAMS
# ─────────────────────────────────────────────────

def query_similar_scams(transcript: str, n_results: int = 2) -> list[dict]:
    """
    Find the top-N most similar historical scam cases.

    Returns
    -------
    list of dicts, each with:
        - text_preview  : first 200 chars of the matched transcript
        - scam_type     : heuristic scam category
        - similarity    : cosine similarity score (0-1, higher = more similar)
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    model = _get_embed_model()
    query_embedding = model.encode([transcript], show_progress_bar=False).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(n_results, collection.count()),
        include=["metadatas", "distances", "documents"],
    )

    similar = []
    if results and results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            # ChromaDB returns cosine distance; similarity = 1 - distance
            distance = results["distances"][0][i] if results["distances"] else 0
            similarity = round(1.0 - distance, 4)

            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            doc = results["documents"][0][i] if results["documents"] else ""

            similar.append({
                "text_preview": meta.get("text_preview", doc[:200]),
                "scam_type": meta.get("scam_type", "Unknown"),
                "similarity": similarity,
            })

    return similar


# ─────────────────────────────────────────────────
# ENSURE LIBRARY (call on startup)
# ─────────────────────────────────────────────────

def ensure_scam_library() -> int:
    """
    Build the scam library if not already populated.
    Returns the number of entries in the collection.
    """
    try:
        count = build_scam_library()
        return count
    except FileNotFoundError:
        return 0
    except Exception as e:
        print(f"[RAG] Warning: Could not build scam library: {e}")
        return 0
