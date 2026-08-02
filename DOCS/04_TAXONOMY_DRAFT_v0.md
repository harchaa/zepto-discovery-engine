# Taxonomy — v1 (Grounded, post open-coding)

**Status: FINALIZED for at-scale tagging.** The dimensions below were revised from the v0
hypothesis (kept in the "What changed" section) after running an inductive open-coding pass on a
150-record stratified sample of the real corpus (`data/processed/open_coding_sample.jsonl`,
Groq/Llama 3.3, see `src/open_code_sample.py`). This is what `src/tag_at_scale.py` tags the full
corpus against.

## What changed from the v0 hypothesis, and why (evidence from the 150-record sample)

- **`behavior_signal: stated_avoidance` scope tightened.** The open-coding pass showed the model
  over-applying "avoidance" to generic app-abandonment venting ("I'm never using this app again",
  frustration with a delivery captain dispute, a payment/coupon glitch) — none of which is about
  avoiding a *product category*. `stated_avoidance` is now explicitly restricted to statements
  about avoiding/refusing to buy a specific **product category** (e.g. "I never buy fruits here"),
  not general app dissatisfaction. General "I'm done with this app" sentiment is just
  `sentiment: negative`, no behavior_signal.
- **`friction_type` gained real generic_ops values seen in the data**: `payment_discount_glitch`
  (coupon/"free cash" not applying — appeared multiple times), `order_cancelled_no_consent`,
  `delivery_partner_dispute` (a real sample included a filed police complaint against a delivery
  captain — rare but real, folds under `customer_support`/`delivery_reliability` rather than
  needing its own category given its rarity).
- **Category-exploration friction confirmed rare but real and detectable**: only ~6% (9/150) of
  the random sample showed `friction_scope: category_exploration`-type friction, and only 1/150
  mentioned a new-adjacent category (electronics: a PS5-availability post, no friction). The
  clearest true positive: a Reddit post questioning whether a cosmetics product ("Staze lippies")
  bought on Zepto was authentic, explicitly framed around it being a first-time purchase — exactly
  the `product_authenticity` / `quality_uncertainty_unfamiliar_category` pattern the taxonomy was
  built to catch. This low base rate is *why* at-scale tagging matters more than sampling for this
  project's central question (RQ2) — a small sample catches too few instances to analyze; the full
  corpus is needed to get a workable count of category-exploration friction.
- **`category_mentioned` confirmed mostly absent or staple-only** in random sampling — most
  reviews are generic (no category signal) or about groceries/fresh-produce/dairy. This matches
  the brief's own expectation and is not a taxonomy problem, just the real base rate.

Everything below is the v1 spec used for full-corpus tagging.

## Dimensions

### 1. `category_mentioned` (multi-select)
Which product category the review text is actually about, if any.
`groceries_staples`, `snacks_beverages`, `personal_care`, `beauty`, `baby_care`, `pet_care`,
`pharmacy_health`, `electronics`, `apparel`, `home_kitchen`, `not_category_specific` (e.g., pure
delivery/app/refund complaints with no category signal).

### 2. `sentiment` (single-select)
`positive`, `negative`, `mixed`, `neutral`.

### 3. `friction_scope` (single-select per friction mention) — **the analytical-lens dimension**
Every friction mention gets routed into exactly one bucket before anything else happens to it.
This is what keeps generic operational complaints from drowning out the category-exploration
signal the 8 research questions actually depend on (see
[03_THOUGHT_PROCESS.md §7](03_THOUGHT_PROCESS.md) for full rationale).

- `generic_ops` — friction that would occur regardless of category: delivery timing, damaged/
  wrong item, refund process, app bugs, customer support, general pricing. Kept only as
  background-context frequency; not carried into the category-exploration analysis.
- `category_exploration` — friction specifically tied to *trying or avoiding a new category*:
  trust/authenticity/fit/information gaps for personal_care, beauty, baby_care, pet_care,
  pharmacy_health, electronics, apparel. This is the primary analytical lens.
- `ambiguous` — can't be confidently placed without more context (rare; tracked separately so it
  doesn't silently inflate either bucket).

