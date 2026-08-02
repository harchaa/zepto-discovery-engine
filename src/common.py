"""Shared helpers for the Phase 1 scrapers: a common record schema and JSONL I/O."""
import json
import os

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")


def make_record(source, record_id, date, rating, text, title, platform, locale, helpful_count, url, extra=None):
    """Common schema per DOCS/01_PLAN.md Phase 1 'Fields captured per record'."""
    rec = {
        "source": source,          # play_store | app_store | reddit
        "record_id": record_id,    # stable id from the source
        "date": date,              # ISO 8601 string, or None if unknown
        "rating": rating,          # 1-5 int, or None (e.g. Reddit posts have no rating)
        "text": text,              # review/post/comment body, or None
        "title": title,            # review title / post title, or None
        "platform": platform,      # android | ios | web (Reddit -> None)
        "locale": locale,          # country code used for the fetch, e.g. "in"
        "helpful_count": helpful_count,  # thumbs-up / upvotes, or None
        "url": url,
    }
    if extra:
        rec.update(extra)
    return rec


def write_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


PROCESSED_DIR = RAW_DIR.replace("/raw", "/processed")

# friction_type canonicalization, built from the actual variant labels observed in tagged
# output (the LLM invents free-form snake_case tags by design - see 04_TAXONOMY_DRAFT_v0.md -
# so near-duplicates like delivery/delivery_issue/delivery_experience accumulate). Collapsed here,
# once, at the single point every downstream consumer reads through (load_joined_tagged), rather
# than in each of analyze_patterns.py / insights.py / the chatbot separately. Raw tags in
# tagged_reviews.jsonl are left untouched (audit trail); this only affects what analysis sees.
FRICTION_TYPE_CANONICAL = {
    "refund": "no_easy_refund", "refund_process": "no_easy_refund", "no_refund": "no_easy_refund",
    "refund_policy": "no_easy_refund", "refund_issue": "no_easy_refund",
    "no_replacement_policy": "no_easy_refund", "return_policy": "no_easy_refund",
    "refund_return_policy": "no_easy_refund", "cash_refund": "no_easy_refund",
    "exchange_policy": "no_easy_refund", "voucher_issue": "no_easy_refund",
    "delivery": "delivery_reliability", "delivery_issue": "delivery_reliability",
    "delivery_issues": "delivery_reliability", "delivery_experience": "delivery_reliability",
    "delivery_process": "delivery_reliability", "delivery_area": "delivery_reliability",
    "delivery_access": "delivery_reliability", "delivery_boys": "delivery_reliability",
    "delivery_option": "delivery_reliability", "delivery_delay": "delivery_reliability",
    "delivery_rider_behaviour": "delivery_reliability", "delivery_refund": "delivery_reliability",
    "delivery/refund": "delivery_reliability", "delivery_partner_behavior": "delivery_reliability",
    "delivery_behavior": "delivery_reliability", "delivery_service": "delivery_reliability",
    "delivery_time_issue": "delivery_reliability", "no_service_partner": "delivery_reliability",
    "serviceability": "delivery_reliability", "limited_pincodes": "delivery_reliability",
    "delivery_charges": "pricing_value", "delivery_charge": "pricing_value",
    "extra_charges": "pricing_value", "unethical_pricing": "pricing_value",
    "discounts": "pricing_value", "offers": "pricing_value", "price_sensitive_language": "pricing_value",
    "app_bug": "app_ux_bug", "account_issue": "app_ux_bug", "notification_strategy": "app_ux_bug",
    "notifications": "app_ux_bug", "map_facility": "app_ux_bug",
    "product_quality": "quality_perishables", "quality": "quality_perishables",
    "spoiled_product": "quality_perishables", "quality_products": "quality_perishables",
    "packaging": "damaged_in_transit", "damaged_product": "damaged_in_transit",
    "quality_authenticity": "product_authenticity",
    "quality_authenticity_unfamiliar_category": "quality_uncertainty_unfamiliar_category",
    "no_customer_support": "customer_support", "bad_service": "customer_support",
    "service_not_available": "customer_support",
    "payment_issues": "payment_discount_glitch", "payment_issue": "payment_discount_glitch",
    "payment": "payment_discount_glitch", "payment_options": "payment_discount_glitch",
    "payment_process": "payment_discount_glitch", "payment_method": "payment_discount_glitch",
    "wallet_issue": "payment_discount_glitch", "cash_on_delivery": "payment_discount_glitch",
    "no_cod": "payment_discount_glitch", "payment_processing": "payment_discount_glitch",
    "banking_system": "payment_discount_glitch",
    "trust_issues": "trust_vs_specialist_retailer", "comparison_to_competitor": "trust_vs_specialist_retailer",
    "scam": "trust_vs_specialist_retailer", "fraud": "trust_vs_specialist_retailer",
    "availability": "product_availability", "out_of_stock": "product_availability",
    "product_unavailability": "product_availability", "stock_availability": "product_availability",
    "stock_out": "product_availability",
    "cancel_option": "order_cancellation", "no_cancel_option": "order_cancellation",
    "cancelled": "order_cancellation",
    "missing_item": "missing_items",
    "price": "pricing_value", "delivery_fee": "pricing_value", "delivery_cost": "pricing_value",
    "handling_charges": "pricing_value", "unnecessary_charges": "pricing_value",
    "fulfilment_fees": "pricing_value", "overpriced": "pricing_value",
    "pricing_issue": "pricing_value", "pricing": "pricing_value",
    "late_delivery": "delivery_reliability", "delivery_time": "delivery_reliability",
    "delivery_location": "delivery_reliability", "delivery_location_accuracy": "delivery_reliability",
    "no_serviceable_location": "delivery_reliability", "service_unavailability": "delivery_reliability",
    "site_down": "delivery_reliability", "high_demand": "delivery_reliability",
    "login_issue": "app_ux_bug", "search_results": "app_ux_bug", "inconvenient_ordering": "app_ux_bug",
    "refund_time": "no_easy_refund", "wallet_refund": "no_easy_refund",
    "no_order_cancellation": "order_cancellation",
    "wrong_item": "wrong_item_delivered", "wrong_items": "wrong_item_delivered",
    "duplicate_items": "wrong_item_delivered",
    "packaging_quality": "damaged_in_transit",
}


