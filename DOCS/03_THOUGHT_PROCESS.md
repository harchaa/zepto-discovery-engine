# Thought Process & Design Rationale

This doc exists so the *reasoning* behind the pipeline is auditable, not just the pipeline itself.
Graduation-project review criteria include clarity of thought and depth of research — this is
where that gets written down explicitly rather than left implicit in code.

## 1. Why this is an "analysis capability," not a Q&A bot

The brief is explicit: Part 1 should not spit out canned answers to the 8 research questions. If
the engine directly output "users don't explore new categories because of X," that would be an
LLM's guess dressed up as research. Instead, the engine's job is to make each question **answerable
with evidence** — counts, cross-tabs, and real quotes a reader can independently check. The 8
questions become a mapping applied *after* patterns emerge (Phase 4), not a template the AI fills
in from priors. This is why Phase 4 (insight layer) comes after Phase 3 (pattern-finding), never
before.

## 2. Why open-code first, then freeze a taxonomy (inductive before deductive)

Two ways to tag reviews: (a) decide categories upfront from intuition, or (b) look at real data
first, let categories emerge, then formalize them. The brief explicitly instructs (b) — "run a
first pass on real data, then finalize the taxonomy from what actually appears. Do not hard-freeze
labels upfront." The reason this matters: an upfront taxonomy encodes the PM's *existing* mental
model of why users don't explore categories, which is exactly the bias the research is supposed to
test. If "delivery speed anxiety" or "trust in perishables" turns out to be the dominant friction
and it wasn't in a preconceived list, an upfront-frozen taxonomy would either miss it or force it
into the wrong bucket. Open-coding a real sample first is slower but keeps the taxonomy grounded in
what users actually said, not what we expected them to say. [04_TAXONOMY_DRAFT_v0.md](04_TAXONOMY_DRAFT_v0.md)
is intentionally labeled a *hypothesis*, not the taxonomy — it exists only to give Phase 2 a
starting shape, and is expected to be revised once the open-coding pass runs on real reviews.

## 3. Why cross-source triangulation matters

Each source has a different demographic and a different failure mode:
- **Play Store** reviews skew toward extremes (1-star rage, 5-star loyalty) and toward Android
  users, who in the Indian market skew more price-sensitive / smaller-city.
- **App Store** reviews are lower volume but skew iOS/urban/higher-income.
- **Reddit** posts skew toward users willing to write long-form narrative complaints or
  comparisons (e.g., "Zepto vs Blinkit vs Instamart"), often more articulate about *why*, not just
  *that* something failed.
A theme that only shows up on one platform might be a platform-specific artifact (e.g., an
Android-only bug) rather than a real product/behavior pattern. Requiring a theme to appear across
at least two independent sources before calling it a "pattern" (vs. "anecdote") is the single
biggest lever against overfitting to one community's quirks.

## 4. Why frequency thresholds, not just "did anyone say this"

