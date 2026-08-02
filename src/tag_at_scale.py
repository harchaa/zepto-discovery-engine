"""
Phase 2 - Step 2d (Tag at scale), per DOCS/01_PLAN.md and Taxonomy v1
(DOCS/04_TAXONOMY_DRAFT_v0.md, finalized after the open-coding pass).

Three-tier workload split, added after hitting Groq's daily token quota on both models
(see DOCS/03_THOUGHT_PROCESS.md decisions table) - the goal was never "tag literally
every gathered review," it's "enough tagged volume to answer the 8 RQs with credible
counts," so LLM calls are reserved for records that actually need judgment:

1. Off-topic Reddit matches (`off_topic_flag`) - excluded entirely, not even auto-tagged.
   They're thrown away at analysis time anyway (see common.load_joined_tagged), so
   sending them to the LLM was pure waste (~18% of the cleaned corpus).
2. Insufficient-text and "trivial" records (short, no friction/category/avoidance
   keyword - "good", "nice app", "very good and useful") - auto-tagged deterministically,
   zero LLM cost. The keyword list is a BLOCKLIST (exclude if any signal word present),
   not an allowlist, so it also safely catches Hinglish short praise without needing to
   enumerate every language's version of "good" (~35% of the cleaned corpus).
3. Everything else ("substantive") - the pool that actually needs LLM nuance (sarcasm,
   multi-topic, category-exploration judgment). Sampled randomly up to TARGET_SUBSTANTIVE
   total (across all runs, resumable) rather than tagging the entire pool - a large
   enough random sample answers the research questions just as well as full coverage,
   at a fraction of the token cost.

Batches multiple records into one Groq call (JSON mode), checkpoints incrementally so the
job can be killed/resumed without re-tagging anything (skips record_ids already present
in the output file).
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
TARGET_SUBSTANTIVE = 20000  # total substantive records to LLM-tag across all runs (see docstring).
# Tagging was deliberately stopped at 6,252 (31%) on Aug 2 2026 - two API keys' daily quotas were
# both exhausted and the sample was judged sufficient to proceed (see DOCS/07_VALIDATION_REPORT.md
# and README.md). Left at 20,000 here rather than lowered, so re-running this script later simply
# continues toward the original target instead of needing to be reconfigured.

TRIVIAL_MAX_LEN = 40
SIGNAL_KEYWORDS = [
    "refund", "deliver", "cancel", "damag", "rotten", "stale", "fake", "quality", "support",
    "beauty", "electronic", "pharmacy", "apparel", "pet ", "baby", "cosmetic", "perfume",
    "makeup", "skincare", "medicine", "clothes", "cloth ", "fit ", "size", "authentic",
    "expire", "complain", "wrong item", "replace", "return", "price", "discount", "coupon",
    "cash", "offer", "slow", "late", "never", "avoid", "worst", "pathetic", "fraud", "cheat",
    "scam", "captain", "rider", "driver", "crash", "not working", "bug", "login",
    "payment fail", "otp", "order not", "missing item", "trust", "duplicate", "genuine",
    "smell", "taste", "mold", "insect", "worm", "first time", "wont buy", "won't buy",
    "stopped buying", "category", "trying", "tried",
]
POSITIVE_WORDS = {"good", "nice", "great", "excellent", "awesome", "super", "best", "fast",
                   "love", "superb", "osm", "gud", "amazing", "perfect"}
NEGATIVE_WORDS = {"bad", "worst", "pathetic", "useless", "poor", "waste", "horrible", "terrible"}

TAXONOMY_PROMPT = """You are tagging user feedback about Zepto (an Indian quick-commerce grocery \
app) for a research project studying why users repeat-buy the same categories (groceries, snacks) \
and rarely try new ones (personal care, beauty, baby, pet, pharmacy, electronics, apparel).

IMPORTANT FIRST CHECK: some Reddit posts merely mention the word "Zepto" without actually being \
about a shopping/product/delivery experience with it - a joke about tech-interview topics at \
different companies, a stock-market comment, an unrelated meme. If the text is NOT actually \
describing a real shopping/product/service experience with Zepto, tag it as: category_mentioned \
[not_category_specific], sentiment neutral (unless clearly positive/negative about something \
else), friction_scope none, friction_type [], behavior_signal [none_detected]. Do not force-fit \
off-topic content into the taxonomy just because it contains a category-sounding word.

