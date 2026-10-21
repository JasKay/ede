# Ede — a living Yoruba dictionary

Ede (èdè) means language in Yoruba. The first milestone is a dependable Yoruba corpus explorer with visible provenance and a moderated contribution queue. It is not a generative translator and does not claim that imported data is speaker-verified.

The earlier multilingual ingestion scripts remain in this repository for reference. The root api.py, corpus.py and static/ directory are the active dictionary app. The old nested yoruba-nlp application is not the production entrypoint.

## Run locally

Python 3.12 is recommended. From this repository:

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements-dev.txt
    .venv\Scripts\python tools/bootstrap_data.py
    .venv\Scripts\python -m uvicorn api:app --reload --port 7860

On macOS/Linux, use .venv/bin/python instead. Open http://localhost:7860.

The bootstrap tool retrieves a 635,908-byte compact artifact already published in this project's Hugging Face Space, pinned to revision 1ad68da6eb4e48427c5b3f2358f2e3064f7179e8 and SHA-256 b520e2793cc4b72ccb3cafa00ce04e3685555986ab387ff7de43ebc77f100aa3. It does not download the README's historic full corpus. Missing lookup words are normal; this artifact includes phrases and software-interface text, not a complete Yoruba dictionary. Example buttons are drawn from actual loaded records.

Downloaded corpora, SQLite files, environments and secrets are ignored by Git. No recovered corpus is bundled in source control.

## Data model and search

The API imports Yoruba entries from these files under EDE_DATA_DIR (default ./data):
- ede_yoruba_rich.json
- ede_yoruba_rich_enhanced.json
- ede_master.json
- ede_word_sense.json

Root-level legacy rich/master/compact files are also recognized. Imports are atomic and content-hash tracked. Duplicate normalized English/Yoruba/dialect pairs merge source attribution. Importing a changed file appends/merges records; it does not delete existing entries. Back up the database before bulk imports or schema work.

Use tools/import_corpus.py SOURCE --database data/ede.db for other compatible files.

NFC Unicode normalization and case folding support English or Yoruba search without removing tone marks or underdots. Search performs literal substring matching; English phrases are not inferred word senses or definitions. Search is bounded and paginated.

All imported entries have:
- status: imported_unverified
- confidence: null
- native_speaker_verified: false
- available sources, or explicit artifact-level attribution when upstream sources were lost
- licence: supplied source value or unknown; redistribution_cleared is always false

Legacy confidence numbers, generated examples and inferred grammar labels are not promoted into verified metadata. This release does not generate translations or invent missing words. Multiple meanings and genuinely sourced examples need future curation. Dialect variants remain separate pairs.

## Community contributions and review

Submissions use JSON POST /contribute with word, translation, language="Yoruba", username, dialect, context, source, consent=true. Display name, context and reference are optional. Do not include personal or sensitive information.

A successful response means a SQLite transaction committed. The pending suggestion is not visible in public search. Identical pending suggestions return the existing reference. Submissions are limited to ten per client IP per fixed ten-minute window through a transactional database counter shared across instances. Only a SHA-256 key is stored for throttling, not the raw IP. The UI retains entered text after a failed save. Anonymous contributions are suggestions, not proof of speaker identity.

Set EDE_REVIEW_TOKEN to a long random secret in the server environment. The Our data → Editor review section accepts it in memory only; it is never placed in a URL or browser storage. Editors can list, approve or reject pending suggestions:
- GET /review/contributions?limit=50&offset=0
- POST /review/contributions/{id} with {"approve": true} or {"approve": false}
- Authorization: Bearer <EDE_REVIEW_TOKEN>

Approval labels the pair editor_reviewed, NOT native_speaker_verified. It does not clear its licence or treat contributor context as a verified usage example. This single editor token is an initial moderation mechanism, not a multi-user identity system or a native-speaker credential. Keep it private and rotate it if disclosed. Use an authenticated staff gateway for production editor access where available.

## Deployment and persistence

