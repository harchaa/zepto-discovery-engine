"""
Discovery Engine - Part 1 deliverable app.
Two tabs: Analysis Dashboard (organized around the 8 research questions), and
"Ask the Reviews" (compact RAG chatbot).
Run with: streamlit run app/streamlit_app.py
"""
import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chatbot import answer as chatbot_answer  # noqa: E402
from chatbot import index_available  # noqa: E402
from data_access import load_joined_tagged, load_pattern_tables, load_phase1_summary  # noqa: E402
from insights import RQ_DEFINITIONS, amazon_flipkart_evidence  # noqa: E402

# ---- Theme: dark surface matching .streamlit/config.toml, Zepto-purple as the brand accent.
ZEPTO_PURPLE = "#8B2FE8"
ZEPTO_PURPLE_LIGHT = "#B98CF2"
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#2fbf2f", "#9085e9", "#e66767",
)
INK = "#f2eefc"
SECONDARY_INK = "#c9c3d9"
MUTED = "#8b849e"
GRIDLINE = "#2a2438"
SURFACE = "#17131f"
PAGE_BG = "#0d0b12"

SOURCE_BADGE_COLORS = {
    "play_store": "#199e70", "app_store": "#3987e5", "reddit": "#d95926",
}
SOURCE_LABELS = {"play_store": "Play Store", "app_store": "App Store", "reddit": "Reddit"}

st.set_page_config(page_title="Zepto Discovery Engine", layout="wide", page_icon="🟣")

