"""Live database contracts run only in isolated, disposable schemas."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from postgres_corpus import PostgresCorpus


class RedactedConnection(str):
    def __repr__(self):
        return "<redacted database connection>"


@pytest.fixture
def remote(tmp_path):
    url = RedactedConnection(os.getenv("EDE_TEST_DATABASE_URL", ""))
    if not url:
        pytest.skip("Set EDE_TEST_DATABASE_URL for real PostgreSQL tests")
    schema = "ede_test_" + uuid4().hex
    with psycopg.connect(url, autocommit=True) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    scoped = RedactedConnection(make_conninfo(url, options=f"-c search_path={schema}"))
    source = tmp_path / "compact.json"
    source.write_text(json.dumps({
        "water": {"t": [{"l": "Yoruba", "w": "omi"}]},
        "greeting": {"t": [{"l": "Yoruba", "w": "e\u0329 ka\u0300a\u0301a\u0301ro\u0329\u0300"}]},
    }), encoding="utf-8")
    try:
        yield PostgresCorpus(scoped), scoped, source
    finally:
        assert schema.startswith("ede_test_")
        with psycopg.connect(url, autocommit=True) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_postgres_import_search_and_word_filters(remote):
    corpus, url, source = remote
    assert corpus.import_file(source) == 2
    assert PostgresCorpus(url).import_file(source) == 0
    assert corpus.search("water")["entries"][0]["translation"] == "omi"
    assert corpus.search("", kind="word")["total"] == 1
    assert corpus.search("", kind="phrase")["total"] == 1
    assert corpus.stats()["word_entries"] == 1
    assert corpus.search("%")["total"] == 0


def test_postgres_shared_contribution_review_and_rate_limit(remote):
    corpus, url, source = remote
    corpus.import_file(source)
    data = {"word": "water", "translation": "omi", "username": "Test", "dialect": "unspecified", "context": "", "source": ""}
    ident = corpus.contribute(data)["id"]
    second = PostgresCorpus(url)
    assert second.contribute(data)["id"] == ident
    second.review(ident, True)
    assert corpus.search("water")["total"] == 1
    assert corpus.search("water")["entries"][0]["status"] == "editor_reviewed"
    assert all(corpus.allow_submission("test-client") for _ in range(10))
    assert second.allow_submission("test-client") is False


def test_postgres_concurrent_imports_are_idempotent(remote):
    corpus, url, source = remote
    def run(_):
        return PostgresCorpus(url).import_file(source)
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert sum(pool.map(run, range(3))) == 2
    assert corpus.stats()["total_entries"] == 2

def test_postgres_sourced_sense_preserves_legacy_licence_and_review_separation(remote):
    from lexicon import import_snapshot, review, queue
    corpus, url, source = remote
    corpus.import_file(source)
    metadata = {"id": "pg-sense", "english": "water", "yoruba": "omi", "pos": "noun",
                "glosses": ["water"], "labels": [], "usage_notes": [], "examples": [],
                "source": "https://en.wiktionary.org/wiki/omi#Yoruba",
                "history": "https://en.wiktionary.org/w/index.php?title=omi&action=history",
                "license": "CC-BY-SA-4.0"}
    lexical = source.parent / "lexical.jsonl"
    lexical.write_text(json.dumps(metadata) + "\n")
    assert import_snapshot(corpus, lexical) == 0
    assert len(queue(corpus)) == 1
    result = PostgresCorpus(url).search("water")["entries"][0]
    assert result["license"] == "unknown"
    assert result["senses"][0]["license"] == "CC-BY-SA-4.0"
    review(corpus, "pg-sense", True)
    result = PostgresCorpus(url).search("water")["entries"][0]
    assert result["senses"][0]["review_status"] == "editor_reviewed"
    assert result["native_speaker_verified"] is False
    assert corpus.stats()["total_entries"] == 2

def test_postgres_headword_index_and_coverage(remote):
    from lexicon import import_snapshot, headwords, word, coverage
    corpus, url, source = remote
    metadata = {"id": "pg-index", "english": "water", "yoruba": "omi", "pos": "noun",
                "glosses": ["water"], "examples": [], "source": "https://en.wiktionary.org/wiki/omi#Yoruba",
                "history": "https://en.wiktionary.org/w/index.php?title=omi&action=history", "license": "CC-BY-SA-4.0"}
    lexical = source.parent / "index.jsonl"
    lexical.write_text(json.dumps(metadata) + "\n")
    import_snapshot(corpus, lexical)
    assert headwords(corpus, "o")["total"] == 1
    assert headwords(corpus, "%")["total"] == 0
    assert word(corpus, "OMI")["senses"][0]["id"] == "pg-index"
    assert coverage(corpus)["headwords_without_examples"] == 1
