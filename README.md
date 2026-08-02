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

## Repo & deployment

- **GitHub (public):** https://github.com/harchaa/zepto-discovery-engine
- **Public Streamlit link:** not yet live — Streamlit Community Cloud's deploy step requires
  logging in with GitHub OAuth through their web UI, which can't be driven headlessly. To finish
  it: go to [share.streamlit.io](https://share.streamlit.io) → "New app" → pick this repo/branch
  `master` → main file path `app/streamlit_app.py` → in the app's **Settings → Secrets**, add
  `GROQ_API_KEY = "<your key>"` → Deploy. Takes about a minute; update this line with the URL once live.
- To continue the pipeline locally: `pip install -r requirements.txt`, add `.env` from
  `.env.example`, then run the `src/` scripts in order (see [DOCS/01_PLAN.md](DOCS/01_PLAN.md)).

## Status

- **Phase 1 (gather) — complete, three sources:** Play Store **163,539** (genuine exhaustion —
  every remaining sort/rating combination returned zero new results). Reddit **1,073 posts +
  38,861 comments** (complete, despite heavy platform rate-limiting along the way — see
  [DOCS/05_EDGE_CASES_AND_TESTING.md](DOCS/05_EDGE_CASES_AND_TESTING.md)). App Store **450
  reviews** — an earlier test wrongly concluded this feed was dead platform-wide; a same-day
  re-test proved that wrong (likely a transient Apple-side outage at the time), corrected once
  caught by review. Combined unified corpus: **~203,900 records**.
- **Phase 2 (structure):** Taxonomy v1 finalized from a 150-record open-coding pass (see
  [DOCS/04_TAXONOMY_DRAFT_v0.md](DOCS/04_TAXONOMY_DRAFT_v0.md)). At-scale tagging runs via Groq
  Llama 3.1 8B Instant (Llama 3.3 70B is reserved for the chatbot — its free-tier budget of only
  100,000 tokens/day caps out after ~190 tagged reviews). Workload split into three tiers to stay
  within real rate limits: off-topic Reddit skipped entirely, "trivial" reviews (short, no
  friction/category keyword) auto-tagged deterministically at zero LLM cost, and the LLM reserved
  for the substantive pool, capped at a 20,000-review target. A round-1 human spot-check (20
  records) caught the tagger over-applying `category_exploration` and `stated_avoidance` —
  corrected via a deterministic re-derivation pass (`src/correct_tags.py`) plus a tightened
  prompt for new tagging (see [DOCS/00b_REVIEW_NOTES_ROUND2.md](DOCS/00b_REVIEW_NOTES_ROUND2.md)).
- **Phase 3/4:** built and working — pattern-analysis pipeline, Streamlit dashboard, and the
  "Ask the Reviews" RAG chatbot all running locally; public deployment pending.