CUSTOM_CSS = f"""
<style>
.stApp {{ background: {PAGE_BG}; }}
div[data-testid="stExpander"] {{ background: {SURFACE}; border: 1px solid rgba(139,47,232,0.25); border-radius: 12px; }}
div[data-testid="stMetric"] {{ background: {SURFACE}; border: 1px solid rgba(139,47,232,0.25); border-radius: 12px; padding: 14px 16px; }}
div[data-testid="stAlert"] {{ border-radius: 12px; }}

.dge-hero {{ background: linear-gradient(135deg, rgba(139,47,232,0.28), rgba(139,47,232,0.04)); border: 1px solid rgba(139,47,232,0.35); border-radius: 16px; padding: 20px 24px; margin-bottom: 18px; }}
.dge-hero h1 {{ margin: 0 0 4px 0; font-size: 1.7rem; }}
.dge-hero p {{ margin: 0; color: {SECONDARY_INK}; font-size: 0.95rem; }}

.insight-card {{ background: {SURFACE}; border: 1px solid rgba(139,47,232,0.25); border-left: 3px solid {ZEPTO_PURPLE}; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }}
.rq-title {{ font-weight: 600; font-size: 0.95rem; color: {INK}; margin-bottom: 6px; }}
.rq-body {{ color: {SECONDARY_INK}; font-size: 0.92rem; line-height: 1.5; }}
.rq-thin {{ color: {MUTED}; font-style: italic; font-size: 0.88rem; }}

.story-bullet {{ background: {SURFACE}; border: 1px solid rgba(139,47,232,0.2); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; color: {SECONDARY_INK}; font-size: 0.92rem; line-height: 1.5; }}
.story-bullet b {{ color: {INK}; }}

div[data-testid="stChatMessage"] {{ background: {SURFACE}; border-radius: 14px; border: 1px solid rgba(139,47,232,0.18); margin-bottom: 8px; }}

.quote-block {{ border-left: 2px solid {ZEPTO_PURPLE_LIGHT}; padding: 4px 12px; margin: 6px 0; color: {SECONDARY_INK}; font-size: 0.9rem; }}
.quote-meta {{ display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }}
.source-badge {{ display: inline-block; font-size: 0.72rem; font-weight: 600; padding: 1px 8px; border-radius: 999px; color: #0d0b12; }}
.date-label {{ color: {MUTED}; font-size: 0.78rem; }}

.need-row {{ display: flex; align-items: center; justify-content: space-between; background: {SURFACE}; border: 1px solid rgba(139,47,232,0.2); border-radius: 8px; padding: 8px 14px; margin-bottom: 6px; }}
.need-name {{ color: {INK}; font-size: 0.9rem; }}
.need-score {{ background: {ZEPTO_PURPLE}; color: white; font-weight: 700; font-size: 0.82rem; padding: 2px 10px; border-radius: 999px; white-space: nowrap; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def base_layout(fig, height=320):
    fig.update_layout(
        height=height, plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(color=INK, size=13), margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PAGE_BG, font_color=INK, bordercolor=ZEPTO_PURPLE_LIGHT),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    return fig


def small_bar(pairs, title, color=ZEPTO_PURPLE, top_n=8):
    if not pairs:
        return None
    pairs = pairs[:top_n]
    labels = [(str(p[0]) or "none").replace("_", " ") for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=color))
    fig.update_layout(title=title)
    return base_layout(fig, height=max(220, 30 * len(labels) + 60))


def source_badge(source):
    color = SOURCE_BADGE_COLORS.get(source, MUTED)
    label = SOURCE_LABELS.get(source, source)
    return f'<span class="source-badge" style="background:{color};">{label}</span>'


def quote_html(q):
    rating = f' · {q["rating"]}★' if q.get("rating") else ""
    return (
        f'<div class="quote-block">"{q["text"]}"</div>'
        f'<div class="quote-meta">{source_badge(q["source"])}'
        f'<span class="date-label">{q["date"]}{rating}</span></div>'
    )


def render_rq_tab(idx, rq, rows):
    matches = [r for r in rows if rq["predicate"](r)]
    result = rq["insight_fn"](rows, matches)

    st.subheader(f"Q{idx}. {result['title']}")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric(result["headline"], result["headline_label"])
        if result.get("narrative"):
            st.markdown(f'<div class="insight-card"><div class="rq-body">{result["narrative"]}</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<div class="rq-thin">Not enough tagged evidence yet to synthesize a '
                        "reliable narrative — check back as tagging accumulates.</div>",
                        unsafe_allow_html=True)
    with c2:
        fig = small_bar(result["chart_pairs"], result["chart_title"])
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("No chart-able breakdown yet for this question.")

    if result.get("needs"):
        st.markdown("**Unmet needs, ranked by Opportunity score** (formula: 60% relative "
                    "frequency + 40% negative-sentiment share — see `app/insights.py`)")
        for need in result["needs"]:
            st.markdown(
                f'<div class="need-row"><span class="need-name">{need["name"]} '
                f'<span style="color:{MUTED};">(n={need["count"]})</span></span>'
                f'<span class="need-score">Opportunity {need["opportunity"]}/10</span></div>',
                unsafe_allow_html=True,
            )

    if result["quotes"]:
        st.markdown("**Real quotes**")
        st.markdown("".join(quote_html(q) for q in result["quotes"]), unsafe_allow_html=True)
    else:
        st.caption("No verbatim quotes available for this question yet.")


st.markdown(
    '<div class="dge-hero"><h1>🟣 Zepto Discovery Engine</h1>'
    "<p>AI-powered analysis of public Zepto user feedback (Play Store + App Store + Reddit) — "
    "why users repeat-buy the same categories and what blocks exploring new ones. Part 1 of a "
    "4-part growth research project.</p></div>",
    unsafe_allow_html=True,
)

tab_dashboard, tab_chat = st.tabs(["📊 Analysis Dashboard", "💬 Ask the Reviews"])

with tab_dashboard:
    phase1 = load_phase1_summary()
    tables = load_pattern_tables()
    rows = load_joined_tagged()

    if phase1 is None or tables is None or not rows:
        st.warning(
            "No tagged data yet — run `src/unify_reviews.py`, `src/clean_corpus.py`, "
            "`src/tag_at_scale.py`, then `src/analyze_patterns.py` first."
        )
        st.stop()

    gathered = phase1["total_unique_after_dedupe"]
    tagged_n = tables["meta"]["n_tagged_and_on_topic"]
    src_split = tables["meta"]["source_split"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gathered", f"{gathered:,}")
    c2.metric("Tagged", f"{tagged_n:,}", f"{tagged_n/gathered:.1%} of gathered")
    c3.metric("Play Store / App Store", f"{src_split.get('play_store', 0):,} / {src_split.get('app_store', 0):,}")
    c4.metric("Reddit", f"{src_split.get('reddit', 0):,}")

    # ---- The story, upfront -------------------------------------------------
    habit_n = sum(1 for r in rows if "habit_repeat_purchase" in (r.get("behavior_signal") or []))
    expl_n = tables["category_exploration_primary"]["n"]
    top_expl_types = tables["category_exploration_primary"]["top_friction_types"][:3]
    az_fk = amazon_flipkart_evidence(rows)

    st.subheader("The story")
    st.markdown(
        f'<div class="story-bullet">🔁 <b>Habit / mission-mode dominates.</b> {habit_n:,} reviews '
        f"({habit_n/tagged_n*100:.1f}%) use repeat-purchase language — staples are the default, "
        "low-effort purchase.</div>"
        f'<div class="story-bullet">👻 <b>New-category exploration is almost invisible in '
        f"reviews — this is a survivorship finding, not missing data.</b> Only {expl_n:,} reviews "
        f"({expl_n/tagged_n*100:.2f}%) show category-exploration friction. People who never buy a "
        "category rarely leave a review about it, so avoidance is structurally under-represented "
        "here. Review-based avoidance signals are <b>leads to validate by interviews</b>, not a "
        "measured avoidance rate.</div>"
        f'<div class="story-bullet">🔍 <b>Where users DO try a new category, the friction is '
        "trust / quality-uncertainty / authenticity</b> — "
        + ", ".join(f"<b>{(t[0] or '').replace('_',' ')}</b> ({t[1]})" for t in top_expl_types)
        + " — not generic delivery/ops complaints.</div>"
        f'<div class="story-bullet">🛒 <b>Users default to Amazon/Flipkart for non-grocery '
        f"needs</b> (a mental-availability gap) — thin but real evidence: {len(az_fk)} reviews "
        "explicitly reference Amazon/Flipkart in an apparel/electronics/personal-care context, "
        "e.g. exchange-policy and authenticity comparisons.</div>",
        unsafe_allow_html=True,
    )
    if az_fk:
        with st.expander(f"Amazon/Flipkart evidence (n={len(az_fk)})"):
            for r in az_fk[:5]:
                st.markdown(quote_html({
                    "text": (r.get("text") or "")[:300], "source": r["source"],
                    "date": (r.get("date") or "")[:10], "rating": r.get("rating"),
                }), unsafe_allow_html=True)

    st.divider()
    st.subheader("The 8 research questions")
    st.caption("Primary navigation for this analysis — one tab per question, each with a "
               "headline number, a small chart, and real verbatim quotes.")

    rq_tabs = st.tabs([f"Q{i}" for i in range(1, 9)])
    for i, (tab, rq) in enumerate(zip(rq_tabs, RQ_DEFINITIONS), 1):
        with tab:
            render_rq_tab(i, rq, rows)

with tab_chat:
    st.markdown(
        '<div class="dge-hero" style="margin-bottom:12px;"><h1 style="font-size:1.2rem;">💬 Ask the Reviews</h1>'
        "<p>Short, cited answers grounded in the tagged review corpus — retrieval-augmented, "
        "declines when the corpus doesn't support an answer.</p></div>",
        unsafe_allow_html=True,
    )

    if not index_available():
        st.warning("Embeddings index not built yet — run `src/build_embeddings.py` first.")
    else:
        st.caption(
            "Try: \"What do people say about beauty products?\", \"Why don't users trust fresh "
            "produce?\", \"Which categories get the most complaints?\""
        )
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for turn in st.session_state.chat_history:
            avatar = "🟣" if turn["role"] == "assistant" else "🧑"
            with st.chat_message(turn["role"], avatar=avatar):
                st.markdown(turn["content"])

        question = st.chat_input("Ask a question about the Zepto review corpus...")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(question)
            with st.chat_message("assistant", avatar="🟣"):
                with st.spinner("Retrieving and asking Llama..."):
                    result = chatbot_answer(question)
                st.markdown(result["answer"])
                if result["retrieved"]:
                    with st.expander(f"Retrieved {len(result['retrieved'])} reviews"):
                        for r in result["retrieved"]:
                            st.caption(
                                f"sim={r['similarity']:.2f} · {r['source']} · "
                                f"{(r.get('date') or '')[:10]} · rating={r.get('rating')}"
                            )
                            st.write(r["text"][:300])
            st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
