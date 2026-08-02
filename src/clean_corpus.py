"""
Phase 2 - Step 2a (Clean), per DOCS/01_PLAN.md.

Reads data/raw/unified_reviews.jsonl (Phase 1 output) and produces
data/processed/cleaned_reviews.jsonl:
- drops exact and near-duplicate text (normalized whitespace/case match)
- flags off-topic Reddit matches (query hit "zepto" but the record doesn't actually
  mention it - can happen for comments pulled from a matched post's thread)
- tags a `language` field (langdetect) - kept, not translated, per the plan's decision
  to tag directly rather than pre-translate (DOCS/01_PLAN.md open questions)
- flags empty/insufficient text rather than dropping the row (rating-only reviews are
  still useful for rating-distribution analysis even with no text to tag)

Does not touch friction/category/sentiment tagging - that's Phase 2b-2d (open-coding +
taxonomy + at-scale tagging).
"""
import re
import sys

from langdetect import DetectorFactory, LangDetectException, detect

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl, write_jsonl  # noqa: E402

DetectorFactory.seed = 0  # deterministic langdetect output
PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def detect_lang(text):
    if not text or len(text.strip()) < 3:
        return None
    try:
        return detect(text)
    except LangDetectException:
        return None


def main():
    records = read_jsonl(f"{RAW_DIR}/unified_reviews.jsonl")
    print(f"Loaded {len(records)} unified records")

    # near-duplicate dedupe by normalized text (within non-empty text only)
    seen_norm = {}
    kept = []
    dropped_near_dupe = 0
    for r in records:
        norm = normalize(r.get("text"))
        if norm and len(norm) > 15:
            if norm in seen_norm:
                dropped_near_dupe += 1
                continue
            seen_norm[norm] = r["record_id"]
        kept.append(r)
    print(f"Dropped {dropped_near_dupe} near-duplicate (normalized text) records")

    off_topic = 0
    empty_text = 0
    for r in kept:
        text_blob = f"{r.get('title') or ''} {r.get('text') or ''}"
        r["language"] = detect_lang(r.get("text") or r.get("title"))
        r["insufficient_text"] = not (r.get("text") and len(r["text"].strip()) >= 3)
        if r["insufficient_text"]:
            empty_text += 1
        if r["source"] == "reddit" and "zepto" not in text_blob.lower():
            r["off_topic_flag"] = True
            off_topic += 1
        else:
            r["off_topic_flag"] = False

    print(f"Flagged {empty_text} records with insufficient/empty text (kept, not dropped)")
    print(f"Flagged {off_topic} Reddit records as off-topic (no 'zepto' mention in title/text)")

    lang_counts = {}
    for r in kept:
        lang_counts[r["language"]] = lang_counts.get(r["language"], 0) + 1
    print("Language distribution:", dict(sorted(lang_counts.items(), key=lambda x: -x[1])))

    out_path = f"{PROCESSED_DIR}/cleaned_reviews.jsonl"
    write_jsonl(out_path, kept)
    print(f"\nWrote {len(kept)} cleaned records to {out_path}")


if __name__ == "__main__":
    main()
