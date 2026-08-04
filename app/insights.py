"""
Deterministic, data-driven insight synthesis for the 8 research questions.

No LLM call here on purpose: every number is a direct count from the tagged corpus
(Counter over real tags), so there's zero fabrication risk. Each RQ function returns a
structured dict (headline, small chart data, narrative, quotes) that the dashboard
renders as one tab per question - not a text blob. Falls back to an honest "not enough
evidence yet" note below a minimum sample size rather than overreaching on a handful of
records.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from common import find_quotes  # noqa: E402

MIN_N_FOR_INSIGHT = 8
NEW_ADJACENT_CATEGORIES = {
    "personal_care", "beauty", "baby_care", "pet_care", "pharmacy_health", "electronics", "apparel",
}


def _counts(rows, field, exclude=()):
    c = Counter()
    for r in rows:
        for v in (r.get(field) or []):
            if v not in exclude and v is not None:
                c[v] += 1
    return c.most_common()


def _pct(n, total):
    return round(n / total * 100, 1) if total else 0.0


def _fmt_tag(tag):
    return (tag or "").replace("_", " ")


def _quotes(matches, limit=3):
    return find_quotes(matches, lambda r: True, limit=limit)


def rq1_habit(rows, matches):
    n, total = len(matches), len(rows)
    cats = _counts(matches, "category_mentioned", exclude=("not_category_specific",))
    top = cats[0] if cats else None
    narrative = (
        f"Habit / mission-mode dominates: {n} reviews ({_pct(n, total)}%) use repeat-purchase "
        f"language" + (f", concentrated on **{_fmt_tag(top[0])}**" if top else "") + ". Staple "
        "categories are the default, low-effort purchase — consistent with the company goal "
        "problem statement (most users rarely cross into new categories)."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "Why do users repeatedly buy from the same categories?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{n} reviews ({_pct(n, total)}%)",
        "headline_label": "show habit / repeat-purchase language",
        "chart_pairs": cats[:8], "chart_title": "Categories mentioned in habit-language reviews",
        "narrative": narrative, "quotes": _quotes(matches),
    }


def rq2_exploration_blockers(rows, matches):
    n, total = len(matches), len(rows)
    frictions = _counts(matches, "friction_type")
    lead = ", ".join(f"**{_fmt_tag(f)}** ({c})" for f, c in frictions[:3])
    narrative = (
        f"Where users DO try a new category, the friction is trust / quality-uncertainty / "
        f"authenticity, not generic complaints: {lead}. This is the direct evidence for what "
        f"blocks exploration — deliberately excludes generic ops complaints (delivery, refunds, "
        f"routine produce quality) even on non-staple items, which are tagged separately as "
        f"background context, not exploration friction."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "What prevents users from exploring new categories?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{n} reviews ({_pct(n, total)}%)",
        "headline_label": "show category-exploration friction (trust/authenticity/info-gap on a new category)",
        "chart_pairs": frictions, "chart_title": "Category-exploration friction types",
        "narrative": narrative, "quotes": _quotes(matches),
    }


def rq3_discovery(rows, matches):
    n, total = len(matches), len(rows)
    narrative = (
        f"{n} reviews ({_pct(n, total)}%) explicitly mention how they discovered a product or "
        f"offer. Thin by nature — reviews are written after a purchase decision, not during "
        f"discovery — so treat this as directional, not a measured discovery-channel mix."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "How do users discover products today?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{n} reviews ({_pct(n, total)}%)",
        "headline_label": "mention a discovery channel",
        "chart_pairs": _counts(matches, "category_mentioned", exclude=("not_category_specific",))[:8],
        "chart_title": "Categories in discovery-mention reviews",
        "narrative": narrative, "quotes": _quotes(matches),
    }


def rq4_habit_role(rows, matches):
    n, total = len(matches), len(rows)
    pos = sum(1 for r in matches if r.get("sentiment") == "positive")
    narrative = (
        f"{n} reviews ({_pct(n, total)}%) reference habitual/repeat behavior; **{pos}/{n}** "
        f"({_pct(pos, n) if n else 0}%) are positive-sentiment — habit here reads mostly as "
        f"satisfied loyalty to staple categories, not friction-driven lock-in. Habit is the "
        f"default; exploration is the exception that needs a specific trigger."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "What role do habits play in shopping behavior?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{pos}/{n}" if n else "0/0",
        "headline_label": "habit-language reviews are positive-sentiment",
        "chart_pairs": _counts(matches, "sentiment" if False else "category_mentioned", exclude=("not_category_specific",))[:8],
        "chart_title": "Categories in habit-language reviews",
        "narrative": narrative, "quotes": _quotes(matches),
    }


def rq5_info_needed(rows, matches):
    n, total = len(matches), len(rows)
    types = _counts(matches, "friction_type")
    lead = ", ".join(f"**{_fmt_tag(f)}** ({c})" for f, c in types[:3])
    narrative = (
        f"{n} reviews ({_pct(n, total)}%) point to specific information gaps before trying a new "
        f"category: {lead}. This is the actionable list — what a category-exploration nudge "
        f"would need to address (authenticity proof, fit guidance, category-specific quality info)."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "What information do users need before trying a new category?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{n} reviews ({_pct(n, total)}%)",
        "headline_label": "cite a specific pre-purchase information gap",
        "chart_pairs": types, "chart_title": "Information-gap friction types",
        "narrative": narrative, "quotes": _quotes(matches),
    }


def rq6_frustrations(rows, matches):
    ops_n = sum(1 for r in matches if r.get("friction_scope") == "generic_ops")
    exp_n = sum(1 for r in matches if r.get("friction_scope") == "category_exploration")
    total = len(rows)
    narrative = (
        f"Of {len(matches)} reviews with friction ({_pct(len(matches), total)}%), **{ops_n}** are "
        f"generic ops complaints (delivery, refunds, app bugs, routine quality) vs. **{exp_n}** "
        f"category-exploration friction. Ops complaints dominate by sheer volume — expected for "
        f"a delivery app — which is exactly why the rest of this dashboard keeps them as "
        f"background context rather than the analytical lens."
    )
    return {
        "title": "What frustrations emerge repeatedly?",
        "n": len(matches), "pct": _pct(len(matches), total),
        "headline": f"{ops_n} ops vs. {exp_n} exploration",
        "headline_label": "friction records by scope",
        "chart_pairs": [("generic_ops (context)", ops_n), ("category_exploration (lens)", exp_n)],
        "chart_title": "Friction scope split",
        "narrative": narrative,
        "quotes": _quotes([r for r in matches if r.get("friction_scope") == "category_exploration"]),
    }


def rq7_segments(rows, matches):
    n, total = len(matches), len(rows)
    segs = _counts(matches, "segment_hint", exclude=("none",))
    seg_str = f", most often alongside **{_fmt_tag(segs[0][0])}** language" if segs else ""
    narrative = (
        f"{n} reviews ({_pct(n, total)}%) show a positive exploration attempt (tried something "
        f"new, went well){seg_str}. Small n — this is the research question most in need of Part "
        f"2 interviews to actually segment users, not just count reviews."
    ) if n >= MIN_N_FOR_INSIGHT else None
    return {
        "title": "Which user segments are more likely to experiment?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{n} reviews ({_pct(n, total)}%)",
        "headline_label": "show a positive exploration attempt",
        "chart_pairs": segs, "chart_title": "Segment language alongside positive exploration",
        "narrative": narrative, "quotes": _quotes(matches),
    }


# Opportunity score formula (fully deterministic, documented so it's never a mystery number):
#   opportunity = round(10 * (0.6 * relative_frequency + 0.4 * negative_share))
#   relative_frequency = this need's mention count / the most-mentioned need's count
#   negative_share      = fraction of this need's mentions that are negative-sentiment
# Frequency says how often it comes up; negative_share says how much it stings when it does.
NEED_LABELS = {
    "quality_uncertainty_unfamiliar_category": "Quality assurance for unfamiliar categories",
    "product_authenticity": "Verified-authentic product guarantees",
    "no_info_before_purchase": "Richer product info before first purchase",
    "sizing_fit_uncertainty": "Size/fit guidance",
    "trust_vs_specialist_retailer": "Trust-building vs. specialist retailers (Amazon/Flipkart/Nykaa)",
}


def rq8_unmet_needs(rows, matches):
    n, total = len(matches), len(rows)
    exploration_matches = [r for r in matches if r.get("friction_scope") == "category_exploration"]
    type_counts = Counter()
    type_negative = Counter()
    for r in exploration_matches:
        for ft in (r.get("friction_type") or []):
            if ft in NEED_LABELS:
                type_counts[ft] += 1
                if r.get("sentiment") == "negative":
                    type_negative[ft] += 1

    needs = []
    max_count = max(type_counts.values()) if type_counts else 1
    for ft, count in type_counts.most_common():
        rel_freq = count / max_count
        neg_share = type_negative[ft] / count if count else 0
        opportunity = round(10 * (0.6 * rel_freq + 0.4 * neg_share))
        needs.append({
            "name": NEED_LABELS[ft], "friction_type": ft, "count": count,
            "opportunity": max(1, min(10, opportunity)),
        })

    cats = _counts(exploration_matches, "category_mentioned", exclude=("not_category_specific",))
    cat_str = f", concentrated on **{_fmt_tag(cats[0][0])}**" if cats else ""
    narrative = (
        f"{len(exploration_matches)} category-exploration friction reviews{cat_str} map to "
        f"{len(needs)} distinct unmet needs (ranked below by Opportunity score — frequency "
        f"weighted 60%, how often the mention is negative-sentiment weighted 40%). Leads to "
        f"validate in Part 2 interviews, not a measured demand curve."
    ) if exploration_matches else None
    return {
        "title": "What unmet needs emerge consistently?",
        "n": n, "pct": _pct(n, total),
        "headline": f"{len(needs)} needs identified",
        "headline_label": f"from {len(exploration_matches)} category-exploration friction reviews",
        "chart_pairs": [(need["name"], need["count"]) for need in needs],
        "chart_title": "Unmet needs by mention count",
        "narrative": narrative, "quotes": _quotes(exploration_matches),
        "needs": needs,
    }


RQ_DEFINITIONS = [
    {
        "predicate": lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
        "insight_fn": rq1_habit,
    },
    {
        "predicate": lambda r: r.get("friction_scope") == "category_exploration",
        "insight_fn": rq2_exploration_blockers,
    },
    {
        "predicate": lambda r: "discovery_channel_mentioned" in (r.get("behavior_signal") or []),
        "insight_fn": rq3_discovery,
    },
    {
        "predicate": lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
        "insight_fn": rq4_habit_role,
    },
    {
        "predicate": lambda r: any(
            ft in ("no_info_before_purchase", "quality_uncertainty_unfamiliar_category", "sizing_fit_uncertainty")
            for ft in (r.get("friction_type") or [])
        ),
        "insight_fn": rq5_info_needed,
    },
    {
        "predicate": lambda r: r.get("friction_scope") in ("generic_ops", "category_exploration"),
        "insight_fn": rq6_frustrations,
    },
    {
        "predicate": lambda r: "exploration_attempt_positive" in (r.get("behavior_signal") or []),
        "insight_fn": rq7_segments,
    },
    {
        "predicate": lambda r: "exploration_attempt_negative" in (r.get("behavior_signal") or [])
        or "stated_avoidance" in (r.get("behavior_signal") or [])
        or r.get("friction_scope") == "category_exploration",
        "insight_fn": rq8_unmet_needs,
    },
]


def amazon_flipkart_evidence(rows):
    """Small supporting-evidence check for the "mental availability gap" framing note - only
    counts records where Amazon/Flipkart come up specifically in a new-category context, not any
    passing mention. Kept separate from the 8 RQs since it's supporting evidence, not a question."""
    hits = []
    for r in rows:
        text = (r.get("text") or "").lower()
        if ("amazon" in text or "flipkart" in text) and set(r.get("category_mentioned") or []) & NEW_ADJACENT_CATEGORIES:
            hits.append(r)
    return hits
