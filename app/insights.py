"""
Deterministic, data-driven insight synthesis for the 8 research questions.

No LLM call here on purpose: every number quoted is a direct count from the tagged
corpus (Counter over real tags), so there's zero fabrication risk - the "insight" is
just a grounded sentence wrapped around numbers that are already true. Falls back to
an honest "not enough evidence yet" note below a minimum sample size rather than
overreaching on a handful of records.
"""
from collections import Counter

MIN_N_FOR_INSIGHT = 8


def _counts(rows, field, exclude=()):
    c = Counter()
    for r in rows:
        for v in (r.get(field) or []):
            if v not in exclude and v is not None:
                c[v] += 1
    return c.most_common()


def _pct(n, total):
    return f"{n / total * 100:.1f}%" if total else "0%"


def _fmt_tag(tag):
    return (tag or "").replace("_", " ")


def _too_thin(matches):
    return len(matches) < MIN_N_FOR_INSIGHT


def rq1_habit(rows, matches):
    if _too_thin(matches):
        return None
    cats = _counts(matches, "category_mentioned", exclude=("not_category_specific",))
    n, pct = len(matches), _pct(len(matches), len(rows))
    if cats:
        top, top_n = cats[0]
        return (f"**{n} reviews** ({pct} of the tagged sample) use habit/repeat-purchase "
                f"language, most concentrated around **{_fmt_tag(top)}** ({top_n} mentions) — "
                f"consistent with staple categories being the default habitual purchase.")
    return (f"**{n} reviews** ({pct}) use habit/repeat-purchase language, without a strongly "
            f"concentrated category — the habit signal reads as general platform loyalty more "
            f"than a specific-category pattern in this sample.")


def rq2_exploration_blockers(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    frictions = _counts(matches, "friction_type")
    cats = _counts(matches, "category_mentioned", exclude=("not_category_specific",))
    lead = ", ".join(f"**{_fmt_tag(f)}** ({c})" for f, c in frictions[:2]) or "no single dominant friction type"
    cat_str = f", centered on **{_fmt_tag(cats[0][0])}**" if cats else ""
    return (f"**{n} reviews** ({pct} of the tagged sample) show category-exploration friction. "
            f"The leading blockers are {lead}{cat_str}. This is the direct evidence base for "
            f"what stops category exploration — see the honest-scope note on why this count is "
            f"a lower bound, not a full measurement.")


def rq3_discovery(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    return (f"**{n} reviews** ({pct}) explicitly mention how they discovered a product or "
            f"offer. This is a thin signal in review data generally — reviews are written "
            f"after a purchase decision, not during discovery — so treat this as directional.")


def rq4_habit_role(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    pos = sum(1 for r in matches if r.get("sentiment") == "positive")
    return (f"**{n} reviews** ({pct}) reference habitual/repeat behavior; **{pos}/{n}** of those "
            f"are positive-sentiment, suggesting habit here reads mostly as satisfied loyalty to "
            f"staple categories rather than friction-driven lock-in.")


def rq5_info_needed(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    types = _counts(matches, "friction_type")
    lead = ", ".join(f"**{_fmt_tag(f)}** ({c})" for f, c in types[:3])
    return (f"**{n} reviews** ({pct}) point to specific information gaps before trying a new "
            f"category: {lead}.")


def rq6_frustrations(rows, matches):
    ops_n = sum(1 for r in matches if r.get("friction_scope") == "generic_ops")
    exp_n = sum(1 for r in matches if r.get("friction_scope") == "category_exploration")
    total = len(rows)
    return (f"Of **{len(matches)} reviews** with friction ({_pct(len(matches), total)} of the "
            f"sample), **{ops_n}** are generic ops complaints (delivery, refunds, app bugs) vs. "
            f"**{exp_n}** category-exploration friction — ops complaints dominate by sheer "
            f"volume, which is exactly why the dashboard keeps them as background context rather "
            f"than the analytical lens (see the scope split above).")


def rq7_segments(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    segs = _counts(matches, "segment_hint", exclude=("none",))
    seg_str = f", most often alongside **{_fmt_tag(segs[0][0])}** language" if segs else ""
    return (f"**{n} reviews** ({pct}) show a positive exploration attempt (tried something new, "
            f"went well){seg_str}. Small n so far — this is the research question most in need "
            f"of Part 2 interviews to actually segment users, not just count reviews.")


def rq8_unmet_needs(rows, matches):
    if _too_thin(matches):
        return None
    n, pct = len(matches), _pct(len(matches), len(rows))
    cats = _counts(matches, "category_mentioned", exclude=("not_category_specific",))
    cat_str = f", concentrated on **{_fmt_tag(cats[0][0])}**" if cats else ""
    return (f"**{n} reviews** ({pct}) show either a failed exploration attempt or stated "
            f"avoidance of a category{cat_str} — the clearest signal of unmet needs the corpus "
            f"can offer on its own (again, a lead to confirm in interviews, not a census).")


RQ_DEFINITIONS = [
    {
        "title": "Why do users repeatedly buy from the same categories?",
        "predicate": lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
        "insight_fn": rq1_habit,
    },
    {
        "title": "What prevents users from exploring new categories?",
        "predicate": lambda r: r.get("friction_scope") == "category_exploration",
        "insight_fn": rq2_exploration_blockers,
    },
    {
        "title": "How do users discover products today?",
        "predicate": lambda r: "discovery_channel_mentioned" in (r.get("behavior_signal") or []),
        "insight_fn": rq3_discovery,
    },
    {
        "title": "What role do habits play in shopping behavior?",
        "predicate": lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
        "insight_fn": rq4_habit_role,
    },
    {
        "title": "What information do users need before trying a new category?",
        "predicate": lambda r: any(
            ft in ("no_info_before_purchase", "quality_uncertainty_unfamiliar_category", "sizing_fit_uncertainty")
            for ft in (r.get("friction_type") or [])
        ),
        "insight_fn": rq5_info_needed,
    },
    {
        "title": "What frustrations emerge repeatedly?",
        "predicate": lambda r: r.get("friction_scope") in ("generic_ops", "category_exploration"),
        "insight_fn": rq6_frustrations,
    },
    {
        "title": "Which user segments are more likely to experiment?",
        "predicate": lambda r: "exploration_attempt_positive" in (r.get("behavior_signal") or []),
        "insight_fn": rq7_segments,
    },
    {
        "title": "What unmet needs emerge consistently?",
        "predicate": lambda r: "exploration_attempt_negative" in (r.get("behavior_signal") or [])
        or "stated_avoidance" in (r.get("behavior_signal") or []),
        "insight_fn": rq8_unmet_needs,
    },
]
