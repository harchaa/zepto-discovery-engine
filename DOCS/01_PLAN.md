# Execution Plan — AI-Powered Discovery Engine (Part 1)

Status: **Draft v1** · Owner: PM (Growth, Zepto) · Scope: Part 1 of 4 only.

## 0. Objective, restated

Build an analysis capability — not a canned-answer machine — that ingests Zepto user feedback at
scale, tags it in a way that is countable and sliceable, surfaces frequency-backed patterns with
real quotes, and makes the 8 research questions (see [PART1_BRIEF.md](../PART1_BRIEF.md))
answerable with evidence. Output feeds Part 2 (interviews), which is the real validation step —
this engine produces **leads and hypotheses**, not proof.

**Analytical lens (firm requirement):** the tagging and every downstream pattern/insight must
keep **generic ops friction** (delivery speed, damaged/wrong item, refunds, app bugs, customer
support — things that would happen regardless of category) explicitly separated from
**category-exploration friction** (trust/fit/authenticity/information gaps specifically tied to
trying or avoiding a *new* category). Ops friction is retained as background context only; the
analysis, the insight layer, and the chatbot's synthesis all keep the lens on
category-exploration friction, because that's what the company goal and the 8 RQs are actually
about. See the `friction_scope` dimension in
[04_TAXONOMY_DRAFT_v0.md](04_TAXONOMY_DRAFT_v0.md) and the rationale in
[03_THOUGHT_PROCESS.md §7](03_THOUGHT_PROCESS.md).

**Final product form (firm requirement):** Part 1 ships as **one deployed Streamlit app, public
link**, with two parts that go live together:
1. **Analysis dashboard** — charts + theme cards (source split, category × friction, theme
   frequencies, the 8-question rollup with counts + quotes).
2. **"Ask the Reviews" chatbot** — free-text Q&A over the tagged corpus, RAG-grounded, answers
   only from retrieved reviews, always cited. Not optional, not a stretch goal — see §4 and
   [03_THOUGHT_PROCESS.md §8](03_THOUGHT_PROCESS.md).

**LLM provider (pinned):** **Groq**, one API key throughout. Model choice per step, revised during
execution once real rate limits were discovered: **Llama 3.3 70B** for open-coding and the
chatbot's answer generation (both benefit from stronger reasoning); **Llama 3.1 8B Instant** for
at-scale tagging (a bounded-vocabulary classification task, and the 70B model's free-tier budget
of only 100,000 tokens/day turned out to cap out after ~190 tagged reviews — see
[03_THOUGHT_PROCESS.md §9](03_THOUGHT_PROCESS.md)).

## 1. Deliverables checklist

| # | Deliverable | Definition of done |
|---|---|---|
| D1 | Multi-source raw dataset | Play Store + Reddit (posts + comments) reviews mentioning Zepto — App Store attempted and found unavailable via any public method, documented as a platform constraint — no volume cap, pulled to natural exhaustion per source, deduped, in one schema, with source/date/rating preserved |
| D2 | Cleaned corpus | Language-normalized, near-duplicate/spam stripped, non-Zepto noise removed, ready for coding |
| D3 | Taxonomy v1 (grounded) | Tag dimensions + values derived from an open-coding pass on real data, not guessed upfront — **including the `friction_scope` (generic_ops vs. category_exploration) split** |
| D4 | Tagged dataset | Every review scored against taxonomy v1 via structured Groq/Llama-3.3 output, machine-readable (one row/record per review) |
| D5 | Validation report | Tagging accuracy spot-check %, cross-source triangulation table, frequency-threshold rationale |
| D6 | Pattern tables | Theme frequency ranking, category × friction matrix (split by `friction_scope`), behavior-signal breakdown, segment × pain cuts |
| D7 | Insight layer / dashboard | Theme cards (count + source split + quotes), explicitly scope-labeled, mapped to each of the 8 RQs; shipped as **Streamlit dashboard tab 1** |
| D8 | Segment recommendation | 1–2 candidate target segments for Part 3, with the evidence trail that supports them and what's still unproven (handed to Part 2) |
| D9 | **"Ask the Reviews" RAG chatbot** | **Firm.** Embeddings over the tagged corpus + cosine-similarity retrieval + Groq Llama 3.3 generation, answers grounded only in retrieved reviews, every answer cites counts + 2–4 verbatim quotes with source and date, honestly declines when the corpus doesn't support an answer. Shipped as **Streamlit tab 2** |
| D10 | **Deployed public Streamlit app** | Both tabs live at one public URL. This is part of Part 1's Definition of Done, not a follow-on step |
| D11 | Edge-case test log | Every phase's edge cases (see [05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md)) written *before* that phase is built and checked off *after* — no phase is "done" until its edge cases are actually run |

## 2. Phase breakdown

Every phase below has a companion edge-case list in
[05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md). Edge cases are written before the
phase is built and run as a checklist right after — a phase is not marked complete until its
edge-case tests pass (or their failures are documented and accepted knowingly).

