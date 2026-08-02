# Review Notes Round 2 — after seeing the running app

The engine is strong: scale (203k gathered, 71k tagged), the ops-vs-exploration lens, all 8
questions answered with counts + quotes, honest scope notes, and both the dashboard and the
"Ask the Reviews" chatbot working. Three fixes before this is slide-ready.

## 1. Fix the category-exploration tag — it's muddied by rotten-produce complaints
The app already flags this: `quality_perishables` (rotten/expired produce, 162 mentions) is being
counted inside category-exploration friction and currently *leads* it. That's wrong. Rotten produce
is an ops/quality complaint about a CORE staple category (groceries), not friction about trying a
NEW category. It inflates the headline number and misrepresents the insight.

Do this:
- Run the Phase 5 tagging accuracy spot-check (human-recode ~50-100 rows) as planned.
- Re-tag so `quality_perishables` on a staple category is classified as generic/ops quality, NOT
  category-exploration friction.
- Reserve category-exploration friction for signals genuinely about trying/avoiding a NEW category:
  quality_uncertainty_unfamiliar_category, product_authenticity, no_info_before_purchase,
  sizing_fit_uncertainty, trust_vs_specialist_retailer.
- Re-render the dashboard + the "Q2 / Q5" insights after the re-tag so the counts are honest.

## 2. Add App Store as a third source — it is NOT unavailable
The app says App Store reviews were "found unavailable via any public method." That's incorrect.
The iTunes RSS review feed works with no auth:
`https://itunes.apple.com/in/rss/customerreviews/page={1..10}/id=1575323645/sortby=mostrecent/json`
This returns real, current Zepto App Store reviews (rating, date, title, text), ~500 across 10 pages.
Add it as a source so we have Play Store + App Store + Reddit — three sources strengthens the
cross-source triangulation and the deck's credibility.

## 3. Minor cleanups
- Normalize duplicate tag labels that the LLM produced as variants: collapse
  refund / refund_process, delivery / delivery_issue / delivery_speed where they mean the same,
  quality / quality_authenticity, etc. Clean labels = clean charts.
- Sanity-check sentiment: only ~2,557 negative against 6,000+ 1-2 star reviews suggests the tagger
  under-calls negative. Spot-check and tighten the sentiment prompt.

## Framing note for the deck (important, not a code fix)
The category-crossing signal in reviews is genuinely thin (~0.4% exploration friction, most of it on
groceries; new categories are single digits). That is the survivorship effect we predicted — people
don't review categories they never buy. Do NOT present the 0.4% as "the answer." Frame Part 1 as:
(a) proved at scale that avoidance is largely invisible in reviews, and (b) surfaced the trust /
quality-uncertainty / authenticity hypotheses to test in interviews. Interviews (Part 2) are the
real validation. Framed this way it's a depth strength, not a weakness.
