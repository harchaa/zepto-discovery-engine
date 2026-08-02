# app/ — Streamlit app (Phase 4)

Single deployed Streamlit app with two tabs:
1. **Analysis dashboard** (`streamlit_app.py`) — theme cards, cross-tabs, 8-question rollup, all
   reading from `data/processed/pattern_tables.json` + `app_export.jsonl`.
2. **"Ask the Reviews"** (`chatbot.py`) — embeddings + cosine retrieval over
   `data/processed/embeddings.npz`, then Groq Llama 3.3 answers grounded only in retrieved
   reviews, always cited.

Run locally: `streamlit run app/streamlit_app.py` (needs `GROQ_API_KEY` in `.env`).

See [../DOCS/01_PLAN.md](../DOCS/01_PLAN.md) Phase 4 and
[../DOCS/03_THOUGHT_PROCESS.md §8](../DOCS/03_THOUGHT_PROCESS.md) for why the chatbot is built the
way it is.