**Tie-break rule (provisional, to be sharpened after open-coding):** classify by *what the
complaint is actually about*, not by which category the order happened to contain. A damaged
electronics item is `generic_ops` (shipping damage — would happen to any fragile item); a beauty
product that "felt fake / not the real brand" is `category_exploration` (an authenticity/trust
issue specific to buying an unfamiliar category on a grocery-first platform). If a review
explicitly says a bad experience is *why* they won't buy that category again, it's
`category_exploration` regardless of the underlying mechanic, and also gets `stated_avoidance`
under `behavior_signal` below.

### 4. `friction_type` (multi-select, nested under `friction_scope`) — provisional, most likely
to change after open-coding

**Under `generic_ops`:** `delivery_speed`, `delivery_reliability` (missed slots, cancellations),
`damaged_in_transit`, `wrong_item_delivered`, `no_easy_refund`, `pricing_value`, `app_ux_bug`,
`customer_support`, `payment_discount_glitch` (coupon/"free cash"/offer not applying — confirmed
recurring in the sample), `order_cancelled_no_consent`.

**Under `category_exploration`:** `product_authenticity` (fake/counterfeit feel — mainly beauty/
electronics), `quality_uncertainty_unfamiliar_category` (no way to judge quality before buying
something you've never bought here), `sizing_fit_uncertainty` (mainly apparel), `no_info_before_purchase`
(missing detail/reviews/specs needed to trust a first-time category purchase), `trust_vs_specialist_retailer`
(explicit comparison to a category specialist, e.g. Nykaa for beauty, pharmacy chains for
medicine), `return_policy_unclear_for_category`.

**Applies regardless of scope:** `quality_perishables` (rotten/expired produce) — usually
`generic_ops` for routine staple groceries, but reclassify as `category_exploration` if the
review frames it as a reason to distrust a *non-staple* fresh/perishable category (e.g. meat,
specialty produce) they were newly trying.

`no_friction_mentioned` — applies when no friction dimension applies at all (pure praise, neutral
mention, or no text/insufficient signal).

### 5. `behavior_signal` (multi-select) — the dimension most central to the research questions
`habit_repeat_purchase` (explicitly says they always buy the same things),
`discovery_channel_mentioned` (says how they found a product — search, homepage, ad, word of
mouth), `stated_avoidance` (explicitly says they avoid/never buy a specific **product category** —
see [03_THOUGHT_PROCESS.md §6](03_THOUGHT_PROCESS.md) on how this is weighted and its limits.
**Tightened post open-coding: does NOT include general app-abandonment venting** — "I'm never
using this app again" over a delivery/refund complaint is generic negative sentiment, not
category avoidance; reserve this tag strictly for statements like "I never buy fruits/beauty
products/electronics here"), `exploration_attempt_positive` (tried something new, went well),
`exploration_attempt_negative` (tried something new, went badly — likely to reduce future
exploration), `none_detected`.

### 6. `segment_hint` (multi-select, inferred only when text supports it — do not force)
`self_described_tenure` (e.g., "been using this for 2 years"), `platform_ios` /
`platform_android` (from source, not text), `comparison_to_competitor` (mentions Blinkit,
Instamart, BigBasket, etc. — useful for competitive/segment framing), `price_sensitive_language`,
`convenience_seeking_language`.

### 7. Metadata carried from source (not tagged, just retained)
`source`, `rating`, `date`, `language`, `record_id`, `url`.

### 8. `category_class` (derived, not tagged directly — computed from `category_mentioned`)
`core_staple` (`groceries_staples`, `snacks_beverages`) vs. `new_adjacent` (`personal_care`,
`beauty`, `baby_care`, `pet_care`, `pharmacy_health`, `electronics`, `apparel`) vs. `n/a`
(`not_category_specific`, `home_kitchen` pending open-coding — may turn out to be core or
new-adjacent depending on how often it's a repeat vs. first-try purchase). This is a
convenience field for segment cuts (Phase 3) — it is computed, never asked of the tagging model.

## Guardrails for the real taxonomy (v1)

- A value only survives into v1 if it actually recurs in the open-coding sample — this list is a
  seed, not a checklist to confirm.
- Every value needs a one-line definition + a real example quote once v1 is written, so tagging
  prompts and future readers aren't guessing at intent.
- If the open-coding pass surfaces something with no home in this draft (expected — e.g., something
  about dark-store proximity, subscription/membership perception, or festival/seasonal ordering
  spikes), add it. This draft is deliberately not exhaustive.
