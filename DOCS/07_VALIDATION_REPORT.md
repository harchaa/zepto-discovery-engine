# Phase 5 — Validation Report

Status: **tagging concluded at 69,158 tagged / 203,923 gathered (34%)**, of which **6,252 were
substantive LLM judgment calls** (the rest deterministic zero-cost auto-tags — see
[03_THOUGHT_PROCESS.md §9](03_THOUGHT_PROCESS.md)). Stopped short of the original 20,000-record
substantive target on 2026-08-02 after two Groq API keys both hit their daily token quota in the
same day; the sample was judged sufficient to proceed rather than wait multiple days for a third
key's budget to regenerate. This report documents what was actually validated, what was corrected,
and what remains an open limitation — per the brief's instruction that validation be honest about
weak points, not just a checkbox.

## 1. Corpus scale

| Source | Gathered | Tagged (any) | Tagged (substantive/LLM) |
|---|---|---|---|
| Play Store | 163,539 | 68,072 | 5,906 |
| App Store | 450 | 55 | 6 |
| Reddit | 39,934 | 1,031 | 340 |
| **Total** | **203,923** | **69,158** | **6,252** |

App Store and Reddit are proportionally under-tagged relative to Play Store simply because
tagging draws a random sample from whatever's cleaned and eligible, and Play Store dominates the
corpus by raw volume — not a deliberate exclusion. If tagging resumes later, this naturally
self-corrects since sampling stays randomized (see `src/tag_at_scale.py`).

## 2. Tagging accuracy — two human spot-check rounds

**Round 1 (20 records, stratified across friction_scope/behavior_signal), pre-fix:**
- `friction_scope: category_exploration` was over-applied to routine ops/quality complaints on
  staple categories — ~6 of 8 sampled category-exploration tags looked wrong, most visibly via
  `quality_perishables` (rotten produce) driving the count on its own.
- `stated_avoidance` was applied to complaints with no actual avoidance language — ~2 of 3
  sampled looked wrong.
- **Fix:** `src/correct_tags.py` deterministically re-derives `friction_scope` from
  `friction_type`/`category_mentioned` (only counts as category_exploration if the friction_type
  itself signals category-newness, or a new-adjacent category is mentioned) and strips
  `stated_avoidance` lacking an explicit avoidance phrase. `src/tag_at_scale.py`'s prompt was
  tightened with explicit pass/fail examples for both dimensions.
- **Result of round 1 fix:** 220 friction_scope corrections, 296 stated_avoidance removals across
  the then-72,682 tagged records.

**Round 2 (20 fresh records tagged under the corrected prompt):**
- The staple-category mistag was gone. Two new issues surfaced instead:
  - The avoidance phrase list was too narrow, wrongly stripping real avoidance statements phrased
    as "don't ever order" or "stopped using it."
  - Reddit posts merely name-dropping "Zepto" without being about an actual shopping experience (a
    tech-interview-topics joke, a stock-market comment) were still getting a friction tag, because
    `off_topic_flag` (set during cleaning) only checks whether the word "zepto" appears, not
    whether the post is about the shopping experience.
- **Fix:** expanded the avoidance phrase list; added `looks_off_topic()`, a Reddit-only check that
  resets friction tags to `none` if the text contains none of a broad commerce-keyword list.
- **Result of round 2 fix:** scanning the *full* corpus (not just the 20-record sample) found and
  corrected 57 more off-topic mistags beyond the original sample. One over-correction was caught
  in turn — a genuine on-topic personal-care question got reset — and the fix was made
  self-healing (pre-correction tags preserved so a keyword-list refinement can restore a wrongly-
  reset record) rather than patched as a one-off.
- Full detail: [05_EDGE_CASES_AND_TESTING.md](05_EDGE_CASES_AND_TESTING.md) Phase 5 section.

**What this means for trust in the numbers:** two rounds of spot-check both found real, fixable
problems, and both fixes were themselves re-checked rather than assumed correct on the first pass.
No round-3 spot-check has been run yet on the ~6,252-record substantive sample as a whole — the
corrections are principled and evidence-based, but a third round (ideally by someone other than
whoever wrote the fix) would strengthen confidence further before treating theme counts as
final for any external-facing claim.

## 3. Frequency thresholds

A friction_type only counts as a "confirmed theme" (not just an anecdote) if it appears in at
least `max(15, 1% of friction-bearing records)` — currently **≥25 mentions** out of 2,487
friction-bearing records. This basis was itself corrected mid-project: the threshold originally
scaled against the *entire* tagged count (including the ~63,000 zero-cost auto-tagged trivial
reviews, which are always `friction_scope: none` by construction), which diluted the threshold and
wrongly zeroed out real themes. Now scaled against only the friction-bearing subset.

Confirmed category-exploration themes at the current sample size:

| Friction type | Count |
|---|---|
| quality_uncertainty_unfamiliar_category | 187 |
| quality_perishables (paired with a genuine exploration signal, not standalone) | 183 |
| product_authenticity | 159 |
| customer_support | 41 |
| app_ux_bug | 29 |
| trust_vs_specialist_retailer | 29 |
| damaged_in_transit | 28 |

`quality_perishables` still appears at meaningful volume here, but — unlike before the round-1
fix — it's no longer classifying a record as category_exploration *by itself*; these 183
mentions co-occur with a genuine exploration-signal friction_type on the same record (e.g., "the
produce was rotten and I don't trust buying fresh items from an app I don't know"). That's a real,
defensible pattern, not the earlier bug.

**Stated-avoidance leads:** 91, explicitly labeled throughout the dashboard/docs as leads to test
in interviews, not a measured avoidance rate (see the brief's honest scope note).

## 4. Cross-source triangulation

With Play Store, App Store, and Reddit all represented in the tagged sample (see §1), the themes
above are drawn predominantly from Play Store simply due to its share of the tagged sample - App
Store (6 substantive tags) and Reddit (340) are too thin at this sample size to independently
confirm or contest the Play Store-driven theme ranking yet. This is a real limitation of stopping
tagging at 31% of target: cross-source triangulation (do independent sources agree a theme is
real?) needs enough tagged volume *per source*, not just overall, and App Store in particular
hasn't reached that bar. If tagging resumes, prioritizing sample balance across sources (not just
overall count) would strengthen this specific check.

## 5. Known limitations carried forward

- **Tagging is a 31%-of-target sample**, not a census — reported as such everywhere (dashboard,
  README, this doc), never presented as complete.
- **Avoidance-phrase detection is English-only** — non-English (Hindi/Hinglish) avoidance
  statements aren't caught by the keyword-based correction pass, a known gap from the taxonomy's
  original design (see [04_TAXONOMY_DRAFT_v0.md](04_TAXONOMY_DRAFT_v0.md)).
- **Off-topic detection is a keyword heuristic**, not perfect — it trades a small false-positive
  rate (rare on-topic posts lacking a commerce keyword) for catching a much larger set of true
  off-topic content, and is self-healing by design if the keyword list needs future refinement.
- **App Store and Reddit are under-represented in the substantive tagged sample** relative to
  their share of the gathered corpus, purely due to random sampling order, not exclusion.
- **No round-3 human spot-check yet** on the corrected pipeline's output as a whole sample.