For EACH numbered review below, return one JSON object with these exact fields:
- "id": the review's given id (copy exactly)
- "category_mentioned": array from [groceries_staples, snacks_beverages, personal_care, beauty, \
baby_care, pet_care, pharmacy_health, electronics, apparel, home_kitchen, not_category_specific]
- "sentiment": one of [positive, negative, mixed, neutral]
- "friction_scope": one of [generic_ops, category_exploration, ambiguous, none]. STRICT TEST: \
category_exploration applies ONLY if the friction is specifically about trust, authenticity, fit, \
or an information gap when trying/avoiding a NEW category the platform doesn't specialize in \
(personal care, beauty, baby, pet, pharmacy, electronics, apparel) - the review must be about \
WHETHER TO TRUST/TRY that category, not just a bad experience with an order. If unsure, or if the \
category is groceries/snacks/staples, or if it's a routine quality/delivery/refund/pricing/app \
complaint (even about produce, dairy, or damaged items), it is generic_ops, NOT category_exploration \
- "damaged item", "rotten vegetables", "wrong item", "slow delivery", "high price", "app bug" are \
ALWAYS generic_ops regardless of which category the item was in, UNLESS the review explicitly \
questions the authenticity/genuineness of a non-staple product or says they don't trust buying \
that unfamiliar category here. Example: "vegetables were rotten" = generic_ops. Example: "not sure \
if this perfume is a genuine/original product, first time buying cosmetics here" = \
category_exploration.
- "friction_type": array of short lowercase_snake_case tags describing the specific friction(s), \
e.g. delivery_speed, damaged_in_transit, no_easy_refund, product_authenticity, \
quality_uncertainty_unfamiliar_category, sizing_fit_uncertainty, no_info_before_purchase, \
quality_perishables, app_ux_bug, customer_support, pricing_value, trust_vs_specialist_retailer - or \
[] if none. NOTE: quality_perishables (rotten/expired produce) is a generic_ops signal by itself - \
it only makes friction_scope category_exploration if paired with an explicit authenticity/trust/ \
unfamiliar-category statement, not just because the product happened to be perishable.
- "behavior_signal": array from [habit_repeat_purchase, discovery_channel_mentioned, \
stated_avoidance, exploration_attempt_positive, exploration_attempt_negative, none_detected]. \
IMPORTANT: stated_avoidance means the user uses an explicit AVOIDANCE VERB about a SPECIFIC \
PRODUCT CATEGORY - "avoid", "never buy", "won't buy", "stopped buying", "boycott" - e.g. "I never \
buy fruits here", "won't buy electronics on Zepto". A complaint about price, quality, or service \
WITHOUT one of those explicit avoidance words is NOT stated_avoidance, even if strongly negative - \
"every product high price" or "very disappointed with service" is just negative sentiment, not \
avoidance. Do NOT use it for general app-abandonment venting ("I'm never using this app again") \
over a delivery/refund/support complaint either - that's app-level frustration, not category \
avoidance.
- "segment_hint": array from [self_described_tenure, comparison_to_competitor, \
price_sensitive_language, convenience_seeking_language, none]

Return ONLY a JSON object: {{"results": [ {{...}}, {{...}} ]}} with one entry per review, same \
order, same ids. Do not add commentary.

