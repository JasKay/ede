import json
import sqlite3
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from api import create_app
from corpus import Corpus


@pytest.fixture
def paths(tmp_path):
    data = tmp_path / "corpus"
    data.mkdir()
    fixture = {
        "water": {"word": "water", "t": [{"l": "Yoruba", "w": "omi", "c": 0.99, "f": 10},
                                        {"l": "Swahili", "w": "maji"}]},
        "greeting": {"word": "greeting", "t": [{"l": "Yoruba", "w": "ẹ káàárọ̀", "c": 0.9}]},
    }
    # Synthetic fixture only: this is not shipped as verified language data.
    (data / "ede_word_sense.json").write_text(json.dumps(fixture), encoding="utf-8")
    return tmp_path / "dictionary.db", data


@pytest.fixture
def client(paths):
    database, data = paths
    with TestClient(create_app(database, data, review_token="test-editor-token", writable=True)) as client:
        yield client


def suggestion(**overrides):
    return {"word": "test word", "translation": "test translation", "language": "Yoruba",
            "username": "Test contributor", "dialect": "Ijebu", "context": "Test context",
            "source": "Test reference", "consent": True, **overrides}


def test_real_counts_and_explicitly_unknown_metadata(client):
    stats = client.get("/stats").json()
    assert stats["total_entries"] == 2
    assert stats["languages"] == {"Yoruba": 2}
    assert stats["native_speaker_verified"] == 0
    result = client.get("/search", params={"q": "water"}).json()["entries"][0]
    assert result["translation"] == "omi"
    assert result["confidence"] is None
    assert result["status"] == "imported_unverified"
    assert result["native_speaker_verified"] is False
    assert result["license"] == "unknown"
    assert result["redistribution_cleared"] is False
    assert "upstream source not recorded" in result["sources"][0]


def test_yoruba_search_preserves_tones_and_unicode_equivalence(client):
    query = unicodedata.normalize("NFD", "ẹ káàárọ̀")
    result = client.get("/search", params={"q": query}).json()
    assert result["total"] == 1
    assert result["entries"][0]["translation"] == "ẹ káàárọ̀"
    assert client.get("/search", params={"q": "e kaaaro"}).json()["total"] == 0


def test_literal_wildcards_missing_words_and_bounded_pagination(client):
    assert client.get("/search", params={"q": "%"}).json()["total"] == 0
    assert client.get("/search", params={"q": "' OR 1=1 --"}).json()["total"] == 0
    assert client.get("/search", params={"q": "absent"}).json()["entries"] == []
    assert client.get("/search", params={"q": "water", "offset": 1}).json()["entries"] == []
    assert client.get("/search", params={"q": "water", "limit": 1000}).status_code == 422
    assert client.get("/search", params={"q": "  "}).status_code == 422


def test_compact_data_supports_search_translate_word_sense_and_suggestions(client):
    assert client.get("/translate", params={"word": "water"}).json()["found"]
    assert client.get("/word-sense", params={"word": "water"}).json()["found"]
    assert client.get("/search-suggestions", params={"q": "wa"}).json()["suggestions"] == ["water"]


def test_contribution_is_pending_private_and_persists_across_restart(client, paths):
    response = client.post("/contribute", json=suggestion())
    assert response.status_code == 201
    ident = response.json()["id"]
    assert response.json()["status"] == "pending"
    assert client.get("/search", params={"q": "test word"}).json()["total"] == 0
    assert client.get("/review/contributions").status_code == 401
    assert client.get("/review/contributions", headers={"Authorization": "Bearer wrong"}).status_code == 401
    database, data = paths
    with TestClient(create_app(database, data, review_token="test-editor-token", writable=True)) as second:
        queue = second.get("/review/contributions", headers={"Authorization": "Bearer test-editor-token"}).json()
        assert queue["contributions"][0]["id"] == ident
        assert second.get("/stats").json()["total_entries"] == 2
        assert second.get("/stats").json()["pending_contributions"] == 1


def test_duplicate_submission_is_idempotent(client):
    first = client.post("/contribute", json=suggestion()).json()
    second = client.post("/contribute", json=suggestion(word=" TEST WORD ")).json()
    assert first["id"] == second["id"]
    assert second["duplicate"] is True
    assert client.get("/stats").json()["pending_contributions"] == 1


def test_review_publishes_only_after_authorized_approval_without_claiming_native_verification(client):
    ident = client.post("/contribute", json=suggestion()).json()["id"]
    path = "/review/contributions/" + ident
    assert client.post(path, json={"approve": True}).status_code == 401
    response = client.post(path, json={"approve": True}, headers={"Authorization": "Bearer test-editor-token"})
    assert response.json()["status"] == "approved"
    entry = client.get("/search", params={"q": "test word"}).json()["entries"][0]
    assert entry["status"] == "editor_reviewed"
    assert entry["native_speaker_verified"] is False
    assert entry["dialect"] == "Ijebu"
    assert entry["examples"] == []
    assert client.get("/stats").json()["editor_reviewed"] == 1
    assert client.post(path, json={"approve": True}, headers={"Authorization": "Bearer test-editor-token"}).status_code == 404