### Phase 1 — Gather at scale
- **Sources confirmed:**
  - **Google Play** (`com.zeptoconsumerapp`) via `google-play-scraper`, no auth. ~453,762 total
    written reviews exist per the app's own listing.
  - **Reddit**, via HTML scraping of `old.reddit.com` (see below), across a site-wide search plus
    ~10 targeted subreddits (r/india, r/bangalore, r/developersIndia, r/IndianStreetBets, etc.)
    and 3 sort orders, including comments on every matched post (not just submissions).
  - **Apple App Store — attempted, not available.** The classic public RSS reviews feed
    (`itunes.apple.com/.../rss/customerreviews/.../json`) now returns zero entries for *any* app
    (verified against Instagram too, not just Zepto), and the modern web reviews API
    (`amp-api-edge.apps.apple.com`) requires an authenticated bearer token scoped to the app's own
    App Store Connect account, which is not available to us. This is a real platform-side
    constraint discovered during execution, not a self-imposed limit — documented rather than
    faked around. Zepto's iOS app (`id1575323645`, `com.zeptonow.customer`) shows ~1.01M ratings
    at 4.75★ on the India storefront for context, but individual written reviews aren't
    extractable via any public, unauthenticated method as of this run. **Two-source corpus
    (Play Store + Reddit) going forward**, noted wherever the plan previously assumed three.
  - **Reddit access note:** Reddit's `.json` API endpoints return a bot-check 403 to
    unauthenticated requests (tested with browser-like headers, still blocked) — this appears to
    be current platform-wide behavior, not something specific to this run. The plain HTML search/
    comment pages serve normally, so Reddit data comes from parsing those instead of the JSON API.
    If Reddit developer credentials become available later, this can be swapped for PRAW.
- **Fields captured per record:** `source`, `record_id`, `date`, `rating` (if applicable),
  `text`, `title` (if any), `app_version`/`platform`, `locale`, `upvotes`/`helpful_count` (if any),
  `url`.
- **Volume target: none imposed.** Per explicit instruction, this phase does not stop at a
  pre-set count — each source is pulled until it stops yielding new content (a
  stops-returning-new-results rule, not an arbitrary cap; see the scraper implementations in
  `src/`). The actual final counts achieved are reported plainly once scraping completes — that
  number, whatever it turns out to be, is what establishes analysis at scale, not a target hit.
- **Output:** `data/raw/playstore_raw.jsonl`, `data/raw/reddit_posts_raw.jsonl`,
  `data/raw/reddit_comments_raw.jsonl`, unified into `data/raw/unified_reviews.jsonl`.
- **Risk:** ToS/rate limits on scraping. No Reddit API credentials in use (see access note above);
  if that changes, store keys in `.env` per the brief's instruction — never commit `.env`.

### Phase 2 — Structure with AI
- **Step 2a — Clean:** unify schema, drop exact/near duplicates, filter out reviews that are not
  about Zepto (noise from generic app-store scraping), keep original language field (many reviews
  will be Hindi/Hinglish — do not discard, tag `language` and consider translation before tagging).
- **Step 2b — Open-code a sample:** pull a stratified random sample (~150–300 records across
  sources/ratings) and run an inductive LLM pass asking only "what is this review about, in the
  user's own terms" — no fixed categories yet. Cluster the outputs by hand/eye.
- **Step 2c — Freeze taxonomy v1:** from the clusters in 2b, define the tag dimensions and their
  allowed values (see [04_TAXONOMY_DRAFT_v0.md](04_TAXONOMY_DRAFT_v0.md), now **finalized as v1**
  after a 150-record open-coding pass — filename kept for link stability, content is the grounded
  spec). This step must explicitly
  confirm the **`friction_scope`** split (generic_ops vs. category_exploration vs. ambiguous) has
  clear, testable tie-break rules — this is the dimension the whole analytical lens depends on.
- **Step 2d — Tag at scale:** run every cleaned record through a structured-output prompt against
  taxonomy v1 using **Groq (Llama 3.3)**, temperature 0, JSON schema per record, few-shot examples
  pulled from the open-coding sample (include at least one worked `friction_scope` tie-break
  example per ambiguous pattern found in 2b).
- **Output:** `data/processed/tagged_reviews.jsonl`

### Phase 3 — Find patterns
- Frequency ranking of every tag value (what shows up most, per dimension).
- Category × friction-type cross-tab, produced **twice**: once for `generic_ops` (kept as a short
  background-context table only) and once for `category_exploration` (the primary lens — this is
  the table the rest of the analysis builds on).
- Behavior-signal breakdown (habit-reinforcing vs. exploration-blocking vs. discovery-related
  vs. explicit-avoidance mentions).
- Segment cuts: by rating band, by platform, by recency, by explicit user-type language in the
  text (e.g., "long-time user", "switched from X"), always crossed against the
  category-exploration friction table, not the generic-ops one.
- **Output:** `data/processed/pattern_tables.*` (CSV/notebook)

### Phase 4 — Turn patterns into insights, and ship them
- For every theme that clears the frequency threshold (see Phase 5), build a **theme card**:
  name, one-line definition, `friction_scope` label, count, % of corpus, source split, 3–5
  representative verbatim quotes, and which of the 8 RQs it answers. Ops-friction themes get
  lightweight cards (context only); category-exploration themes get the full treatment.