REVIEWS:
{items}
"""


def is_off_topic(r):
    return bool(r.get("off_topic_flag"))


def is_trivial(r):
    t = (r.get("text") or "").strip().lower()
    if len(t) > TRIVIAL_MAX_LEN:
        return False
    rating = r.get("rating")
    if rating is not None and rating <= 2:
        # 1-2 star reviews concentrate real friction signal even in very short text ("packet is
        # leaked", "most faltu") that a keyword blocklist won't catch - a simple keyword-based
        # sentiment/friction guess on these is unreliable (confirmed via spot-check: ~2,951 such
        # reviews were being auto-tagged "neutral" when the rating alone says otherwise). Always
        # send low-rated reviews to the LLM regardless of length/keywords.
        return False
    return not any(k in t for k in SIGNAL_KEYWORDS)


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


def auto_tag_trivial(r):
    t = (r.get("text") or "").strip().lower()
    has_pos = any(w in t for w in POSITIVE_WORDS)
    has_neg = any(w in t for w in NEGATIVE_WORDS)
    sentiment = "mixed" if (has_pos and has_neg) else ("positive" if has_pos else ("negative" if has_neg else "neutral"))
    return {
        "id": r["record_id"],
        "category_mentioned": ["not_category_specific"],
        "sentiment": sentiment,
        "friction_scope": "none",
        "friction_type": [],
        "behavior_signal": ["none_detected"],
        "segment_hint": ["none"],
        "auto_tagged_trivial": True,
    }


def load_already_tagged(path):
    try:
        rows = read_jsonl(path)
        return {r["id"]: r for r in rows}
    except FileNotFoundError:
        return {}


def main():
    records = read_jsonl(f"{PROCESSED_DIR}/cleaned_reviews.jsonl")
    cleaned_by_id = {r["record_id"]: r for r in records}
    out_path = f"{PROCESSED_DIR}/tagged_reviews.jsonl"
    already = load_already_tagged(out_path)
    print(f"Loaded {len(records)} cleaned records, {len(already)} already tagged")

    todo_all = [r for r in records if r["record_id"] not in already]
    off_topic = [r for r in todo_all if is_off_topic(r)]
    insufficient = [r for r in todo_all if not is_off_topic(r) and r.get("insufficient_text")]
    trivial = [r for r in todo_all if not is_off_topic(r) and not r.get("insufficient_text") and is_trivial(r)]
    substantive = [r for r in todo_all if not is_off_topic(r) and not r.get("insufficient_text") and not is_trivial(r)]

    print(f"  off_topic (skipped entirely, not tagged): {len(off_topic)}")
    print(f"  insufficient_text (auto-tagged, no LLM): {len(insufficient)}")
    print(f"  trivial (auto-tagged, no LLM): {len(trivial)}")
    print(f"  substantive (LLM-bound pool): {len(substantive)}")

    out_f = open(out_path, "a", encoding="utf-8")
    auto_count = 0
    for r in insufficient:
        out_f.write(json.dumps(auto_tag_insufficient(r), ensure_ascii=False) + "\n")
        auto_count += 1
    for r in trivial:
        out_f.write(json.dumps(auto_tag_trivial(r), ensure_ascii=False) + "\n")
        auto_count += 1
    out_f.flush()
    print(f"Auto-tagged {auto_count} records deterministically (zero LLM cost)")

    already_substantive = sum(
        1 for rid in already
        if rid in cleaned_by_id and not is_off_topic(cleaned_by_id[rid])
        and not cleaned_by_id[rid].get("insufficient_text") and not is_trivial(cleaned_by_id[rid])
    )
    remaining_target = max(0, TARGET_SUBSTANTIVE - already_substantive)
    print(f"Substantive already LLM-tagged (prior runs): {already_substantive} / target {TARGET_SUBSTANTIVE} "
          f"-> {remaining_target} remaining this run")

    random.shuffle(substantive)
    todo = substantive[:remaining_target]
    print(f"{len(todo)} substantive records queued for the LLM this run (capped at target)")

    tagged_count = 0
    failed_count = 0
    start = time.time()

    batch = []
    for idx, r in enumerate(todo):
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
            print(f"LLM-tagged {tagged_count} in this run ({elapsed / 60:.1f} min), plus "
                  f"{auto_count} auto-tagged. Re-run later (resumes automatically) once the "
                  f"quota resets.")
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
            print(f"  progress: {tagged_count} LLM-tagged, {failed_count} failed, "
                  f"{rate:.0f}/min, ETA {eta_min:.0f} min for remaining {remaining}")

        time.sleep(SLEEP_BETWEEN_BATCHES)

    out_f.close()
    print(f"\nDone. LLM-tagged {tagged_count}, auto-tagged {auto_count}, failed {failed_count}. "
          f"Output: {out_path}")


if __name__ == "__main__":
    main()
