# Part 1: AI-Powered Discovery Engine — Context & Plan

## Context

This is a Product Management graduation project. I'm playing a PM on the Growth team at **Zepto** (Indian quick-commerce app).

**Company goal:** increase the percentage of Monthly Active Customers who buy from at least one *new* category each month. Most users repeat-buy the same staples (groceries, snacks, essentials) and rarely cross into new categories (personal care, beauty, baby, pet, pharmacy, electronics, apparel).

The overall project has 4 parts: (1) an AI review-analysis engine, (2) user interviews, (3) problem definition, (4) an AI-native MVP deployed to production. **This is Part 1 only.**

**What Part 1 is:** not a machine that spits out canned answers. It's an *analysis capability*. It ingests user feedback at scale, tags it, surfaces patterns and evidence, and makes it explorable. The point is trustworthy analysis that lets us answer the research questions below and pick a target segment. Interviews (Part 2) confirm the findings later.

**Honest scope note (keep it visible):** reviews mostly capture friction people *experienced* on categories they tried (rotten produce, fake-feeling beauty product, damaged electronics, no refunds). When a review directly states *avoidance* ("I never order fruits here because quality is bad"), that's high-value, capture and weight it. Just remember silent non-buyers leave no review, so the corpus under-represents avoidance overall. Treat scraped avoidance as a strong lead; use interviews (Part 2) to measure avoidance properly.

## Research questions the analysis should make answerable
1. Why do users repeatedly buy from the same categories?
2. What prevents users from exploring new categories?
3. How do users discover products today?
4. What role do habits play in shopping behavior?
5. What information do users need before trying a new category?
6. What frustrations emerge repeatedly?
7. Which user segments are more likely to experiment?
8. What unmet needs emerge consistently?

## Plan (5 moves — you own the execution and direction)

1. **Gather at scale.** Pull Zepto feedback from multiple public sources (Play Store, App Store, Reddit) into one dataset.

2. **Structure with AI.** Tag each review so it's countable and sliceable (things like category, sentiment, friction type, behavior signal). Run a first pass on real data, then finalize the taxonomy from what actually appears. Do not hard-freeze labels upfront.

3. **Find patterns.** Frequency-ranked themes, a category-by-friction view, behavior signals, and which user groups show which pain.

4. **Turn patterns into insights.** Back each theme with counts and real quotes, and make it explorable. This is the layer that makes the 8 questions answerable and points to a target segment.

5. **Validate quality.** Cross-source triangulation, frequency thresholds, and a spot-check of tagging accuracy. Interviews are the final validation.

## Notes
- Use real data, real counts, real quotes. Nothing fabricated.
- Keep any API keys in `.env`, never committed.
