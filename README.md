# Ede 🌍
> *Ede (èdè) means "language" in Yoruba*

Unified, verified, living corpus infrastructure for African languages.

## The Problem
African languages make up roughly a third of the world's languages but less than 0.02% of NLP training data. The datasets that do exist are scattered across Hugging Face, inconsistently formatted, frequently duplicated, and rarely verified by native speakers. Researchers waste months finding, cleaning, and deduplicating data before they can build anything.

## What Ede Does
Ede solves this by providing a single, unified, deduplicated, source-attributed dataset of African languages accessible via a clean API.

Every entry in Ede knows where it came from, how many native speakers verified it, what domain it belongs to, and whether it has been quality checked.

## Current Stats
- Total unique entries: 132,880
- Languages covered: Yoruba
- Datasets ingested: 3
- Duplicates removed: 687,405
- Domains: Conversational, Software-UI, Multi-domain

## API Endpoints
- GET / — Root
- GET /search?q=water&target_language=Yoruba&limit=10 — Search
- GET /stats — Stats

## Running Locally
1. Clone the repo and cd into it
2. Run: python -m venv venv
3. Run: source venv/bin/activate
4. Run: pip install -r requirements.txt
5. Run ingestion scripts: ingest_0xnu.py, ingest_helsinki.py, ingest_menyo.py
6. Run: python merge.py
7. Run: python database.py
8. Run: uvicorn api:app --reload
9. Visit http://127.0.0.1:8000/docs

## Roadmap
- Add Igbo datasets
- Add Hausa datasets
- Native speaker verification layer
- Front end interface
- Postgres migration for production
- Expand to 20+ African languages
- Community contributor portal

## The Vision
Ede is not a research project. It is not an NGO. It is infrastructure — the same kind of clean, unified, accessible language infrastructure that English and Mandarin have had for decades, built from the ground up for African languages.

One dataset. One dialect. One voice at a time.

## Contributing
Ede grows through community contribution. If you are a native speaker of any African language and want to help verify, annotate, or contribute data — open an issue or reach out directly.

## Built By
Built by an Ijebu Yoruba native speaker from Ogun State, Nigeria, with a belief that African voices deserve to be heard by AI as clearly as anyone else's.

---
*Started April 2026*
