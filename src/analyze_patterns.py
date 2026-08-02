"""
Phase 3 - Find patterns, per DOCS/01_PLAN.md and DOCS/02_WORKFLOW.md.

Joins the tagged dataset back to the cleaned corpus (for source/rating/date) and produces
the pattern tables the dashboard (Phase 4) consumes. Keeps the analytical lens split:
generic_ops friction is summarized only as background context; category_exploration
friction is the primary table everything else builds on (DOCS/03_THOUGHT_PROCESS.md §7).

Runs against whatever is in data/processed/tagged_reviews.jsonl at the time - tagging is
a resumable, randomized-order background process (see src/tag_at_scale.py), so this is
designed to be re-run as that sample grows, always reporting its actual N honestly rather
than presenting a partial tag as if it were the full corpus.
"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, dump_app_export, load_joined_tagged  # noqa: E402

PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")


def load_joined():
    return load_joined_tagged()


def rating_band(rating):
    if rating is None:
        return "n/a"
    return "neg(1-2)" if rating <= 2 else ("neu(3)" if rating == 3 else "pos(4-5)")


def counter_table(rows, field, multi=True):
    c = Counter()
    for r in rows:
        vals = r.get(field) or []
        if not multi:
            vals = [vals] if vals else []
        for v in vals:
            c[v] += 1
    return c.most_common()


def main():
    rows = load_joined()
    n = len(rows)
    print(f"Analyzing {n} tagged (and on-topic) records")
    if n == 0:
        print("Nothing tagged yet - run src/tag_at_scale.py first.")
        return

    by_source = Counter(r["source"] for r in rows)
    print(f"Source split: {dict(by_source)}")

    ops_rows = [r for r in rows if r.get("friction_scope") == "generic_ops"]
    exploration_rows = [r for r in rows if r.get("friction_scope") == "category_exploration"]
    ambiguous_rows = [r for r in rows if r.get("friction_scope") == "ambiguous"]
    none_rows = [r for r in rows if r.get("friction_scope") in (None, "none")]
    print(f"friction_scope split: generic_ops={len(ops_rows)}, "
          f"category_exploration={len(exploration_rows)}, ambiguous={len(ambiguous_rows)}, "
          f"none={len(none_rows)} (sums to {len(ops_rows)+len(exploration_rows)+len(ambiguous_rows)+len(none_rows)} of {n})")

    tables = {"meta": {"n_tagged_and_on_topic": n, "source_split": dict(by_source)}}

    tables["ops_friction_context_only"] = {
        "n": len(ops_rows),
        "top_friction_types": counter_table(ops_rows, "friction_type")[:15],
    }

    tables["category_exploration_primary"] = {
        "n": len(exploration_rows),
        "top_friction_types": counter_table(exploration_rows, "friction_type"),
        "categories_involved": counter_table(exploration_rows, "category_mentioned"),
    }

    cat_friction = defaultdict(Counter)
    for r in exploration_rows:
        for cat in (r.get("category_mentioned") or ["not_category_specific"]):
            for ft in (r.get("friction_type") or ["none"]):
                cat_friction[cat][ft] += 1
    tables["category_x_friction_exploration"] = {
        cat: dict(counter.most_common()) for cat, counter in cat_friction.items()
    }

    tables["behavior_signal_breakdown"] = dict(counter_table(rows, "behavior_signal"))
    tables["sentiment_breakdown"] = dict(Counter(r.get("sentiment") for r in rows).most_common())
    tables["category_mentioned_overall"] = dict(counter_table(rows, "category_mentioned"))

    stated_avoidance = [r for r in rows if "stated_avoidance" in (r.get("behavior_signal") or [])]
    tables["stated_avoidance_leads"] = {
        "n": len(stated_avoidance),
        "categories": counter_table(stated_avoidance, "category_mentioned"),
        "note": "Leads, not a measured avoidance rate - see DOCS/03_THOUGHT_PROCESS.md §6",
    }

    segment_cuts = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        band = rating_band(r.get("rating"))
        for signal in (r.get("behavior_signal") or []):
            segment_cuts[band][r["source"]][signal] += 1
    tables["segment_x_behavior"] = {
        band: {src: dict(c.most_common()) for src, c in sources.items()}
        for band, sources in segment_cuts.items()
    }

    # Threshold basis: % of records that could carry friction at all (friction_scope != none),
    # not % of the full tagged set - trivial/insufficient auto-tags are always friction_scope
    # "none" by construction, so including them in the denominator dilutes real signal (this
    # became visible once auto-tagging started covering ~half the corpus with zero-friction
    # placeholders - see DOCS/03_THOUGHT_PROCESS.md decisions table).
    n_with_friction = len(ops_rows) + len(exploration_rows) + len(ambiguous_rows)
    freq_threshold = max(15, round(0.01 * n_with_friction))
    tables["meta"]["frequency_threshold_used"] = freq_threshold
    tables["meta"]["frequency_threshold_basis_n"] = n_with_friction
    confirmed_exploration_themes = [
        (ft, count) for ft, count in tables["category_exploration_primary"]["top_friction_types"]
        if count >= freq_threshold
    ]
    weak_exploration_themes = [
        (ft, count) for ft, count in tables["category_exploration_primary"]["top_friction_types"]
        if count < freq_threshold
    ]
    tables["exploration_themes_above_threshold"] = confirmed_exploration_themes
    tables["exploration_themes_below_threshold_weak"] = weak_exploration_themes

    out_path = f"{PROCESSED_DIR}/pattern_tables.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nWrote pattern tables to {out_path}")

    exported = dump_app_export(rows)
    print(f"Refreshed data/processed/app_export.jsonl ({exported} rows) - what the deployed app reads")
    print(f"Frequency threshold used: >= {freq_threshold} mentions to count as a confirmed theme "
          f"(max(15, 1% of {n_with_friction} friction-bearing records))")
    print(f"Category-exploration themes above threshold: {len(confirmed_exploration_themes)}")
    print(f"Stated-avoidance leads found: {len(stated_avoidance)}")


if __name__ == "__main__":
    main()
