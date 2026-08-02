"""
Phase 1 - Reddit scraper for Zepto.

No official Reddit API credentials available (would require registering an app under
someone's Reddit account - see .env.example if that becomes available later and this
should be swapped for PRAW). Reddit's public `.json` endpoints return a bot-check 403
for unauthenticated requests as of this run, but the plain HTML pages (old.reddit.com)
serve normally, so this scrapes and parses HTML instead - documented here because it's
a real, load-bearing implementation detail, not an incidental choice.

Two passes:
1. Site-wide + subreddit-scoped search for "zepto", multiple sort orders, paginated via
   old.reddit's `after` token until a stream goes stale (no volume cap imposed).
2. For every matched post, fetch the full comments page and pull in top-level comments
   too (a post titled generically, e.g. a quick-commerce comparison thread, often has
   individual comments that are the actually-relevant Zepto content).
"""
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, __file__.rsplit("/", 2)[0] + "/src")
from common import RAW_DIR, make_record, write_jsonl  # noqa: E402

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
BASE = "https://old.reddit.com"
QUERY = "zepto"
SLEEP_SECONDS = 1.0
MAX_PAGES_PER_STREAM = 200  # safety valve, not a target
STALE_WINDOW = 4
STALE_NEW_RATE = 0.05

SUBREDDITS = [
    None,  # site-wide
    "india", "bangalore", "developersIndia", "IndianStreetBets", "IndiaInvestments",
    "StartUpIndia", "indianbusiness", "mumbai", "delhi", "IndiaSpeaks",
]
SORTS = ["new", "relevance", "top"]

seen_posts = {}  # fullname -> post dict
seen_post_records = {}
seen_comment_ids = set()
comment_records = []


