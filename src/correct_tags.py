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
   the review text ("avoid", "never buy", "won't buy", "stopped buying", "boycott", etc.) -
   English-only, a known limitation for non-English avoidance statements (documented, not silently
   assumed away).

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
    "avoid", "never buy", "never order", "wont buy", "won't buy", "will not buy",
    "stopped buying", "stopped ordering", "boycott", "not buying", "not going to buy",
]


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


def main():
    tagged_path = f"{PROCESSED_DIR}/tagged_reviews.jsonl"
    cleaned_path = f"{PROCESSED_DIR}/cleaned_reviews.jsonl"
    tagged = read_jsonl(tagged_path)
    cleaned_by_id = {r["record_id"]: r for r in read_jsonl(cleaned_path)}
    print(f"Loaded {len(tagged)} tagged records")

    scope_changed = 0
    avoidance_removed = 0
    requeued = 0
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

        old_scope = t.get("friction_scope")
        new_scope = recompute_friction_scope(t)
        if new_scope != old_scope:
            scope_changed += 1
            t["friction_scope"] = new_scope
            t["friction_scope_corrected_from"] = old_scope

        if "stated_avoidance" in (t.get("behavior_signal") or []):
            text = (cleaned_by_id.get(t["id"]) or {}).get("text", "")
            if not has_avoidance_language(text):
                t["behavior_signal"] = [b for b in t["behavior_signal"] if b != "stated_avoidance"]
                if not t["behavior_signal"]:
                    t["behavior_signal"] = ["none_detected"]
                avoidance_removed += 1

        corrected.append(t)

    print(f"friction_scope corrected: {scope_changed}")
    print(f"stated_avoidance removed (no avoidance language found in text): {avoidance_removed}")
    print(f"low-rating trivial auto-tags dropped for re-queueing to LLM: {requeued}")

    write_jsonl(tagged_path, corrected)
    print(f"Wrote corrected tags back to {tagged_path}")


if __name__ == "__main__":
    main()
