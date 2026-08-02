"""
Phase 2 - Step 2b (Open-code a sample), per DOCS/01_PLAN.md and DOCS/02_WORKFLOW.md.

Draws a stratified sample from the cleaned corpus (by source, and by rating band for
Play Store / post type for Reddit) and runs an INDUCTIVE pass: the model describes each
review in its own words - what it's about, what friction/praise it expresses, whether it
signals a behavior pattern - without being constrained to a fixed taxonomy. This is the
input to manually clustering into Taxonomy v1 (DOCS/04_TAXONOMY_DRAFT_v0.md is only the
pre-open-coding hypothesis, not what gets used to tag the full corpus).
"""
import random
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl, write_jsonl  # noqa: E402
from groq_client import chat  # noqa: E402

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")
random.seed(42)

TARGET_PER_STRATUM = 30
BATCH_SIZE = 6  # requests are the scarce resource (Groq free tier: 1000/day) - batch to conserve
OPEN_CODE_PROMPT = """You are doing INDUCTIVE open-coding for a qualitative research project on a \
quick-commerce app (Zepto) in India. Do NOT force this into any fixed taxonomy - describe what is \
actually there, in plain language, even if it doesn't fit neat categories.

For EACH numbered review below, produce one entry with this exact structure:
id: <copy the given id exactly>
Category: <what product category, if any, is this about - use your own words>
Sentiment: <positive/negative/mixed/neutral, and briefly why>
Topic: <what is this actually about, in the user's own terms, one sentence>
Friction (if any): <describe the specific friction in your own words, or "none">
Friction nature: <does this friction feel like a GENERIC operational issue (delivery, refund, app \
bug, support - would happen regardless of what was ordered) or something SPECIFIC to trying/trusting \
a new/unfamiliar product category (authenticity, fit, quality-uncertainty, lack of info) - or "n/a">
Behavior signal: <habit/repeat-purchase, avoidance of a category, discovery of a product, an \
exploration attempt (good or bad outcome), or "none noticed">
Notes: <anything else surprising or noteworthy that doesn't fit above>

Return ONLY a JSON object: {{"results": [{{"id": "...", "coding": "the full multi-line structure \
above as one string"}}, ...]}}, one entry per review, same order, same ids.

REVIEWS:
{items}
"""


def stratum_key(r):
    if r["source"] == "play_store":
        rating = r.get("rating") or 0
        band = "neg" if rating <= 2 else ("neu" if rating == 3 else "pos")
        return ("play_store", band)
    return ("reddit", r.get("post_type", "unknown"))


def sample_corpus(records):
    eligible = [r for r in records if not r.get("off_topic_flag") and not r.get("insufficient_text")]
    by_stratum = defaultdict(list)
    for r in eligible:
        by_stratum[stratum_key(r)].append(r)

    sample = []
    print("Stratified sampling:")
    for key, rows in by_stratum.items():
        random.shuffle(rows)
        take = rows[:TARGET_PER_STRATUM]
        sample.extend(take)
        print(f"  {key}: {len(take)} sampled (of {len(rows)} eligible)")
    return sample


def main():
    records = read_jsonl(f"{PROCESSED_DIR}/cleaned_reviews.jsonl")
    print(f"Loaded {len(records)} cleaned records")

    sample = sample_corpus(records)
    print(f"\nTotal sample size: {len(sample)}, batch size {BATCH_SIZE} "
          f"-> ~{-(-len(sample) // BATCH_SIZE)} requests")

    by_id = {r["record_id"]: r for r in sample}
    results = []
    for start in range(0, len(sample), BATCH_SIZE):
        batch = sample[start:start + BATCH_SIZE]
        items = "\n".join(
            f'{i}. id="{r["record_id"]}": """'
            + ((r.get("title") + " - " if r.get("title") else "") + (r.get("text") or ""))[:1200]
            + '"""'
            for i, r in enumerate(batch, 1)
        )
        try:
            raw = chat(
                [{"role": "user", "content": OPEN_CODE_PROMPT.format(items=items)}],
                max_tokens=BATCH_SIZE * 220,
                response_format={"type": "json_object"},
            )
            import json
            parsed = json.loads(raw)
            for item in parsed.get("results", []):
                r = by_id.get(item.get("id"))
                if not r:
                    continue
                results.append({
                    "record_id": r["record_id"],
                    "source": r["source"],
                    "rating": r.get("rating"),
                    "stratum": list(stratum_key(r)),
                    "text": ((r.get("title") + " - " if r.get("title") else "") + (r.get("text") or ""))[:1200],
                    "open_coding": item.get("coding"),
                })
        except Exception as e:
            print(f"  batch at {start}: FAILED: {e}")
            continue

        print(f"  [{start + len(batch)}/{len(sample)}] open-coded, checkpointing...")
        write_jsonl(f"{PROCESSED_DIR}/open_coding_sample.jsonl", results)

    write_jsonl(f"{PROCESSED_DIR}/open_coding_sample.jsonl", results)
    print(f"\nWrote {len(results)} open-coded records to {PROCESSED_DIR}/open_coding_sample.jsonl")


if __name__ == "__main__":
    main()
