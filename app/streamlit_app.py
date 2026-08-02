"""
Discovery Engine - Part 1 deliverable app.
Two tabs: Analysis Dashboard, and "Ask the Reviews" (RAG chatbot).
Run with: streamlit run app/streamlit_app.py
"""
import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chatbot import answer as chatbot_answer  # noqa: E402
from chatbot import index_available  # noqa: E402
from data_access import find_quotes, load_joined_tagged, load_pattern_tables, load_phase1_summary  # noqa: E402
from insights import RQ_DEFINITIONS  # noqa: E402

# ---- Theme: dark surface matching .streamlit/config.toml, Zepto-purple as the brand accent.
# Chart data colors stay the validated dark-mode categorical set (dataviz skill reference) -
# brand purple is used for UI chrome/accents, not forced onto every data series, to keep the
# categorical palette's CVD-safety guarantees intact.
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

st.set_page_config(page_title="Zepto Discovery Engine", layout="wide", page_icon="🟣")

CUSTOM_CSS = f"""
<style>
.stApp {{ background: {PAGE_BG}; }}

/* Cards */
div[data-testid="stExpander"] {{
    background: {SURFACE};
    border: 1px solid rgba(139,47,232,0.25);
    border-radius: 12px;
}}
div[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid rgba(139,47,232,0.25);
    border-radius: 12px;
    padding: 14px 16px;
}}
div[data-testid="stAlert"] {{ border-radius: 12px; }}

/* Header banner */
.dge-hero {{
    background: linear-gradient(135deg, rgba(139,47,232,0.28), rgba(139,47,232,0.04));
    border: 1px solid rgba(139,47,232,0.35);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 18px;
}}
.dge-hero h1 {{ margin: 0 0 4px 0; font-size: 1.7rem; }}
.dge-hero p {{ margin: 0; color: {SECONDARY_INK}; font-size: 0.95rem; }}

/* Insight cards */
.insight-card {{
    background: {SURFACE};
    border: 1px solid rgba(139,47,232,0.25);
    border-left: 3px solid {ZEPTO_PURPLE};
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
}}
.insight-card .rq-title {{ font-weight: 600; font-size: 0.95rem; color: {INK}; margin-bottom: 6px; }}
.insight-card .rq-body {{ color: {SECONDARY_INK}; font-size: 0.92rem; line-height: 1.5; }}
.insight-card .rq-thin {{ color: {MUTED}; font-style: italic; font-size: 0.88rem; }}

/* Chat bubbles */
div[data-testid="stChatMessage"] {{
    background: {SURFACE};
    border-radius: 14px;
    border: 1px solid rgba(139,47,232,0.18);
    margin-bottom: 8px;
}}
.quote-block {{
    border-left: 2px solid {ZEPTO_PURPLE_LIGHT};
    padding: 4px 12px;
    margin: 6px 0;
    color: {SECONDARY_INK};
    font-size: 0.9rem;
}}
.quote-meta {{ color: {MUTED}; font-size: 0.78rem; margin-bottom: 8px; }}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def base_layout(fig, height=360):
    fig.update_layout(
        height=height,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(color=INK, size=13),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PAGE_BG, font_color=INK, bordercolor=ZEPTO_PURPLE_LIGHT),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    return fig


def bar_from_pairs(pairs, title, color=BLUE, top_n=12):
    pairs = pairs[:top_n]
    labels = [(p[0] or "none").replace("_", " ") for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=color))
    fig.update_layout(title=title)
    return base_layout(fig, height=max(240, 28 * len(labels) + 80))


def quote_html(q):
    rating = f", {q['rating']}★" if q.get("rating") else ""
    return (
        f'<div class="quote-block">"{q["text"]}"</div>'
        f'<div class="quote-meta">— {q["source"]}, {q["date"]}{rating}</div>'
    )


st.markdown(
    '<div class="dge-hero"><h1>🟣 Zepto Discovery Engine</h1>'
    "<p>AI-powered analysis of public Zepto user feedback (Play Store + Reddit) — why users "
    "repeat-buy the same categories and what blocks exploring new ones. Part 1 of a 4-part "
    "growth research project.</p></div>",
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

    st.subheader("Corpus at a glance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reviews/posts gathered", f"{gathered:,}")
    c2.metric("Tagged & analyzed so far", f"{tagged_n:,}", f"{tagged_n/gathered:.1%} of gathered")
    src_split = tables["meta"]["source_split"]
    c3.metric("Play Store (tagged)", f"{src_split.get('play_store', 0):,}")
    c4.metric("Reddit (tagged)", f"{src_split.get('reddit', 0):,}")

    st.info(
        "**Honest scope note:** tagging is a resumable background process rate-limited by the "
        "LLM provider's daily quota (see `DOCS/03_THOUGHT_PROCESS.md §9`) — it accumulates over "
        "multiple runs, tagging a randomized (unbiased) subsample of the gathered corpus each "
        "time. Every number on this page reflects the sample analyzed **so far**, not the full "
        "gathered corpus. Corpus is Play Store + App Store + Reddit. A round-1 human spot-check "
        "(20 records, Aug 2 2026) found the tagger over-applying `category_exploration` to "
        "routine ops/quality complaints and `stated_avoidance` to complaints with no actual "
        "avoidance language — both corrected (deterministic re-derivation for already-tagged "
        "records, tightened prompt going forward). A second spot-check round is still pending "
        "(`DOCS/05_EDGE_CASES_AND_TESTING.md`) — treat theme counts as provisional until then.",
        icon="ℹ️",
    )

    st.divider()
    st.subheader("The analytical lens: generic ops friction vs. category-exploration friction")
    st.caption(
        "Per the project's core design decision (DOCS/03_THOUGHT_PROCESS.md §7): generic "
        "operational complaints (delivery, refunds, app bugs) are kept as background context "
        "only. The rest of this dashboard's analysis foregrounds category-exploration friction "
        "— the friction specifically tied to trying or avoiding a *new* product category — "
        "because that's what the company goal and research questions are actually about."
    )
    scope_counts = {
        "Category-exploration (primary lens)": tables["category_exploration_primary"]["n"],
        "Generic ops (context only)": tables["ops_friction_context_only"]["n"],
        "No friction / other": tagged_n - tables["category_exploration_primary"]["n"] - tables["ops_friction_context_only"]["n"],
    }
    fig = go.Figure(go.Bar(
        x=list(scope_counts.values()), y=list(scope_counts.keys()), orientation="h",
        marker_color=[ZEPTO_PURPLE, MUTED, GRIDLINE],
    ))
    fig.update_layout(title=f"Friction scope split (n={tagged_n})")
    st.plotly_chart(base_layout(fig, height=260), width="stretch")

    exp_n = tables["category_exploration_primary"]["n"]
    st.markdown(
        f'<div class="insight-card" style="border-left-color:{ZEPTO_PURPLE_LIGHT};">'
        f'<div class="rq-title">How to read this: {exp_n} exploration-friction records is a '
        f"thin slice ({exp_n/tagged_n*100:.1f}% of tagged) — expected, not a failure</div>"
        '<div class="rq-body">This is the predicted survivorship effect (see PART1_BRIEF.md\'s '
        "honest scope note): people who never try a new category rarely leave a review about it, "
        "so avoidance is structurally under-represented in review data. Read this dashboard as "
        "proof the signal is genuinely thin in reviews, plus a set of specific hypotheses "
        "(trust, quality-uncertainty, authenticity) worth testing directly in Part 2 interviews — "
        "not as a measured avoidance rate.</div></div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            bar_from_pairs(tables["ops_friction_context_only"]["top_friction_types"],
                           "Generic ops friction (context only)", color=MUTED),
            width="stretch",
        )
    with col_b:
        exp_types = tables["category_exploration_primary"]["top_friction_types"]
        if exp_types:
            st.plotly_chart(
                bar_from_pairs(exp_types, "Category-exploration friction (primary lens)", color=ZEPTO_PURPLE),
                width="stretch",
            )
        else:
            st.warning(
                f"No category-exploration friction tagged yet in this sample (n={tagged_n}). "
                "Needs a larger tagged sample to surface enough instances. Not fabricated."
            )

    st.divider()
    st.subheader("Behavior signals")
    behavior_pairs = sorted(tables["behavior_signal_breakdown"].items(), key=lambda x: -x[1])
    st.plotly_chart(bar_from_pairs(behavior_pairs, "Behavior signal frequency", color=AQUA), width="stretch")

    avoidance = tables["stated_avoidance_leads"]
    with st.expander(f"Stated-avoidance leads (n={avoidance['n']}) — leads, not a measured rate"):
        st.caption(avoidance["note"])
        avoid_rows = [r for r in rows if "stated_avoidance" in (r.get("behavior_signal") or [])]
        quotes = find_quotes(avoid_rows, lambda r: True, limit=5)
        if quotes:
            st.markdown("".join(quote_html(q) for q in quotes), unsafe_allow_html=True)
        else:
            st.write("None in the current tagged sample.")

    st.divider()
    st.subheader("Sentiment & category mix")
    col_c, col_d = st.columns(2)
    with col_c:
        sent_pairs = sorted(tables["sentiment_breakdown"].items(), key=lambda x: -x[1])
        st.plotly_chart(bar_from_pairs(sent_pairs, "Sentiment", color=BLUE, top_n=6), width="stretch")
    with col_d:
        cat_pairs = sorted(tables["category_mentioned_overall"].items(), key=lambda x: -x[1])
        st.plotly_chart(bar_from_pairs(cat_pairs, "Category mentioned", color=ORANGE), width="stretch")

    st.divider()
    st.subheader("Key insights — the 8 research questions")
    st.caption(
        "Each is a synthesized, data-driven finding (real counts, not narrative filler) — not a "
        "raw quote dump. Supporting quotes are tucked underneath as evidence, not the headline."
    )

    for i, rq in enumerate(RQ_DEFINITIONS, 1):
        matches = [r for r in rows if rq["predicate"](r)]
        insight = rq["insight_fn"](rows, matches)
        st.markdown('<div class="insight-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="rq-title">{i}. {rq["title"]}  ·  n={len(matches)}</div>', unsafe_allow_html=True)
        if insight:
            st.markdown(f'<div class="rq-body">{insight}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="rq-thin">Not enough tagged evidence yet to synthesize a reliable '
                "insight — check back as tagging accumulates.</div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        if matches:
            with st.expander("Supporting quotes"):
                quotes = find_quotes(matches, lambda r: True, limit=3)
                st.markdown("".join(quote_html(q) for q in quotes), unsafe_allow_html=True)

with tab_chat:
    st.markdown(
        '<div class="dge-hero" style="margin-bottom:12px;"><h1 style="font-size:1.2rem;">💬 Ask the Reviews</h1>'
        "<p>Free-text Q&amp;A grounded in the tagged review corpus — retrieval-augmented, "
        "answers only from retrieved reviews, always cited. Declines when the corpus doesn't "
        "support an answer, rather than guessing.</p></div>",
        unsafe_allow_html=True,
    )

    if not index_available():
        st.warning("Embeddings index not built yet — run `src/build_embeddings.py` first.")
    else:
        st.caption(
            "Try: \"What do people say about beauty products?\", \"Why don't users trust fresh "
            "produce?\", \"Which categories get the most complaints?\", \"Why do people avoid "
            "buying electronics here?\""
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
                with st.spinner("Retrieving relevant reviews and asking Llama 3.3..."):
                    result = chatbot_answer(question)
                st.markdown(result["answer"])
                if result["retrieved"]:
                    with st.expander(f"Retrieved {len(result['retrieved'])} reviews (similarity scores)"):
                        for r in result["retrieved"]:
                            st.caption(
                                f"sim={r['similarity']:.2f} · {r['source']} · "
                                f"{(r.get('date') or '')[:10]} · rating={r.get('rating')}"
                            )
                            st.write(r["text"][:300])
            st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