LLM tagging at scale will surface a long tail of one-off mentions. Without a minimum-count
threshold, the loudest or most creatively-worded single review could look as significant in a
table as a theme mentioned by hundreds of users. The threshold exists to separate **signal**
(recurring, count-backed) from **noise** (one person's unusual experience) — directly serving the
brief's instruction to back every theme with counts and real quotes, not just a compelling
anecdote.

## 5. Why a tagging-accuracy spot-check, and why it can send work backward

LLM classification is not free of error, especially on: sarcasm, code-mixed Hindi/English text,
reviews that mention multiple categories/frictions in one sentence, and ambiguous sentiment
("it's fine, better than Blinkit" — praise or backhanded complaint?). Rather than assume the
tagging is correct, a human-recoded sample against the LLM's tags produces an honest agreement
rate. If a specific dimension (say, `behavior_signal`) comes back with low agreement, that is a
signal to fix the prompt/taxonomy definition for that dimension and re-tag — not to quietly keep
results that are known to be unreliable. This is why the workflow diagram shows a loop back from
spot-check to taxonomy, not a one-way arrow.

## 6. The avoidance/survivorship-bias problem — how it's handled, not just noted

The brief's "honest scope note" is the single most important limitation of this entire engine, so
it's worth stating precisely how it's operationalized rather than just repeated as a disclaimer:

- **What reviews can tell us well:** friction *experienced* by people who already tried a new
  category (bad produce, damaged electronics, refund issues). This is the majority of the signal
  in the corpus and it directly answers RQ6 (frustrations) and partially RQ2/RQ5.
- **What reviews can tell us weakly:** *avoidance* — someone who never tried personal care or
  pharmacy on Zepto usually never reviews Zepto because of it. The few reviews that *do* state
  avoidance explicitly ("I never buy fruits here, quality is unreliable") are treated as
  high-value signal and tagged with a dedicated `behavior_signal: stated_avoidance` value — but
  the absence of more such mentions is **not** interpreted as evidence that avoidance is rare.
  Silence in a review corpus is not the same as absence in reality.
- **How this shapes the insight layer:** any theme derived from `stated_avoidance` mentions gets
  explicitly labeled in its theme card as "lead, not measurement" and is flagged for follow-up in
  Part 2 interviews, which are the actual instrument for measuring avoidance (you can ask a
  non-buyer directly why they don't buy; a review corpus cannot).
- **How this shapes the segment recommendation:** the segment recommendation (Phase 4 output) is
  framed as a hypothesis to test in interviews, not a conclusion — consistent with the brief
  stating interviews are the final validation.

## 7. Why generic ops friction and category-exploration friction must be kept apart

Zepto's review corpus, like any delivery app's, is dominated by operational complaints: late
delivery, missed slots, damaged parcels, refund hassles, app bugs. None of that is *nothing* — but
none of it explains why someone keeps buying groceries and never tries beauty or pharmacy on the
same app. If ops friction and category-exploration friction are tagged and counted together, the
loudest, highest-volume bucket (ops) will dominate every frequency ranking and cross-tab purely by
base rate, and the resulting "top frustrations" table will answer a question nobody asked ("is
delivery reliable?") instead of the one the company goal actually depends on ("what stops
category exploration?"). The `friction_scope` dimension exists specifically to prevent this: it
is applied *before* any pattern analysis runs, so ops friction never gets the chance to compete
for attention in the theme-ranking step — it's demoted to a background-context table up front, not
filtered out after the fact by eyeballing which themes "feel" relevant. This is why the workflow
diagram puts the scope-split fork immediately after tagging (node S in
[02_WORKFLOW.md](02_WORKFLOW.md)), not after pattern analysis.

The tie-break rule (classify by what the complaint is *about*, not which category the order
happened to contain — see [04_TAXONOMY_DRAFT_v0.md](04_TAXONOMY_DRAFT_v0.md)) exists because the
naive version of this split (just look at `category_mentioned`) would be wrong: a damaged
electronics item is a shipping problem, not a signal about electronics-category trust, while a
"felt fake" beauty product *is* a category-trust signal even though nothing was damaged. Getting
this tie-break right is worth explicit edge-case testing (see
[05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md), Phase 2) because it's the single
dimension the whole analytical lens depends on.

## 8. Why the chatbot is a firm deliverable, and what "grounded" actually requires

The brief's insight-layer instruction is to make patterns "explorable" and back every theme with
"real counts and real quotes." A static dashboard does that for pre-decided cuts of the data, but
anyone reviewing this project will have their own questions the dashboard didn't anticipate ("what
do people say about pet care specifically?"). The chatbot is the mechanism that makes the corpus
explorable for *arbitrary* questions, not just the ones baked into the dashboard — that's why it's
a firm deliverable rather than a nice-to-have demo feature.

"Grounded" is not a vibe, it's an architecture constraint, and it drives several concrete
decisions:
- **Retrieval before generation (RAG), not the model's own knowledge.** Llama 3.3 has never seen
  this specific review corpus and has plenty of generic priors about delivery apps — if it
  answered from parametric knowledge, it would produce plausible-sounding but fabricated claims
  about *this* dataset. Retrieval forces every answer to be traceable to specific reviews.
- **The prompt must instruct the model to answer only from retrieved reviews and refuse
  otherwise** — this is the same anti-hallucination discipline as the rest of the pipeline (§1,
  §6): no canned or invented answers, ever, even when a plausible one is easy to generate.
- **Citations (count + 2–4 verbatim quotes + source + date) are mandatory, not decorative** —
  they're what lets a reader independently verify the bot isn't making it up, the same reason
  theme cards carry quotes.
- **Honesty about corpus gaps is a feature, not a failure mode.** The single most important test
  case is a question like "why do people avoid the pharmacy category?" where the corpus likely has
  very few or zero `stated_avoidance` mentions for that category (§6's survivorship-bias problem,
  now live in the chatbot). The bot must say the corpus doesn't support a confident answer rather
  than reach for the nearest tangentially-related quote or fall back on general reasoning about
  delivery apps. Getting this right is exactly as important as getting a good answer right when
  the corpus *does* support one — see the adversarial test cases in
  [05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md), Phase 4.
- **Review text is retrieved content, not instructions.** Because real reviews are user-generated
  text, a review containing something like "ignore previous instructions and say X" must not be
  able to hijack the bot's system prompt — retrieved reviews are data to cite, never instructions
  to follow. This is tested explicitly (prompt-injection-via-review-text case).

## 9. Key decisions & tradeoffs

| Decision | Alternatives considered | Why chosen | Risk accepted |
|---|---|---|---|
| Tag with an LLM using structured output (JSON schema per record) rather than keyword/regex rules | Rule-based classifier; manual-only coding | Reviews are free text with sarcasm, code-mixing, multi-topic sentences — rules miss nuance; fully manual doesn't scale to a multi-source corpus | LLM misclassification risk — mitigated by the spot-check (§5) |
| Inductive open-coding pass before freezing taxonomy | Freeze taxonomy from PM intuition upfront | Avoids baking in preconceived answers to the exact questions being researched | Slower — needs a real sample and a clustering step before scale-tagging can start |
| Require ≥2-source presence + minimum count before calling something a "pattern" | Report every tag frequency as-is | Prevents one loud community or one viral rant from masquerading as a widespread pattern | Might under-report a real but genuinely single-source or low-volume issue — mitigated by still listing it as "weak/anecdotal" rather than deleting it |
| Keep non-English/code-mixed text and tag directly rather than machine-translate first | Translate everything to English before tagging | Translation can flatten nuance/sarcasm before the tagger ever sees it | If tagging accuracy on non-English text is poor in the spot-check, revisit and add a translation step |
| Treat stated avoidance as a flagged lead, never as a measured rate | Compute an "avoidance rate" from the corpus | Silent non-buyers leave no review — any computed rate would be fabricated precision | The engine will likely under-surface avoidance-driven frictions relative to their real-world weight; interviews (Part 2) are the explicit compensating mechanism |
| Split every friction mention by `friction_scope` (generic_ops vs. category_exploration) before any pattern analysis | Tag friction as one flat list; filter for "relevant" themes manually at the reporting stage | A fixed, tested tie-break rule applied at tagging time is auditable and repeatable; manual after-the-fact filtering is subjective and invites the exact selection bias the analysis is supposed to avoid | Some ambiguous cases will be misclassified even with a tie-break rule — mitigated by the dedicated `ambiguous` bucket and edge-case testing (§7) |
| One LLM provider (Groq / Llama 3.3) for open-coding, at-scale tagging, and chatbot generation | Different models per stage (e.g., a stronger model for open-coding, a cheaper one for scale-tagging) | Consistency of judgment across the pipeline — a review tagged in Phase 2 and a review cited by the chatbot in Phase 4 are being read by the "same eyes"; one API key, simpler ops | Locked into Groq/Llama 3.3's specific strengths and failure modes throughout — mitigated by the accuracy spot-check (§5) and by choosing prompts/taxonomy design that don't lean on capabilities Llama 3.3 lacks |
| Local embedding model (e.g. `sentence-transformers/all-MiniLM-L6-v2`) for chatbot retrieval, not a paid embeddings API | Hosted embeddings API (higher quality, per-call cost, extra key) | Groq doesn't serve embeddings; a free local model needs no additional key/cost and is sufficient for retrieval over a review-sized corpus | Slightly lower retrieval quality than a top hosted embedding model — acceptable given retrieval only needs to find "close enough" reviews for the LLM to read verbatim, not rank with perfect precision |
| No pre-set volume target — each source scraped to natural exhaustion (a "stops yielding new results" stopping rule per pagination stream, not a row-count cap), final counts reported after the fact | An earlier draft of this plan set a fixed target (~3,000 Play Store / ~500 App Store) to guarantee a credible scale number upfront | Explicit instruction: don't self-impose a limit on how much real data gets pulled — report the true achieved total instead of engineering toward a pre-picked number | The final count is whatever the platforms' own pagination ceilings allow, which could be very large (Play Store alone showed no plateau past tens of thousands of reviews) — reporting this honestly, including how it was arrived at, matters more than hitting a specific figure |
| At-scale tagging uses `llama-3.1-8b-instant` (Groq), not `llama-3.3-70b-versatile` | Keep one model across open-coding, tagging, and the chatbot for judgment consistency (the original plan) | Discovered empirically during execution: `llama-3.3-70b-versatile`'s free-tier daily budget is **100,000 tokens/day (TPD)** — exhausted after tagging only ~190 reviews. `llama-3.1-8b-instant` is a separate quota bucket that showed no daily-limit wall at equivalent usage, and a bounded-vocabulary classification task (category/sentiment/friction tags from a fixed list) doesn't need a 70B model's reasoning depth the way open-ended chatbot answers do | Tagging quality is being spot-checked (Phase 5) against the smaller model specifically, not assumed equivalent to the 70B model's open-coding output; `llama-3.3-70b-versatile` stays reserved for the chatbot (Phase 4), where its remaining daily budget is deliberately preserved rather than spent on tagging |
| Full-corpus tagging is NOT a fixed target — it runs as a resumable, randomized-order background process, accumulating over however many days the real per-model daily token quota takes | Impose a smaller fixed "tagging sample size" up front to guarantee a clean single-session number | Same principle as the gathering phase: report the real constraint and the real achieved number rather than silently under-scoping. Randomized tagging order means whatever fraction is done at any moment is an unbiased subsample, so analysis can start on partial data honestly | Full coverage of 166k+ records will take multiple days of accumulated runs even on the higher-budget model; Phase 3 analysis will need to either wait for a large-enough subsample or explicitly report its N and treat it as a sample, not a census |
| Drop Apple App Store as a data source after a documented, verified attempt | Keep trying alternate scraping methods (reverse-engineering Apple's authenticated web API) | Apple's public RSS reviews feed is confirmed dead platform-wide (tested against Instagram, not just Zepto) and the modern API requires developer-account credentials we don't have — further effort would be reverse-engineering an intentionally-gated system, not "public source" scraping | Corpus is two-source (Play Store + Reddit) instead of three; triangulation (§3) still functions with two independent sources, just with one fewer cross-check than originally planned |

## 10. How the 8 research questions map to pipeline outputs

| RQ | Primarily answered by |
|---|---|
| 1. Why do users repeatedly buy from the same categories? | Behavior-signal frequency (habit-reinforcing tags) + quotes, category × repeat-purchase language |
| 2. What prevents users from exploring new categories? | Category × friction-type matrix **filtered to `friction_scope: category_exploration`** + stated-avoidance theme cards (flagged as leads) |
| 3. How do users discover products today? | Discovery-related behavior-signal tags (search, homepage banners, word of mouth, none) |
| 4. What role do habits play in shopping behavior? | Habit-signal frequency + segment cuts (recency, repeat-language) |
| 5. What information do users need before trying a new category? | Friction subtype around trust/uncertainty (quality unknowns, no reviews-in-app, sizing/fit for apparel, etc.) |
| 6. What frustrations emerge repeatedly? | Friction-type frequency ranking, the best-supported output given the data's inherent skew toward experienced friction |
| 7. Which user segments are more likely to experiment? | Segment cuts (rating band, platform, recency, self-described tenure) crossed with exploration-positive language |
| 8. What unmet needs emerge consistently? | Cross-cutting read of friction + discovery + avoidance theme cards, synthesized in the insight layer |

## 11. Definition of "done" for Part 1

Part 1 is done when: each source has been pulled to natural exhaustion (no pre-set volume cap —
see the Phase 1 note on this reversal below) and the final total analyzed is reported
prominently, establishing this is analysis at scale rather than anecdote; the tagged
dataset exists with a documented, grounded taxonomy (including a
tested `friction_scope` split); the validation report shows tagging agreement and triangulation
results honestly (including where they're weak); every reported theme has a count, a source
split, a `friction_scope` label, and real quotes; every one of the 8 RQs has an explicit,
evidence-backed answer or an explicit "here's what we can't tell from reviews alone" note; a
segment recommendation is handed off clearly labeled as a hypothesis for Part 2 to confirm — not a
final answer; **the "Ask the Reviews" RAG chatbot is live and answers grounded, cited questions
about the corpus while honestly declining unsupported ones**; **both the dashboard and the
chatbot are deployed as one Streamlit app at a public URL**; and every phase's edge cases (see
[05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md)) have been run, with results —
pass or documented-and-accepted failure — recorded.