def test_rejection_does_not_publish(client):
    ident = client.post("/contribute", json=suggestion()).json()["id"]
    assert client.post("/review/contributions/" + ident, json={"approve": False},
                       headers={"Authorization": "Bearer test-editor-token"}).json()["status"] == "rejected"
    assert client.get("/search", params={"q": "test word"}).json()["total"] == 0


def test_validation_and_ephemeral_storage_never_report_success(client, paths):
    assert client.post("/contribute", json=suggestion(translation=" ")).status_code == 422
    assert client.post("/contribute", json=suggestion(language="Swahili")).status_code == 422
    assert client.post("/contribute", json=suggestion(consent=False)).status_code == 422
    assert client.post("/contribute", json=suggestion(context="x" * 17000)).status_code == 413
    database, data = paths
    with TestClient(create_app(database, data, writable=False)) as ephemeral:
        assert ephemeral.post("/contribute", json=suggestion()).status_code == 503
        assert ephemeral.get("/stats").json()["contributions_enabled"] is False


def test_failed_database_write_never_reports_success(client, monkeypatch):
    def fail(_):
        raise sqlite3.OperationalError("disk full")
    monkeypatch.setattr(client.app.state.corpus, "contribute", fail)
    assert client.post("/contribute", json=suggestion()).status_code == 503


def test_imports_are_atomic_deduplicated_and_do_not_invent_examples(paths):
    database, data = paths
    corpus = Corpus(database)
    source = data / "ede_word_sense.json"
    assert corpus.import_file(source) == 2
    assert corpus.import_file(source) == 0
    rich = data / "rich.json"
    rich.write_text(json.dumps({"water": {"definitions": [{"translations": [
        {"word": "omi", "language": "Yoruba", "sources": ["Example source"], "confidence": 0.99,
         "examples": [{"english": "water", "yoruba": "omi"}]}]}]}}))
    assert corpus.import_file(rich) == 0
    assert "Example source" in corpus.search("water")["entries"][0]["sources"]
    assert corpus.search("water")["entries"][0]["examples"] == []
    broken = data / "broken.json"
    broken.write_text(json.dumps({"one": {"t": [{"l": "Yoruba", "w": "two"}]}, "bad": {"t": [{}]}}))
    with pytest.raises(KeyError):
        corpus.import_file(broken)
    assert corpus.stats()["total_entries"] == 2


def test_empty_or_corrupt_corpus_has_honest_status(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "ede_word_sense.json").write_text("invalid")
    with TestClient(create_app(tmp_path / "test.db", data, writable=False)) as empty:
        assert empty.get("/stats").json()["total_entries"] == 0
        assert empty.get("/health").json()["status"] == "no_data"
        assert empty.get("/stats").json()["data_errors"] == ["ede_word_sense.json"]


def test_concurrent_writers_do_not_lose_submissions(paths):
    database, _ = paths
    corpus = Corpus(database)
    def save(index):
        return corpus.contribute(suggestion(word=f"word {index}"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(save, range(10)))
    assert len({r["id"] for r in result}) == 10
    assert len(corpus.queue()) == 10


def test_rate_limit_and_missing_editor_configuration(client, paths):
    for i in range(10):
        assert client.post("/contribute", json=suggestion(word=str(i))).status_code == 201
    assert client.post("/contribute", json=suggestion(word="limited")).status_code == 429
    database, data = paths
    with TestClient(create_app(database, data, review_token="", writable=True)) as no_editor:
        assert no_editor.get("/review/contributions").status_code == 503


def test_static_ui_security_and_openapi(client):
    html = client.get("/").text
    assert "A growing corpus, with honest labels." in html
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/missing").status_code == 422
    assert "script-src 'self'" in client.get("/").headers["content-security-policy"]
    assert client.get("/openapi.json").status_code == 200
    script = client.get("/static/app.js").text
    assert "innerHTML" not in script
    assert "localStorage" not in script

def test_word_browser_separates_pairs_without_inventing_word_alignments(client):
    data = client.get("/browse").json()
    assert data["total"] == 1
    assert data["entries"][0]["english"] == "water"
    assert data["entries"][0]["entry_kind"] == "word"
    phrase = client.get("/browse", params={"kind": "phrase"}).json()["entries"][0]
    assert phrase["english_words"] == ["greeting"]
    assert len(phrase["yoruba_words"]) == 2
    assert client.get("/search", params={"q": "greeting", "kind": "word"}).json()["total"] == 0
    assert client.get("/stats").json()["word_entries"] == 1
    assert client.get("/stats").json()["phrase_entries"] == 1
    assert client.get("/browse", params={"kind": "bad"}).status_code == 422


def test_tokenization_preserves_combining_marks_and_does_not_treat_codes_as_words():
    from corpus import word_tokens, entry_kind
    text = unicodedata.normalize("NFD", "\u1eb9\u0300d\u00e8")
    assert word_tokens(text) == [unicodedata.normalize("NFC", text)]
    assert entry_kind("hello", "test") == "word"
    assert entry_kind("hello world", "test") == "phrase"
    assert entry_kind("_go", "test") == "phrase"
    assert entry_kind("123", "456") == "phrase"


def test_concurrent_duplicate_suggestions_collapse_to_one_record(paths):
    database, _ = paths
    corpus = Corpus(database)
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: corpus.contribute(suggestion()), range(6)))
    assert len({item["id"] for item in records}) == 1
    assert len(corpus.queue()) == 1