"""
Phase 4 - embeddings index for the "Ask the Reviews" RAG chatbot.

Embeds every tagged, on-topic review (local sentence-transformers model - see
DOCS/01_PLAN.md open questions for why local over a paid hosted embeddings API) and
stores the vectors + metadata for cosine-similarity retrieval. Incremental: only embeds
records not already in the index, so it can be re-run as tagging accumulates more data.
"""
import json
import os
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl  # noqa: E402

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")
INDEX_PATH = f"{PROCESSED_DIR}/embeddings.npz"
META_PATH = f"{PROCESSED_DIR}/embeddings_meta.jsonl"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_existing():
    try:
        data = np.load(INDEX_PATH)
        with open(META_PATH, encoding="utf-8") as f:
            meta = [json.loads(line) for line in f]
        return data["embeddings"], meta
    except FileNotFoundError:
        return None, []


def main():
    export_path = f"{PROCESSED_DIR}/app_export.jsonl"
    if not os.path.exists(export_path):
        print("app_export.jsonl not found - run src/analyze_patterns.py first.")
        return
    rows = read_jsonl(export_path)
    print(f"{len(rows)} tagged, on-topic records available")

    existing_emb, existing_meta = load_existing()
    existing_ids = {m["id"] for m in existing_meta}
    todo = [r for r in rows if r["record_id"] not in existing_ids and (r.get("text") or "").strip()]
    print(f"{len(existing_meta)} already embedded, {len(todo)} new to embed")

    if not todo:
        print("Nothing new to embed.")
        return

    model = SentenceTransformer(MODEL_NAME)
    texts = [(r.get("title") + " - " if r.get("title") else "") + r["text"] for r in todo]
    new_embeddings = model.encode(texts, show_progress_bar=True, batch_size=64, normalize_embeddings=True)

    new_meta = [{
        "id": r["record_id"],
        "source": r["source"],
        "date": r.get("date"),
        "rating": r.get("rating"),
        "text": r["text"][:500],
        "category_mentioned": r.get("category_mentioned"),
        "friction_scope": r.get("friction_scope"),
        "friction_type": r.get("friction_type"),
        "behavior_signal": r.get("behavior_signal"),
        "sentiment": r.get("sentiment"),
    } for r in todo]

    if existing_emb is not None:
        all_embeddings = np.vstack([existing_emb, new_embeddings])
    else:
        all_embeddings = new_embeddings
    all_meta = existing_meta + new_meta

    np.savez_compressed(INDEX_PATH, embeddings=all_embeddings)
    with open(META_PATH, "w", encoding="utf-8") as f:
        for m in all_meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"Index now has {len(all_meta)} embedded records -> {INDEX_PATH}, {META_PATH}")


if __name__ == "__main__":
    main()
