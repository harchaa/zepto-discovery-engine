"""
Phase 2 - Step 2d (Tag at scale), per DOCS/01_PLAN.md and Taxonomy v1
(DOCS/04_TAXONOMY_DRAFT_v0.md, finalized after the open-coding pass).

Batches multiple cleaned records into one Groq call (JSON mode) to make the most of a
rate-limited API, tags each against the taxonomy, and checkpoints incrementally so the
job can be killed/resumed without re-tagging anything (skips record_ids already present
in the output file). Designed to run as a long background job - the corpus doesn't need
to be 100% final before starting; re-running later just picks up any new records.

Records with insufficient text are tagged locally (no API call, nothing to read).
"""
import json
import random
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl  # noqa: E402
from groq_client import TAGGING_MODEL, QuotaExhausted, chat  # noqa: E402

random.seed(42)

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")
BATCH_SIZE = 25  # llama-3.1-8b-instant's TPM cap is 6,000 (vs 12,000 for the 70B model) - a
# smaller batch keeps (prompt_tokens + max_tokens) safely under that per-request reservation
MAX_TOKENS_PER_ITEM = 110  # observed actual ~93/item; adds headroom without over-reserving
SLEEP_BETWEEN_BATCHES = 45.0  # paced to the 6,000 TPM budget at ~4k tokens/batch-of-25

TAXONOMY_PROMPT = """You are tagging user feedback about Zepto (an Indian quick-commerce grocery \
app) for a research project studying why users repeat-buy the same categories (groceries, snacks) \
and rarely try new ones (personal care, beauty, baby, pet, pharmacy, electronics, apparel).

For EACH numbered review below, return one JSON object with these exact fields:
- "id": the review's given id (copy exactly)
- "category_mentioned": array from [groceries_staples, snacks_beverages, personal_care, beauty, \
baby_care, pet_care, pharmacy_health, electronics, apparel, home_kitchen, not_category_specific]
- "sentiment": one of [positive, negative, mixed, neutral]
- "friction_scope": one of [generic_ops, category_exploration, ambiguous, none] - generic_ops = \
delivery/refund/app bug/support issues that would happen regardless of category; \
category_exploration = friction specifically about trust/fit/authenticity/info-gap when trying or \
avoiding a NEW (non-staple) category; none = no friction expressed
- "friction_type": array of short lowercase_snake_case tags describing the specific friction(s), \
e.g. delivery_speed, damaged_in_transit, no_easy_refund, product_authenticity, \
quality_uncertainty_unfamiliar_category, sizing_fit_uncertainty, no_info_before_purchase, \
quality_perishables, app_ux_bug, customer_support, pricing_value, trust_vs_specialist_retailer - or \
[] if none
- "behavior_signal": array from [habit_repeat_purchase, discovery_channel_mentioned, \
stated_avoidance, exploration_attempt_positive, exploration_attempt_negative, none_detected]. \
IMPORTANT: stated_avoidance means the user explicitly says they avoid/never buy a SPECIFIC \
PRODUCT CATEGORY (e.g. "I never buy fruits here", "won't buy electronics on Zepto"). Do NOT use \
it for general app-abandonment venting like "I'm never using this app again" over a delivery/ \
refund/support complaint - that is just negative sentiment, not category avoidance.
- "segment_hint": array from [self_described_tenure, comparison_to_competitor, \
price_sensitive_language, convenience_seeking_language, none]

Return ONLY a JSON object: {{"results": [ {{...}}, {{...}} ]}} with one entry per review, same \
order, same ids. Do not add commentary.

REVIEWS:
{items}
"""


def format_batch(batch):
    lines = []
    for i, r in enumerate(batch, 1):
        text = (r.get("title") + " - " if r.get("title") else "") + (r.get("text") or "")
        text = text.replace("\n", " ")[:1200]
        lines.append(f'{i}. id="{r["record_id"]}": """{text}"""')
    return "\n".join(lines)


def auto_tag_insufficient(r):
    return {
        "id": r["record_id"],
        "category_mentioned": ["not_category_specific"],
        "sentiment": "neutral",
        "friction_scope": "none",
        "friction_type": [],
        "behavior_signal": ["none_detected"],
        "segment_hint": ["none"],
        "auto_tagged_insufficient_text": True,
    }


def load_already_tagged(path):
    try:
        rows = read_jsonl(path)
        return {r["id"]: r for r in rows}
    except FileNotFoundError:
        return {}


def main():
    records = read_jsonl(f"{PROCESSED_DIR}/cleaned_reviews.jsonl")
    out_path = f"{PROCESSED_DIR}/tagged_reviews.jsonl"
    already = load_already_tagged(out_path)
    print(f"Loaded {len(records)} cleaned records, {len(already)} already tagged")

    todo = [r for r in records if r["record_id"] not in already]
    random.shuffle(todo)  # unbiased order: Groq's daily request cap means this may run over
    # multiple days, so whatever fraction is done at any point must be a valid random subsample
    # of the whole corpus, not e.g. all-Play-Store-NEWEST-first from scrape order.
    print(f"{len(todo)} records left to tag (shuffled for unbiased partial coverage)")

    out_f = open(out_path, "a", encoding="utf-8")
    tagged_count = 0
    failed_count = 0
    start = time.time()

    batch = []
    for idx, r in enumerate(todo):
        if r.get("insufficient_text"):
            tag = auto_tag_insufficient(r)
            out_f.write(json.dumps(tag, ensure_ascii=False) + "\n")
            tagged_count += 1
            continue
        batch.append(r)
        if len(batch) < BATCH_SIZE and idx != len(todo) - 1:
            continue

        prompt = TAXONOMY_PROMPT.format(items=format_batch(batch))
        try:
            raw = chat(
                [{"role": "user", "content": prompt}],
                max_tokens=len(batch) * MAX_TOKENS_PER_ITEM,
                response_format={"type": "json_object"},
                model=TAGGING_MODEL,
            )
            parsed = json.loads(raw)
            results = {item["id"]: item for item in parsed.get("results", [])}
            for r2 in batch:
                tag = results.get(r2["record_id"])
                if tag is None:
                    failed_count += 1
                    continue
                out_f.write(json.dumps(tag, ensure_ascii=False) + "\n")
                tagged_count += 1
        except QuotaExhausted as e:
            out_f.flush()
            out_f.close()
            elapsed = time.time() - start
            print(f"\nSTOPPING: Groq's daily quota is exhausted for now ({e}).")
            print(f"Tagged {tagged_count} in this run ({elapsed / 60:.1f} min). "
                  f"Re-run this script later (it resumes automatically, skipping tagged ids) "
                  f"once the quota resets.")
            return
        except Exception as e:
            print(f"  BATCH FAILED ({len(batch)} records): {e}")
            failed_count += len(batch)

        out_f.flush()
        batch = []

        if tagged_count % 120 == 0 and tagged_count > 0:
            elapsed = time.time() - start
            rate = tagged_count / elapsed * 60
            remaining = len(todo) - tagged_count - failed_count
            eta_min = remaining / rate if rate > 0 else float("inf")
            print(f"  progress: {tagged_count} tagged, {failed_count} failed, "
                  f"{rate:.0f}/min, ETA {eta_min:.0f} min for remaining {remaining}")

        time.sleep(SLEEP_BETWEEN_BATCHES)

    out_f.close()
    print(f"\nDone. Tagged {tagged_count}, failed {failed_count}. Output: {out_path}")


if __name__ == "__main__":
    main()
