# Review Notes — 3 fixes before execution

The plan docs are strong (analysis-capability framing, inductive taxonomy, triangulation, spot-check,
avoidance handling). Three changes before running the pipeline:

## 1. Keep the lens on category-crossing, not generic app complaints
The friction taxonomy is mostly universal quick-commerce gripes (late delivery, no refund, support
bots, wrong item). Those will dominate the counts in any Zepto corpus, but this project is about
**why users don't buy from new categories**, not overall app satisfaction. If the analysis isn't
guarded, the output becomes "Zepto has delivery problems," which is off-target for the growth goal.

Do this:
- In pattern analysis, explicitly split friction into **generic ops friction** vs.
  **category-exploration friction** (trust/quality/authenticity/uncertainty tied to trying a *new*
  category: perishables quality, fake-feeling beauty/electronics, apparel fit, pharmacy sensitivity,
  no in-app info to judge an unfamiliar product).
- Lead the insights with category-exploration friction. Report generic ops friction as context only.
- Every theme should connect back to the goal metric: % of MACs buying from a new category.

## 2. Deployment is a firm deliverable, not "if time allows"
The assignment requires a testable link to the workflow. Make these hard deliverables:
- A deployed **Streamlit app** (public link) with: a pipeline/how-it-works view, an insights
  dashboard (charts: source split, category × friction, theme frequencies), and an
  **"ask the reviews" chatbot** over the corpus (Groq, Llama 3.3).
- The chatbot answers with real quotes + counts pulled from the tagged dataset, not model priors.
- Treat the public link + the one explainer slide as part of Definition of Done.

## 3. Set a concrete volume target
Replace "as much as sources allow" with a stated target so the deck has a credible number:
- ~3,000 Play Store + ~500 App Store + Reddit posts.
- Report the final total analyzed prominently (strong past submissions cited 300–3,000+).

Everything else in the plan stays as-is.
