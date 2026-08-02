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

# Validated categorical palette (fixed order - never cycled/reassigned), see DOCS dataviz notes.
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED = (
    "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948",
)
INK = "#0b0b0b"
SECONDARY_INK = "#52514e"
MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

st.set_page_config(page_title="Zepto Discovery Engine", layout="wide")


def base_layout(fig, height=360):
    fig.update_layout(
        height=height,
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(color=INK, size=13),
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    fig.update_yaxes(gridcolor=GRIDLINE, linecolor=MUTED, zeroline=False)
    return fig


def bar_from_pairs(pairs, title, color=BLUE, top_n=12, orientation="h"):
    pairs = pairs[:top_n]
    labels = [p[0] or "none" for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=color))
    fig.update_layout(title=title)
    return base_layout(fig, height=max(240, 28 * len(labels) + 80))


st.title("Zepto Discovery Engine")
st.caption(
    "AI-powered analysis of public Zepto user feedback (Play Store + Reddit) — why users "
    "repeat-buy the same categories and what blocks exploring new ones. Part 1 of a 4-part "
    "growth research project."
)

tab_dashboard, tab_chat = st.tabs(["Analysis Dashboard", "Ask the Reviews"])

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
        "gathered corpus, and is reported as such rather than presented as complete. App Store "
        "reviews were attempted and found unavailable via any public method (documented in "
        "`DOCS/01_PLAN.md`) — this corpus is Play Store + Reddit only. Tagging accuracy has not "
        "yet been human-validated (Phase 5, not run) — treat theme counts as provisional; a "
        "known concern already flagged is the tagger over-applying `category_exploration` to "
        "routine rotten-produce complaints (see `DOCS/05_EDGE_CASES_AND_TESTING.md`).",
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
        "Category-exploration\n(primary lens)": tables["category_exploration_primary"]["n"],
        "Generic ops\n(context only)": tables["ops_friction_context_only"]["n"],
        "No friction / other": tagged_n - tables["category_exploration_primary"]["n"] - tables["ops_friction_context_only"]["n"],
    }
    fig = go.Figure(go.Bar(
        x=list(scope_counts.values()), y=list(scope_counts.keys()), orientation="h",
        marker_color=[VIOLET, MUTED, GRIDLINE],
    ))
    fig.update_layout(title=f"Friction scope split (n={tagged_n})")
    st.plotly_chart(base_layout(fig, height=260), width='stretch')

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            bar_from_pairs(tables["ops_friction_context_only"]["top_friction_types"],
                           "Generic ops friction (context only)", color=MUTED),
            width='stretch',
        )
    with col_b:
        exp_types = tables["category_exploration_primary"]["top_friction_types"]
        if exp_types:
            st.plotly_chart(
                bar_from_pairs(exp_types, "Category-exploration friction (primary lens)", color=VIOLET),
                width='stretch',
            )
        else:
            st.warning(
                f"No category-exploration friction tagged yet in this sample (n={tagged_n}). "
                "This matches the brief's expectation that this signal is rare in review data — "
                "needs a larger tagged sample to surface enough instances. Not fabricated."
            )

    st.divider()
    st.subheader("Behavior signals")
    behavior = tables["behavior_signal_breakdown"]
    behavior_pairs = sorted(behavior.items(), key=lambda x: -x[1])
    st.plotly_chart(bar_from_pairs(behavior_pairs, "Behavior signal frequency", color=AQUA), width='stretch')

    avoidance = tables["stated_avoidance_leads"]
    with st.expander(f"Stated-avoidance leads (n={avoidance['n']}) — leads, not a measured rate"):
        st.caption(avoidance["note"])
        avoid_rows = [r for r in rows if "stated_avoidance" in (r.get("behavior_signal") or [])]
        quotes = find_quotes(avoid_rows, lambda r: True, limit=5)
        if quotes:
            for q in quotes:
                st.markdown(f"> {q['text']}")
                st.caption(f"— {q['source']}, {q['date']}" + (f", {q['rating']}★" if q['rating'] else ""))
        else:
            st.write("None in the current tagged sample.")

    st.divider()
    st.subheader("Sentiment & category mix")
    col_c, col_d = st.columns(2)
    with col_c:
        sent_pairs = sorted(tables["sentiment_breakdown"].items(), key=lambda x: -x[1])
        st.plotly_chart(bar_from_pairs(sent_pairs, "Sentiment", color=BLUE, top_n=6), width='stretch')
    with col_d:
        cat_pairs = sorted(tables["category_mentioned_overall"].items(), key=lambda x: -x[1])
        st.plotly_chart(bar_from_pairs(cat_pairs, "Category mentioned", color=ORANGE), width='stretch')

    st.divider()
    st.subheader("The 8 research questions — evidence rollup")
    st.caption("Each answered with counts from the tagged sample and real quotes, or an honest 'not enough evidence yet' note.")

    def rq_section(title, predicate, note=""):
        matches = [r for r in rows if predicate(r)]
        with st.expander(f"{title}  ·  n={len(matches)}"):
            if note:
                st.caption(note)
            if not matches:
                st.write("No matching tagged records yet in this sample.")
                return
            for q in find_quotes(matches, lambda r: True, limit=4):
                st.markdown(f"> {q['text']}")
                st.caption(f"— {q['source']}, {q['date']}" + (f", {q['rating']}★" if q['rating'] else ""))

    rq_section(
        "1. Why do users repeatedly buy from the same categories?",
        lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
    )
    rq_section(
        "2. What prevents users from exploring new categories?",
        lambda r: r.get("friction_scope") == "category_exploration",
    )
    rq_section(
        "3. How do users discover products today?",
        lambda r: "discovery_channel_mentioned" in (r.get("behavior_signal") or []),
    )
    rq_section(
        "4. What role do habits play in shopping behavior?",
        lambda r: "habit_repeat_purchase" in (r.get("behavior_signal") or []),
    )
    rq_section(
        "5. What information do users need before trying a new category?",
        lambda r: any(ft in ("no_info_before_purchase", "quality_uncertainty_unfamiliar_category",
                              "sizing_fit_uncertainty") for ft in (r.get("friction_type") or [])),
    )
    rq_section(
        "6. What frustrations emerge repeatedly?",
        lambda r: r.get("friction_scope") in ("generic_ops", "category_exploration"),
        note="Best-supported question given the data's inherent skew toward experienced friction.",
    )
    rq_section(
        "7. Which user segments are more likely to experiment?",
        lambda r: "exploration_attempt_positive" in (r.get("behavior_signal") or []),
    )
    rq_section(
        "8. What unmet needs emerge consistently?",
        lambda r: "exploration_attempt_negative" in (r.get("behavior_signal") or [])
        or "stated_avoidance" in (r.get("behavior_signal") or []),
    )

with tab_chat:
    st.subheader("Ask the Reviews")
    st.caption(
        "Free-text Q&A grounded in the tagged review corpus — retrieval-augmented, answers "
        "only from retrieved reviews, always cited. Declines when the corpus doesn't support "
        "an answer, rather than guessing. See DOCS/03_THOUGHT_PROCESS.md §8."
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
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])

        question = st.chat_input("Ask a question about the Zepto review corpus...")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
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