Dockerfile serves the app on port 7860 and recovers the same pinned corpus during build. On Hugging Face the Space must receive all active files, including corpus.py, static/, tools/, requirements.txt and Dockerfile. GitHub and the Space are separate repositories; a GitHub push alone does not update the Space. Vercel is configured separately through app.py, pyproject.toml and vercel.json. The existing Hugging Face Space is not automatically updated.

EDE_DB_PATH sets the database path. EDE_DATA_DIR sets the import directory. The app uses /data/ede.db when /data exists; otherwise it defaults to ./data/ede.db.

Hugging Face's ordinary container filesystem is ephemeral. When SPACE_ID is present, contribution writes and moderation writes are disabled unless EDE_PERSISTENT_STORAGE=1 is set. Only set this AFTER provisioning durable storage and pointing EDE_DB_PATH to it. The flag does not create or purchase storage. Until then the dictionary remains readable and the UI says submissions are unavailable.

For self-hosted Docker, mount a persistent writable volume at /data, owned/writable by UID 1000. The Docker image runs as that non-root user. Back up the SQLite database with SQLite's online backup API or a consistent stopped-server backup, not by copying an actively written main DB file alone.

This initial backend is intended for one instance / one worker. Multiple replicas, durable distributed throttling, authentication for contributors, abuse controls, review audit identities and a production database migration are subsequent work.

## API

- GET /health: ready or no_data, import-error filenames, contribution availability
- GET /stats: counts from the loaded database, actual example queries, source import summary
- GET /search?q=...&limit=20&offset=0: bidirectional literal corpus lookup
- GET /search-suggestions?q=...: suggestions from loaded English keys
- GET /word-sense?word=... and /translate?word=...: compatibility lookups, returning corpus records
- GET /openapi.json: API schema

The old rule-based chatbot and local-browser voting are not part of the active dictionary. Browser-local votes are not shared review evidence.

## Verify

    .venv\Scripts\python -m pytest -q

Tests cover accent preservation, literal wildcard handling, compact/rich imports, missing and corrupt data, source merging, truthful metadata, restart persistence, atomic writes, moderation authorization, rejection, storage failures, rate limits and concurrent submissions. Test fixtures are synthetic, never bundled as real or verified dictionary data.

## Next milestones

1. Audit original sources and licences; choose a distributable Yoruba seed corpus with reliable attribution.
2. Curate word senses, dialects and real usage examples with Yoruba speakers.
3. Add authenticated contributor/editor accounts and accountable native-speaker verification.
4. Offer licensed, versioned corpus exports and developer API plans after validating demand.
5. Add other African languages with the same evidence and review standards.

## References

- Existing demo: https://huggingface.co/spaces/jaskay/ede-african-nlp
- FastAPI lifespan: https://fastapi.tiangolo.com/advanced/events/
- Hugging Face storage: https://huggingface.co/docs/hub/spaces-storage

### Optional browser verification

With Node and Playwright available, run python tools/browser_smoke.py. Set EDE_NODE to the Node executable, PLAYWRIGHT_MODULE to an installed Playwright module path when it is outside the default module lookup, and BROWSER_EXECUTABLE to an installed Chromium/Chrome executable if needed. The test creates an isolated temporary database, imports the real recovered corpus, and checks search, correction prefill, pending submissions, editor approval, failed-save behavior, safe rendering and mobile layout. It does not write to the live Space or the local working database.
## Word-first browsing

The initial view is Individual words: existing corpus records where both sides are single orthographic tokens. This is a structural classification, not proof that the meaning is verified. Select Phrases & sentences or All corpus records to explore longer material.

Longer records expose separate English and Yoruba token buttons. These preserve combining marks and link to individual-word searches. They do not infer translations by matching token positions. Unsupported words are not inserted into the dictionary.

GET /browse?kind=word&limit=20&offset=0 supports alphabetical browsing. GET /search?q=...&kind=word filters searches; kind can be word, phrase or all. Statistics report word_entries and phrase_entries separately.

