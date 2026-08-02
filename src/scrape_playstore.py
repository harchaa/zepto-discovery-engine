"""
Phase 1 - Play Store scraper for Zepto (com.zeptoconsumerapp).

No volumetric cap by design: we don't stop at a target count. Instead each pagination
stream (a sort order x star-rating filter) runs until it stops surfacing NEW reviews -
that's a principled stopping rule based on information content, not an arbitrary count.
Sweeping multiple sort orders x score filters gets around the fact that a single
pagination stream's continuation token eventually plateaus (keeps returning reviews
we've already seen) well before the app's total review count is reached.

Writes incrementally after every stream so a kill/crash never loses progress.
"""
import sys
import time

from google_play_scraper import Sort, reviews

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, make_record, write_jsonl  # noqa: E402

APP_ID = "com.zeptoconsumerapp"
COUNTRY = "in"
LANG = "en"
PAGE_SIZE = 200
SLEEP_SECONDS = 0.15
MAX_PAGES_PER_STREAM = 3000  # safety valve against a runaway loop, not a target
STALE_WINDOW = 8             # look at the last N pages of a stream
STALE_NEW_RATE = 0.03        # stop the stream if <3% of the last N pages' rows were new

seen_ids = set()
all_records = []


def to_record(r):
    rid = r["reviewId"]
    return rid, make_record(
        source="play_store",
        record_id=rid,
        date=str(r.get("at")) if r.get("at") else None,
        rating=r.get("score"),
        text=r.get("content"),
        title=None,
        platform="android",
        locale=COUNTRY,
        helpful_count=r.get("thumbsUpCount"),
        url=f"https://play.google.com/store/apps/details?id={APP_ID}&reviewId={rid}",
        extra={
            "app_version": r.get("appVersion") or r.get("reviewCreatedVersion"),
            "user_name": r.get("userName"),
            "reply_content": r.get("replyContent"),
        },
    )


def fetch_stream(sort, score, log_prefix):
    token = None
    page = 0
    new_rate_window = []
    stream_new_count = 0

    while page < MAX_PAGES_PER_STREAM:
        page += 1
        try:
            batch, token = reviews(
                APP_ID, lang=LANG, country=COUNTRY, sort=sort,
                count=PAGE_SIZE, filter_score_with=score, continuation_token=token,
            )
        except Exception as e:
            print(f"  [{log_prefix}] page {page}: request error ({e}), stopping stream", flush=True)
            break

        if not batch:
            print(f"  [{log_prefix}] page {page}: 0 reviews returned, stopping stream", flush=True)
            break

        new_in_page = 0
        for r in batch:
            rid, rec = to_record(r)
            if rid not in seen_ids:
                seen_ids.add(rid)
                all_records.append(rec)
                new_in_page += 1
        stream_new_count += new_in_page

        new_rate_window.append(new_in_page / len(batch))
        if len(new_rate_window) > STALE_WINDOW:
            new_rate_window.pop(0)

        if page % 10 == 0 or new_in_page == 0:
            print(
                f"  [{log_prefix}] page {page}: batch={len(batch)} new={new_in_page} "
                f"(stream_new={stream_new_count}, total_unique={len(seen_ids)})",
                flush=True,
            )

        if token is None:
            print(f"  [{log_prefix}] page {page}: no continuation token, stream exhausted", flush=True)
            break

        if len(new_rate_window) == STALE_WINDOW and (sum(new_rate_window) / STALE_WINDOW) < STALE_NEW_RATE:
            print(
                f"  [{log_prefix}] page {page}: stale (last {STALE_WINDOW} pages <{STALE_NEW_RATE:.0%} new), "
                f"moving to next stream",
                flush=True,
            )
            break

        time.sleep(SLEEP_SECONDS)

    return stream_new_count


def main():
    sorts = [("NEWEST", Sort.NEWEST), ("MOST_RELEVANT", Sort.MOST_RELEVANT), ("RATING", Sort.RATING)]
    scores = [None, 1, 2, 3, 4, 5]

    out_path = f"{RAW_DIR}/playstore_raw.jsonl"

    for sort_name, sort_val in sorts:
        for score in scores:
            label = f"sort={sort_name} score={score}"
            print(f"Fetching {label} ... (unique so far: {len(seen_ids)})", flush=True)
            new_count = fetch_stream(sort_val, score, label)
            print(f"  [{label}] contributed {new_count} new unique reviews", flush=True)
            write_jsonl(out_path, all_records)  # checkpoint after every stream

    print(f"\nFINAL total unique Play Store reviews: {len(all_records)}", flush=True)
    write_jsonl(out_path, all_records)
    print(f"Wrote {len(all_records)} records to {out_path}", flush=True)


if __name__ == "__main__":
    main()
