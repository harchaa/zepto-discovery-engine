"""
Phase 5 correction pass, per DOCS/00b_REVIEW_NOTES_ROUND2.md findings from the human spot-check.

Two systematic tagging errors were confirmed by manually reading ~20 tagged reviews against
their LLM tags:

1. `friction_scope: category_exploration` was over-applied to routine ops/quality complaints on
   CORE STAPLE categories (rotten produce, damaged items, pricing, UX bugs) that have nothing to
   do with trying/avoiding a NEW category - most visibly via `quality_perishables`, which was
   leading the category-exploration count. This deterministically re-derives friction_scope from
   friction_type + category_mentioned instead of trusting the model's own scope label: scope is
   only category_exploration when the friction_type itself signals category-newness
   (quality_uncertainty_unfamiliar_category, product_authenticity, no_info_before_purchase,
   sizing_fit_uncertainty, trust_vs_specialist_retailer) or a genuinely new-adjacent category is
   mentioned - not just because the model said so.

2. `behavior_signal: stated_avoidance` was applied to reviews with no actual avoidance statement
   (e.g. a plain price complaint). Filtered to require an explicit avoidance-indicating phrase in
   the review text ("avoid", "never buy", "won't buy", "stopped buying", "boycott", "don't ever",
   "stopped using", etc.) - English-only, a known limitation for non-English avoidance statements
   (documented, not silently assumed away). The phrase list was expanded after a round-2
   spot-check found it too narrow, wrongly stripping real avoidance statements phrased as "don't
   ever order" or "stopped using it".

3. Reddit posts merely name-dropping "Zepto" without being about an actual shopping/product
   experience (a tech-interview-topics joke, a stock-market comment) were still getting a friction
   tag, because `off_topic_flag` (set during cleaning) only checks whether the word "zepto"
   appears - not whether the post is about the shopping experience. `looks_off_topic()` adds a
   second, narrower check: if a Reddit record has a friction tag but its text contains none of a
   broad commerce-keyword list, it's reset to friction_scope=none rather than trusting the model's
   attempt to force-fit unrelated content into the taxonomy.

4. `category_mentioned` occasionally got 3+ categories on one record (up to 6 on one) - found by
   manually tracing a thin/confusing chatbot answer about "beauty products" back to its retrieved
   reviews, two of which turned out to be a Reddit startup-pitch post name-dropping many product
   types (not a Zepto review at all) and an unrelated platform price-comparison post. A real
   review essentially never legitimately spans 3+ specific product categories - `MAX_PLAUSIBLE_
   CATEGORIES` resets any record exceeding it to `not_category_specific`. Only 5 of 6,088 embedded
   records were affected (0.08%), but for a rare category like beauty/personal_care (0.25% of the
   sample to begin with), even a couple of polluting records meaningfully worsen retrieval.

This is a free, instant, deterministic pass - re-tagging everything via the LLM would cost real
quota to fix what a rule can fix directly. Src/tag_at_scale.py's TAXONOMY_PROMPT is separately
tightened so NEW tagging doesn't keep repeating the same errors going forward.
"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl, write_jsonl  # noqa: E402

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")

EXPLORATION_SIGNAL_FRICTION_TYPES = {
    "quality_uncertainty_unfamiliar_category", "product_authenticity",
    "no_info_before_purchase", "sizing_fit_uncertainty", "trust_vs_specialist_retailer",
}
NEW_ADJACENT_CATEGORIES = {
    "personal_care", "beauty", "baby_care", "pet_care", "pharmacy_health", "electronics", "apparel",
}
AVOIDANCE_PHRASES = [
    "avoid", "never buy", "never order", "never ordering", "never using", "wont buy",
    "won't buy", "will not buy", "won't order", "wont order", "stopped buying",
    "stopped ordering", "stopped using", "boycott", "not buying", "not going to buy",
    "don't ever", "dont ever", "don't use", "dont use", "please don't use",
    "won't use", "wont use",
]

# Round-2 spot-check (a fresh sample after the friction_scope/avoidance fixes) found a further
# error: Reddit posts that merely name-drop "Zepto" without being about an actual shopping/product
# experience (a tech-interview-topics joke, a stock-market comment) were still getting tagged
# category_exploration/generic_ops with an invented friction_type, because off_topic_flag (set
# during cleaning) only checks whether the word "zepto" appears - it doesn't check whether the
# post is actually ABOUT the shopping experience. Play Store/App Store reviews aren't at risk
# here (writing one is inherently about the app), so this only applies to Reddit.
COMMERCE_KEYWORDS = [
    "order", "deliver", "buy", "bought", "purchase", "product", "item", "app", "refund",
    "service", "quality", "price", "pricing", "package", "packaging", "review", "shop",
    "store", "cart", "checkout", "payment", "customer", "support", "complain", "return",
    "exchange", "discount", "coupon", "offer", "groceries", "grocery", "fruit", "vegetable",
    "delivery", "rider", "captain", "app crash", "bug", "subscription", "membership",
    "area", "available", "availability", "trust", "genuine", "authentic", "fake", "quality",
    "cheap", "expensive", "brand", "stock", "pincode",
]


def looks_off_topic(record):
    if record.get("source") != "reddit":
        return False
    if record.get("friction_scope") in (None, "none"):
        return False
    text = (record.get("text") or "").lower()
    return not any(k in text for k in COMMERCE_KEYWORDS)


def recompute_friction_scope(record):
    ftypes = set(record.get("friction_type") or [])
    cats = set(record.get("category_mentioned") or [])
    if not ftypes:
        return "none"
    if (ftypes & EXPLORATION_SIGNAL_FRICTION_TYPES) or (cats & NEW_ADJACENT_CATEGORIES):
        return "category_exploration"
    return "generic_ops"


def has_avoidance_language(text):
    t = (text or "").lower()
    return any(p in t for p in AVOIDANCE_PHRASES)


# A 4th systematic error, found by manually tracing a chatbot answer back to its retrieved
# reviews: a handful of records got tagged with 3+ categories at once (up to 6 on one record) -
# a real review essentially never legitimately spans that many specific product categories in one
# sitting. Checked: only 5 of 6,088 embedded substantive records hit this (0.08%), and all 5 were
# garbage on inspection - a Reddit startup-pitch post name-dropping many product types while
# validating a business idea (not a Zepto review at all), a Blinkit/Zepto-vs-BigBasket comparison
# post, and generic/gibberish text. High-precision, low-volume signal: safe to reset outright
# rather than needing a broader off-topic check.
MAX_PLAUSIBLE_CATEGORIES = 2


def has_category_overtagging(record):
    return len(record.get("category_mentioned") or []) > MAX_PLAUSIBLE_CATEGORIES


def main():
    tagged_path = f"{PROCESSED_DIR}/tagged_reviews.jsonl"
    cleaned_path = f"{PROCESSED_DIR}/cleaned_reviews.jsonl"
    tagged = read_jsonl(tagged_path)
    cleaned_by_id = {r["record_id"]: r for r in read_jsonl(cleaned_path)}
    print(f"Loaded {len(tagged)} tagged records")

    scope_changed = 0
    avoidance_removed = 0
    requeued = 0
    off_topic_reset = 0
    category_overtag_reset = 0
    corrected = []
    for t in tagged:
        t = dict(t)
        if t.get("auto_tagged_trivial"):
            c = cleaned_by_id.get(t["id"])
            if c and c.get("rating") is not None and c["rating"] <= 2:
                # is_trivial() no longer classifies low-rating reviews as trivial (see
                # tag_at_scale.py) - drop this stale auto-tag entirely so it gets re-queued into
                # the substantive LLM pool on the next tagging run instead of keeping a wrong tag.
                requeued += 1
                continue
            corrected.append(t)
            continue
        if t.get("auto_tagged_insufficient_text"):
            corrected.append(t)
            continue

        c = cleaned_by_id.get(t["id"]) or {}
        merged = {**c, **t}

        if has_category_overtagging(t):
            category_overtag_reset += 1
            t["category_mentioned_corrected_from"] = t.get("category_mentioned")
            t["category_mentioned"] = ["not_category_specific"]
            merged["category_mentioned"] = t["category_mentioned"]

        if looks_off_topic(merged):
            off_topic_reset += 1
            # Keep the pre-correction tags around (not just friction_scope) so a future keyword
            # refinement can restore a record if it turns out this reset it wrongly - the very
            # thing that would otherwise happen silently if a fix here needed a fix of its own.
            t["pre_off_topic_correction"] = {
                "friction_scope": t.get("friction_scope"),
                "friction_type": t.get("friction_type"),
                "category_mentioned": t.get("category_mentioned"),
                "behavior_signal": t.get("behavior_signal"),
            }
            t["friction_scope"] = "none"
            t["friction_type"] = []
            t["category_mentioned"] = ["not_category_specific"]
            t["behavior_signal"] = ["none_detected"]
            t["off_topic_content_corrected"] = True
            corrected.append(t)
            continue

        if t.get("off_topic_content_corrected") and "pre_off_topic_correction" in t:
            # Re-evaluate a previous reset against the current (possibly wider) keyword list,
            # using the ORIGINAL pre-reset tags - otherwise a reset record reads friction_scope
            # "none" forever and can never be un-reset even if the keyword list improves.
            prior = t["pre_off_topic_correction"]
            if not looks_off_topic({**c, **prior}):
                t.update(prior)
                del t["pre_off_topic_correction"]
                del t["off_topic_content_corrected"]
                off_topic_reset -= 1  # restored, not a fresh reset this run

        old_scope = t.get("friction_scope")
        new_scope = recompute_friction_scope(t)
        if new_scope != old_scope:
            scope_changed += 1
            t["friction_scope"] = new_scope
            t["friction_scope_corrected_from"] = old_scope

        if "stated_avoidance" in (t.get("behavior_signal") or []):
            text = c.get("text", "")
            if not has_avoidance_language(text):
                t["behavior_signal"] = [b for b in t["behavior_signal"] if b != "stated_avoidance"]
                if not t["behavior_signal"]:
                    t["behavior_signal"] = ["none_detected"]
                avoidance_removed += 1

        corrected.append(t)

    print(f"friction_scope corrected: {scope_changed}")
    print(f"stated_avoidance removed (no avoidance language found in text): {avoidance_removed}")
    print(f"low-rating trivial auto-tags dropped for re-queueing to LLM: {requeued}")
    print(f"off-topic Reddit content reset to friction_scope=none: {off_topic_reset}")
    print(f"category_mentioned over-tagging (3+ categories) reset to not_category_specific: {category_overtag_reset}")

    write_jsonl(tagged_path, corrected)
    print(f"Wrote corrected tags back to {tagged_path}")


if __name__ == "__main__":
    main()
