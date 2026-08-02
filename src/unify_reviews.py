"""
Phase 1 - D1 deliverable: unify all per-source raw scrapes into one schema-consistent
dataset (data/raw/unified_reviews.jsonl), with a dedupe pass and the Phase 1 edge-case
checks from DOCS/05_EDGE_CASES_AND_TESTING.md run against the result.

This does NOT clean/filter content (that's Phase 2, DOCS/01_PLAN.md). It only unifies
schema and removes true duplicates - the "gather at scale" step, not "structure with AI".
"""
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, read_jsonl, write_jsonl  # noqa: E402

INPUTS = [
    ("play_store", "playstore_raw.jsonl"),
    ("app_store", "appstore_raw.jsonl"),
    ("reddit_post", "reddit_posts_raw.jsonl"),
    ("reddit_comment", "reddit_comments_raw.jsonl"),
]


def load_all():
    records = []
    counts = {}
    for label, fname in INPUTS:
        path = f"{RAW_DIR}/{fname}"
        if not os.path.exists(path):
            print(f"WARNING: {path} not found, skipping ({label})")
            counts[label] = 0
            continue
        rows = read_jsonl(path)
        counts[label] = len(rows)
        records.extend(rows)
    return records, counts


def dedupe(records):
    seen_keys = set()
    unique = []
    dropped_exact_id = 0
    for r in records:
        key = (r["source"], r["record_id"])
        if key in seen_keys:
            dropped_exact_id += 1
            continue
        seen_keys.add(key)
        unique.append(r)
    return unique, dropped_exact_id


def run_edge_case_checks(records):
    print("\n=== Phase 1 edge-case checks (DOCS/05_EDGE_CASES_AND_TESTING.md) ===")
    results = {}

    # unique record_id count == row count, per source
    by_source = defaultdict(list)
    for r in records:
        by_source[r["source"]].append(r)
    for source, rows in by_source.items():
        ids = [r["record_id"] for r in rows]
        dup = len(ids) - len(set(ids))
        status = "PASS" if dup == 0 else f"FAIL ({dup} duplicate ids)"
        print(f"[dedupe integrity] {source}: {len(rows)} rows, {len(set(ids))} unique ids -> {status}")
        results[f"dedupe_integrity_{source}"] = status

    # empty/null text handling
    empty_text = [r for r in records if not r.get("text") or not str(r.get("text")).strip()]
    print(f"[empty text] {len(empty_text)} / {len(records)} records have empty/null text "
          f"(expected for e.g. rating-only Play Store reviews) -> logged, not dropped")
    results["empty_text_count"] = len(empty_text)

    # date sanity - Zepto launched 2021; flag anything earlier
    bad_dates = []
    for r in records:
        d = r.get("date")
        if d and isinstance(d, str) and len(d) >= 4:
            try:
                year = int(d[:4])
                if year < 2021 or year > 2026:
                    bad_dates.append((r["source"], r["record_id"], d))
            except ValueError:
                bad_dates.append((r["source"], r["record_id"], d))
    status = "PASS" if not bad_dates else f"FAIL ({len(bad_dates)} out-of-range dates)"
    print(f"[date sanity] out-of-[2021,2026] or unparseable dates -> {status}")
    if bad_dates:
        for b in bad_dates[:10]:
            print(f"    {b}")
    results["date_sanity"] = status

    # cross-source exact-text duplicates (would indicate a scraping bug, not expected legitimately)
    text_to_sources = defaultdict(set)
    for r in records:
        t = (r.get("text") or "").strip()
        if len(t) > 40:  # ignore short/empty text, too likely to coincidentally match
            text_to_sources[t].add(r["source"])
    cross_source_dupes = {t: s for t, s in text_to_sources.items() if len(s) > 1}
    print(f"[cross-source exact-text duplicates] {len(cross_source_dupes)} found "
          f"-> {'PASS (none)' if not cross_source_dupes else 'REVIEW'}")
    results["cross_source_text_dupes"] = len(cross_source_dupes)

    # source volume summary
    print("\n[source volume]")
    for source, rows in by_source.items():
        print(f"  {source}: {len(rows)}")
    results["volume_by_source"] = {s: len(r) for s, r in by_source.items()}

    return results


def main():
    records, per_file_counts = load_all()
    print("Loaded raw counts:", per_file_counts)
    print(f"Total rows before dedupe: {len(records)}")

    unique, dropped = dedupe(records)
    print(f"Dropped {dropped} exact (source, record_id) duplicates")
    print(f"Total unique records: {len(unique)}")

    check_results = run_edge_case_checks(unique)

    out_path = f"{RAW_DIR}/unified_reviews.jsonl"
    write_jsonl(out_path, unique)
    print(f"\nWrote {len(unique)} unified records to {out_path}")

    summary_path = f"{RAW_DIR}/phase1_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "per_file_raw_counts": per_file_counts,
            "total_unique_after_dedupe": len(unique),
            "edge_case_checks": check_results,
        }, f, indent=2, default=str)
    print(f"Wrote Phase 1 summary to {summary_path}")


if __name__ == "__main__":
    main()