def canonicalize_friction_types(tags):
    if not tags:
        return tags
    seen = []
    for t in tags:
        canon = FRICTION_TYPE_CANONICAL.get(t, t)
        if canon not in seen:
            seen.append(canon)
    return seen


def load_joined_tagged():
    """Tagged records joined back to their cleaned-corpus metadata (source, date, rating, text).
    Shared by Phase 3 analysis, embeddings build, and the Streamlit app - single source of truth
    for what counts as "the analyzable corpus" (tagged + on-topic).
    """
    tagged_path = f"{PROCESSED_DIR}/tagged_reviews.jsonl"
    cleaned_path = f"{PROCESSED_DIR}/cleaned_reviews.jsonl"
    if not (os.path.exists(tagged_path) and os.path.exists(cleaned_path)):
        return []
    tagged = read_jsonl(tagged_path)
    cleaned = {r["record_id"]: r for r in read_jsonl(cleaned_path)}
    joined = []
    for t in tagged:
        c = cleaned.get(t["id"])
        if c is None or c.get("off_topic_flag"):
            continue
        row = dict(c)
        row.update(t)
        row["friction_type"] = canonicalize_friction_types(row.get("friction_type"))
        joined.append(row)
    return joined


APP_EXPORT_FIELDS = [
    "source", "record_id", "date", "rating", "text", "title", "category_mentioned", "sentiment",
    "friction_scope", "friction_type", "behavior_signal", "segment_hint",
    "auto_tagged_trivial", "auto_tagged_insufficient_text",  # build_embeddings.py filters on these
]
APP_EXPORT_TEXT_MAX_LEN = 800  # dashboard/chatbot quotes never show more than a few hundred chars


def dump_app_export(rows=None):
    """Write the joined (tagged + on-topic) rows to a small standalone export file.
    The full cleaned_reviews.jsonl is 60MB+ (the whole gathered corpus) and only needed by the
    pipeline scripts (tagging, embedding) - the deployed app only ever needs the much smaller
    tagged subset, so it reads this export instead of recomputing the join from the giant file.
    Keeps the deployed repo small and the app's startup fast regardless of corpus size.

    Trimmed to just the fields the app actually reads (dropping url/reply_content/user_name/
    app_version/locale/helpful_count/platform/language/insufficient_text/off_topic_flag, none of
    which the dashboard or chatbot ever displays) and truncates text - this cut the export from
    ~51MB to a fraction of that at ~69k rows, which matters because GitHub warns above 50MB per
    file and hard-blocks at 100MB, and this file was on a growth trajectory toward that limit.
    """
    rows = rows if rows is not None else load_joined_tagged()
    trimmed = []
    for r in rows:
        row = {k: r.get(k) for k in APP_EXPORT_FIELDS}
        if row.get("text"):
            row["text"] = row["text"][:APP_EXPORT_TEXT_MAX_LEN]
        trimmed.append(row)
    write_jsonl(f"{PROCESSED_DIR}/app_export.jsonl", trimmed)
    return len(trimmed)


def find_quotes(rows, predicate, limit=4):
    """Pick up to `limit` real verbatim quotes (text, source, date) matching predicate."""
    out = []
    for r in rows:
        if not predicate(r):
            continue
        text = (r.get("text") or "").strip()
        if len(text) < 15:
            continue
        out.append({
            "text": text[:400],
            "source": r["source"],
            "date": (r.get("date") or "")[:10],
            "rating": r.get("rating"),
        })
        if len(out) >= limit:
            break
    return out