## Vercel release

The Ede project belongs to kay-jasanyas-projects and uses FastAPI with an isolated Neon Free PostgreSQL database in London. DATABASE_URL selects the shared PostgreSQL backend; SQLite remains supported for explicit local/testing database paths. No production data is stored on a Vercel function's local disk.

The build recovers the pinned legacy corpus artifact. Imports are transactional, hash-tracked and serialized across concurrent cold starts. Shared PostgreSQL storage retains contributions and approved records across deployments. Source licences remain subject to audit.

Editor credentials are environment-specific. The production editor token is stored locally under EDE_PRODUCTION_REVIEW_TOKEN in the git-ignored .env.local file; it is not public frontend configuration. The corresponding deployed secret is EDE_REVIEW_TOKEN. Do not commit or share these values. Re-pulling development envs can overwrite local-only keys, so preserve the production editor token securely before doing that.

Run the optional database contracts by setting EDE_TEST_DATABASE_URL to a direct/unpooled PostgreSQL connection, then pytest. Tests create and clean up their own random ede_test_ schemas. Never run these contracts with credentials that lack permission to create isolated test schemas. Test representations redact connection strings and tracebacks use the short format.

## Attributed dictionary expansion

The repository includes data/yoruba-lexicon.jsonl: an adapted CC-BY-SA-4.0
snapshot of 3,918 Yoruba headwords and 5,803 lexical senses from English
Wiktionary via Wiktextract / Kaikki, with 1,179 eligible usage examples.
Read NOTICE.md for attribution, source links, extraction dates, licence scope
and selection changes. This does not clear the older corpus's unknown licences.

tools/build_lexicon.py rebuilds this file from a local copy of the pinned
Kaikki source; its SHA-256 is checked before transformation. Canonical forms
preserve source tone marks. Ambiguous canonical forms, proper names,
nonlexical/form-only records and quotations are excluded. Dialect facts are
not inferred from etymologies; original source labels and usage notes remain
visible. No generated usage examples or numeric confidence scores are added.

Each dictionary sense has separate provenance, part of speech, glosses,
source examples and review_status. source_imported is not Ede verification.
Editor review changes only that sense to editor_reviewed or needs_correction;
it never marks a native speaker as having verified it. Existing community
contribution review remains separate.

Authenticated API:
- GET /review/senses?limit=20&offset=0
- POST /review/senses/{id} with {"approve": true} to mark editor review
- POST /review/senses/{id} with {"approve": false} to flag for correction

Both use the same private Bearer editor token as the community queue.
The Our data ? Editor review screen shows dictionary senses alongside
community suggestions. Source changes and flagged meanings should be checked
by a qualified Yoruba speaker; the automated importer is not a substitute
for linguistic review. Review labels do not imply Wiktionary endorsement.

Public GET /attribution serves the data notice. Dictionary text carries its
source licence and credit links per sense; the application code is not
automatically relicensed by this data notice.


## Yoruba dictionary coverage and Swahili sequencing

The sourced headword index groups meanings under exact NFC-normalized Yoruba headwords, preserving tone marks and underdots. Its Unicode ordering is not a Yoruba linguistic collation. Legacy corpus pairs are excluded from this index.

- GET /dictionary/headwords?prefix=...&limit=30&offset=0: bounded, literal prefix browsing.
- GET /dictionary/word?headword=...: all attributed senses for an exact headword, or 404.
- GET /dictionary/coverage: measured examples and review gaps; no invented completeness percentage.
- /?headword=...#word-index: shareable word lookup.

Yoruba work remains: audit source coverage, curate missing meanings and examples, support accountable speaker review, and obtain licensed pronunciation recordings. Do not interpret a large record count as a complete dictionary. Swahili is the next planned language; legacy Swahili ingestion scripts are not a live or verified Swahili dictionary. Its launch needs separately licensed sources, language-specific validation and review, and language-scoped storage/search before importing any data.
