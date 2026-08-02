# Discovery Engine — Part 1 (AI-Powered Review Analysis)

Graduation project, Part 1 of 4: an AI-powered analysis capability over public Zepto user feedback
(Play Store, App Store, Reddit), built to answer 8 specific research questions about why users
don't explore new categories on Zepto. Full context: [PART1_BRIEF.md](PART1_BRIEF.md).

**Ships as one deployed Streamlit app (public link) with two parts:**
1. **Analysis dashboard** — theme cards, category × friction, source split, the 8-question rollup.
2. **"Ask the Reviews" chatbot** — free-text Q&A over the tagged corpus, RAG-grounded on **Groq
   (Llama 3.3)**, every answer cited with counts + verbatim quotes, honest when the corpus can't
   answer something.

The analysis keeps a deliberate lens: **generic ops friction** (delivery, refunds, bugs) is kept
as background context only; **category-exploration friction** (why people don't try new
categories) is the primary analytical focus throughout — dashboard, insights, and chatbot alike.

**Public link:** _not yet deployed — added here once Phase 4 ships._

## Start here

| Doc | Purpose |
|---|---|
| [DOCS/01_PLAN.md](DOCS/01_PLAN.md) | Full execution plan — phases, deliverables, sequencing |
| [DOCS/02_WORKFLOW.md](DOCS/02_WORKFLOW.md) | Pipeline diagram + stage-by-stage description |
| [DOCS/03_THOUGHT_PROCESS.md](DOCS/03_THOUGHT_PROCESS.md) | Design rationale, tradeoffs, RQ mapping, scope limits |
| [DOCS/04_TAXONOMY_DRAFT_v0.md](DOCS/04_TAXONOMY_DRAFT_v0.md) | Tagging taxonomy — v0 hypothesis plus the v1 grounded spec (finalized after a 150-record open-coding pass), incl. `friction_scope` |
| [DOCS/05_EDGE_CASES_AND_TESTING.md](DOCS/05_EDGE_CASES_AND_TESTING.md) | Edge cases per phase, written before each phase is built, checked off after |

Later, once real data runs through the pipeline: `DOCS/06_INSIGHTS.md` and
`DOCS/07_VALIDATION_REPORT.md` (not created yet — see Plan Phase 4/5).

## Repo layout

```
Discovery Engine/
├── PART1_BRIEF.md          assignment context (source of truth for scope)
├── DOCS/                   plan, workflow, rationale, taxonomy, edge cases, (later) insights + validation
├── data/
│   ├── raw/                one file per source, untouched scrape output
│   └── processed/          cleaned + tagged datasets, pattern tables
├── src/                    scraping / tagging / analysis code (added as each phase is built)
├── app/                    Streamlit app — dashboard tab + "Ask the Reviews" chatbot tab (Phase 4)
├── notebooks/               exploratory analysis
└── .env                    API keys — never committed (see .env.example)
```

## Tech choices

- **LLM:** Groq, Llama 3.3 (70B) — open-coding, at-scale tagging, and chatbot generation.
- **Embeddings (chatbot retrieval):** local `sentence-transformers` (e.g. `all-MiniLM-L6-v2`) —
  free, no extra API key.
- **App:** Streamlit, deployed on Streamlit Community Cloud (public link).

## Status

- **Phase 1 (gather):** Play Store scraping complete — **163,539 unique reviews**, reached by
  genuine exhaustion (every remaining sort/rating combination returned zero new results, not cut
  short). Reddit scraping ongoing in the background (Reddit's own rate-limiting makes this slow —
  see [DOCS/05_EDGE_CASES_AND_TESTING.md](DOCS/05_EDGE_CASES_AND_TESTING.md)), **2,757 posts +
  comments so far** and growing. App Store: attempted, confirmed unavailable via any public
  method (documented, not a silent gap). Combined unified corpus so far: **166,296 records**.
- **Phase 2 (structure):** Taxonomy v1 finalized from a 150-record open-coding pass (see
  [DOCS/04_TAXONOMY_DRAFT_v0.md](DOCS/04_TAXONOMY_DRAFT_v0.md)). At-scale tagging is running via
  Groq — **discovered Llama 3.3 70B's free-tier budget is only 100,000 tokens/day, which caps out
  after ~190 tagged reviews**, so tagging was switched to **Llama 3.1 8B Instant** (separate quota,
  no daily wall hit at equivalent usage, and plenty capable for bounded-vocabulary classification).
  Still a multi-day background process to cover the full corpus, not instant. Resumes automatically
  (skips already-tagged ids) if stopped/restarted, and tags in random order so partial progress is
  always an unbiased subsample.
- **Phase 3/4:** not started yet — waiting on a large-enough tagged subsample to analyze.
