"""
Phase 1 - App Store scraper for Zepto (id1575323645), via the iTunes RSS customer-reviews feed.

Correction (see DOCS/00b_REVIEW_NOTES_ROUND2.md): an earlier test of this exact endpoint during
this project returned zero entries for every app tried (Zepto AND Instagram), which was
documented as "Apple has deprecated this public feed." That was wrong - re-testing later in the
same session, the endpoint returned real data again for both apps. The likely explanation is a
transient outage/caching blip on Apple's side at the time of the first test, not a dead feed.
Corrected across all docs. Lesson: a single failed probe against a third-party endpoint (even
tested against a second app) isn't enough to conclude "permanently unavailable" - worth a retest
before writing that off as a platform constraint.

Known real limitation: this feed is capped at 10 pages x 50 reviews = 500, and only surfaces
recent reviews (not the full historical set) - that part of the original Phase 1 edge-case
expectation was correct, just not "zero."
"""
import sys
import time

import requests

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, make_record, write_jsonl  # noqa: E402

APP_ID = "1575323645"
COUNTRY = "in"
MAX_PAGES = 10
SLEEP_SECONDS = 1.0
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_page(page, tries=3):
    url = f"https://itunes.apple.com/{COUNTRY}/rss/customerreviews/page={page}/id={APP_ID}/sortby=mostrecent/json"
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json().get("feed", {}).get("entry", [])
            print(f"  page {page}: HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  page {page}: request error {e}")
        time.sleep(2 * (attempt + 1))
    return []


def main():
    all_entries = []
    seen_ids = set()
    for page in range(1, MAX_PAGES + 1):
        entries = fetch_page(page)
        new = 0
        for e in entries:
            eid = e.get("id", {}).get("label")
            if not eid or eid in seen_ids:
                continue
            seen_ids.add(eid)
            all_entries.append(e)
            new += 1
        print(f"page {page}: {len(entries)} entries, {new} new (total {len(all_entries)})")
        time.sleep(SLEEP_SECONDS)

    records = []
    for e in all_entries:
        eid = e.get("id", {}).get("label")
        records.append(make_record(
            source="app_store",
            record_id=eid,
            date=e.get("updated", {}).get("label"),
            rating=int(e["im:rating"]["label"]) if e.get("im:rating") else None,
            text=e.get("content", {}).get("label"),
            title=e.get("title", {}).get("label"),
            platform="ios",
            locale=COUNTRY,
            helpful_count=int(e["im:voteSum"]["label"]) if e.get("im:voteSum") else None,
            url=e.get("link", {}).get("attributes", {}).get("href"),
            extra={
                "app_version": e.get("im:version", {}).get("label"),
                "user_name": e.get("author", {}).get("name", {}).get("label"),
            },
        ))

    out_path = f"{RAW_DIR}/appstore_raw.jsonl"
    write_jsonl(out_path, records)
    print(f"\nWrote {len(records)} App Store records to {out_path}")


if __name__ == "__main__":
    main()