def get(url, params=None, tries=3):
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
            print(f"    HTTP {r.status_code} for {r.url}", flush=True)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            return None
        except requests.RequestException as e:
            print(f"    request error: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    return None


def parse_search_results(html):
    soup = BeautifulSoup(html, "lxml")
    results = []
    for div in soup.select("div.search-result-link"):
        fullname = div.get("data-fullname")
        title_a = div.select_one("a.search-title")
        time_tag = div.select_one("span.search-time time")
        author_a = div.select_one("a.author")
        subreddit_a = div.select_one("a.search-subreddit-link")
        score_span = div.select_one("span.search-score")
        num_comments_a = div.select_one("a.search-comments")
        if not (fullname and title_a):
            continue
        score = None
        if score_span:
            m = re.search(r"-?\d+", score_span.get_text())
            if m:
                score = int(m.group())
        results.append({
            "fullname": fullname,
            "title": title_a.get_text(strip=True),
            "url": title_a.get("href"),
            "date": time_tag.get("datetime") if time_tag else None,
            "author": author_a.get_text(strip=True) if author_a else None,
            "subreddit": subreddit_a.get_text(strip=True) if subreddit_a else None,
            "score": score,
            "num_comments": (
                int(re.search(r"\d+", num_comments_a.get_text()).group())
                if num_comments_a and re.search(r"\d+", num_comments_a.get_text())
                else None
            ),
        })
    next_after = None
    for a in soup.select("a"):
        href = a.get("href", "")
        if "after=t3_" in href or ("after=t1_" in href and "type=comment" in href):
            next_after = href
    return results, next_after


def search_stream(subreddit, sort, log_prefix):
    new_count = 0
    new_rate_window = []
    page = 0
    after_url = None

    while page < MAX_PAGES_PER_STREAM:
        page += 1
        if after_url:
            r = get(after_url)
        else:
            path = f"{BASE}/r/{subreddit}/search" if subreddit else f"{BASE}/search"
            params = {"q": QUERY, "sort": sort, "limit": 25}
            if subreddit:
                params["restrict_sr"] = "on"
            r = get(path, params=params)

        if r is None:
            print(f"  [{log_prefix}] page {page}: no response, stopping", flush=True)
            break

        results, next_after = parse_search_results(r.text)
        if not results:
            print(f"  [{log_prefix}] page {page}: 0 results, stopping", flush=True)
            break

        new_in_page = 0
        for res in results:
            if res["fullname"] not in seen_posts:
                seen_posts[res["fullname"]] = res
                new_in_page += 1
        new_count += new_in_page
        new_rate_window.append(new_in_page / len(results))
        if len(new_rate_window) > STALE_WINDOW:
            new_rate_window.pop(0)

        print(
            f"  [{log_prefix}] page {page}: results={len(results)} new={new_in_page} "
            f"(stream_new={new_count}, total_unique_posts={len(seen_posts)})",
            flush=True,
        )

        if not next_after:
            print(f"  [{log_prefix}] page {page}: no next page, stream exhausted", flush=True)
            break
        if len(new_rate_window) == STALE_WINDOW and (sum(new_rate_window) / STALE_WINDOW) < STALE_NEW_RATE:
            print(f"  [{log_prefix}] page {page}: stale, moving to next stream", flush=True)
            break

        after_url = next_after
        time.sleep(SLEEP_SECONDS)

    return new_count


def fetch_post_and_comments(post):
    url = post["url"]
    if not url:
        return
    if not url.startswith("http"):
        url = BASE + url
    r = get(url)
    if r is None:
        return
    soup = BeautifulSoup(r.text, "lxml")

    link_thing = soup.select_one('div.thing[data-type="link"]')
    selftext = None
    if link_thing:
        body = link_thing.select_one("div.usertext-body")
        if body:
            selftext = body.get_text("\n", strip=True)
        score_attr = link_thing.get("data-score")
        if score_attr and score_attr.lstrip("-").isdigit():
            post["score"] = int(score_attr)

    fullname = post["fullname"]
    if fullname not in seen_post_records:
        seen_post_records[fullname] = make_record(
            source="reddit",
            record_id=fullname,
            date=post.get("date"),
            rating=None,
            text=selftext,
            title=post.get("title"),
            platform=None,
            locale="in",
            helpful_count=post.get("score"),
            url=url,
            extra={
                "post_type": "submission",
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "num_comments": post.get("num_comments"),
            },
        )

    for c in soup.select("div.comment"):
        cid = c.get("data-fullname")
        author = c.get("data-author")
        if not cid or cid in seen_comment_ids or author == "AutoModerator":
            continue
        body_el = c.select_one("div.usertext-body")
        if not body_el:
            continue
        text = body_el.get_text("\n", strip=True)
        if len(text) < 3 or text in ("[deleted]", "[removed]"):
            continue
        seen_comment_ids.add(cid)
        score_attr = c.get("data-score")
        score = int(score_attr) if score_attr and score_attr.lstrip("-").isdigit() else None
        time_tag = c.select_one("time")
        comment_records.append(make_record(
            source="reddit",
            record_id=cid,
            date=time_tag.get("datetime") if time_tag else post.get("date"),
            rating=None,
            text=text,
            title=None,
            platform=None,
            locale="in",
            helpful_count=score,
            url=url + cid.split("_")[-1],
            extra={
                "post_type": "comment",
                "subreddit": post.get("subreddit"),
                "author": author,
                "parent_post_fullname": fullname,
                "parent_post_title": post.get("title"),
            },
        ))


def main():
    posts_path = f"{RAW_DIR}/reddit_posts_raw.jsonl"
    comments_path = f"{RAW_DIR}/reddit_comments_raw.jsonl"

    print("=== Phase A: search sweep ===", flush=True)
    for subreddit in SUBREDDITS:
        for sort in SORTS:
            label = f"r/{subreddit or 'ALL'} sort={sort}"
            print(f"Searching {label} ...", flush=True)
            search_stream(subreddit, sort, label)
            time.sleep(SLEEP_SECONDS)

    print(f"\nTotal unique posts found: {len(seen_posts)}", flush=True)

    print("=== Phase B: fetch each post + its comments ===", flush=True)
    for i, post in enumerate(seen_posts.values(), 1):
        fetch_post_and_comments(post)
        if i % 20 == 0:
            print(f"  fetched {i}/{len(seen_posts)} posts, comments so far={len(comment_records)}", flush=True)
            write_jsonl(posts_path, list(seen_post_records.values()))
            write_jsonl(comments_path, comment_records)
        time.sleep(SLEEP_SECONDS)

    write_jsonl(posts_path, list(seen_post_records.values()))
    write_jsonl(comments_path, comment_records)
    print(f"\nFINAL: {len(seen_post_records)} posts, {len(comment_records)} comments", flush=True)
    print(f"Wrote {posts_path} and {comments_path}", flush=True)


if __name__ == "__main__":
    main()
