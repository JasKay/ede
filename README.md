# Ede 🌍
> *Ede (èdè) means "language" in Yoruba*

 *Current website: https://huggingface.co/spaces/jaskay/ede-african-nlp*

Unified, verified, living corpus infrastructure for African languages.

## The Problem
African languages make up roughly a third of the world's languages but less than 0.02% of NLP training data. The datasets that do exist are scattered across Hugging Face, inconsistently formatted, frequently duplicated, and rarely verified by native speakers. Researchers waste months finding, cleaning, and deduplicating data before they can build anything.

## What Ede Does
Ede solves this by providing a single, unified, deduplicated, source-attributed dataset of African languages accessible via a clean API.

Every entry in Ede knows where it came from, how many native speakers verified it, what domain it belongs to, and whether it has been quality checked.

## Current Stats
- Total unique entries: 696,174
- Languages covered: Yoruba (West Africa), Swahili (East Africa), Tamazight (North Africa)
- Datasets ingested: 5
- Duplicates removed: 1,239,811
- Domains: Conversational, Software-UI, Multi-domain, General
- Scripts supported: Latin, Tifinagh

## API Endpoints
- GET / — Root
- GET /search?q=water&target_language=Yoruba&limit=10 — Search
- GET /search?q=mtu&target_language=Swahili&limit=10 — Search Swahili
- GET /stats — Stats

## Running Locally
1. Clone the repo and cd into it
2. Run: python -m venv venv
3. Run: source venv/bin/activate
4. Run: pip install -r requirements.txt
5. Run ingestion scripts in ingestion/ folder
6. Run: python merge.py
7. Run: python database.py
8. Run: uvicorn api:app --reload
9. Visit http://127.0.0.1:8000/docs

## Languages
| Language | Region | Script | Entries |
| Yoruba | West Africa | Latin | 132,880 |
| Swahili | East Africa | Latin | 563,294 |
| Tamazight | North Africa | Tifinagh | 6,193 |
| Xhosa | Southern Africa | Latin | Coming soon |

## Roadmap
- Add Xhosa (Southern Africa) — in progress
- Add Igbo datasets
- Add Hausa datasets
- **Preserve tonal marks and context-specific meanings in all language data**
- Native speaker verification layer with confidence voting
- Multilingual word sense inventory — search one English word, get results in all 4+ languages with synonyms, homonyms, contexts
- Multilingual translation hub — one English input, simultaneous output in N African languages (text + voice)
- Postgres migration for production
- Expand to 20+ African languages
- Community contributor portal
- Open core business model — free data, paid enterprise API

## The Vision
Ede is not a research project. It is not an NGO. It is infrastructure — the same kind of clean, unified, accessible language infrastructure that English and Mandarin have had for decades, built from the ground up for African languages.

The data is open. Always. The services on top are how Ede sustains itself.

One dataset. One dialect. One voice at a time.

## Contributing
Ede grows through community contribution. If you are a native speaker of any African language and want to help verify, annotate, or contribute data — open an issue or reach out directly.

## Built By
Built by an Ijebu Yoruba native speaker from Ogun State, Nigeria, with a belief that African voices deserve to be heard by AI as clearly as anyone else's.

---
*Started April 2026*