- **Step 4a — Dashboard:** build the Streamlit **analysis dashboard tab** — charts + theme cards:
  source split, category × friction (exploration-lens primary, ops-lens as a collapsed/secondary
  view), theme frequency ranking, and the 8-question rollup (each RQ with its supporting counts +
  quotes).
- **Step 4b — RAG chatbot:** build the Streamlit **"Ask the Reviews" tab**:
  1. Embed every tagged review (embedding model TBD — see open questions §5).
  2. On each user question, retrieve top-k most similar reviews via cosine similarity.
  3. Send the question + retrieved reviews (verbatim, with their tags/source/date) to **Groq
     (Llama 3.3)**, instructed to answer using **only** the retrieved reviews — no outside
     knowledge, no priors about Zepto.
  4. Every answer must include counts and 2–4 verbatim quotes with source + date.
  5. If retrieval returns nothing relevant or the corpus doesn't support the question (classic
     case: asking about avoidance of a category with ~0 stated-avoidance mentions), the bot says
     so explicitly rather than answering from general knowledge. See
     [03_THOUGHT_PROCESS.md §8](03_THOUGHT_PROCESS.md) for why this is a firm requirement, and
     [05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md) for the specific adversarial
     questions this gets tested against (off-topic questions, prompt injection via review text,
     low-relevance retrieval, corpus-can't-answer cases).
- **Step 4c — Deploy:** ship both tabs as one Streamlit app to a public URL (Streamlit Community
  Cloud by default). The link is part of Part 1's Definition of Done.
- Close with a segment recommendation: which user segment(s) look most promising to target for
  category-exploration nudges, and explicitly flag what's inference vs. what's evidenced.
- **Output:** deployed Streamlit app (public link) + `DOCS/06_INSIGHTS.md` write-up.
  (Note: this deployed app is the *analysis tool* required as Part 1's output form — not to be
  confused with the Part 4 "AI-native MVP," which is a growth-feature product built later on
  whatever target segment Part 3 lands on.)

### Phase 5 — Validate quality
- **Cross-source triangulation:** does a theme show up in ≥2 independent sources, or only one?
  Single-source themes get flagged as weaker evidence.
- **Frequency thresholds:** define a minimum mention count (e.g., ≥1% of corpus or ≥15 mentions,
  whichever is stricter) before a theme is reported as a "pattern" rather than an anecdote.
- **Tagging accuracy spot-check:** human-recode a random ~5–10% sample post-hoc, compare to LLM
  tags, report agreement rate per dimension. If agreement is low on a dimension, revise the
  taxonomy or prompt and re-tag before trusting that dimension's patterns.
- **Output:** `DOCS/07_VALIDATION_REPORT.md`

## 3. Sequencing / dependencies

```
Phase 1 (gather) ──▶ Phase 2 (structure) ──▶ Phase 3 (patterns) ──▶ Phase 4 (insights + ship)
                                │                                        ▲
                                └────────────▶ Phase 5 (validate) ───────┘
```
Validation (Phase 5) runs partly *inside* Phase 2 (taxonomy grounding, accuracy spot-check) and
partly *after* Phase 3 (triangulation, thresholding) — it gates whether Phase 4's insights (and
what the chatbot is allowed to say) are trustworthy enough to ship. See
[02_WORKFLOW.md](02_WORKFLOW.md) for the full diagram, and
[05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md) for the per-phase test gate.

## 4. Out of scope for Part 1
- No interviews (Part 2), no problem-statement write-up (Part 3).
- No Part-4 "AI-native MVP" growth feature — the Streamlit app in this plan is the analysis tool
  required as Part 1's output, a different thing from the Part 4 product.
- No claim that this corpus *measures* avoidance — it only surfaces *stated* avoidance as a lead
  (see the brief's honest scope note, expanded in
  [03_THOUGHT_PROCESS.md](03_THOUGHT_PROCESS.md)).
- No paid/private data sources — public reviews only.
- Chatbot answers only the corpus — it is explicitly not a general Zepto-support bot and must
  refuse questions outside what the retrieved reviews support.

## 5. Open questions to resolve before/while building
- Exact Reddit search terms and subreddit list (needs a first pass to see what returns signal).
- Whether to translate Hindi/Hinglish reviews before or after tagging (leaning: tag directly in a
  multilingual-capable model rather than machine-translate first, to avoid translation-introduced
  distortion — revisit if tagging accuracy on non-English text is poor in the spot-check).
- ~~Final choice of LLM~~ — **resolved: Groq / Llama 3.3**, used for open-coding, at-scale tagging,
  and chatbot generation.
- ~~Embeddings provider~~ — **resolved: local `sentence-transformers` (e.g.
  `all-MiniLM-L6-v2`)**. Groq doesn't serve embeddings; a local model needs no extra API key,
  costs nothing, and is plenty for a review-sized corpus since the LLM reads retrieved reviews
  verbatim rather than depending on perfect ranking precision.
- Streamlit deployment target assumed to be Streamlit Community Cloud (free, public link) unless
  told otherwise.
