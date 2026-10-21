import json

from fastapi.testclient import TestClient
import pytest

from api import create_app
from corpus import Corpus
from lexicon import import_snapshot, review as review_sense
from relations import queue, propose, review, history


def records(path):
    sense = {"id": "sense-a", "english": "fixture sense", "yoruba": "fixture", "pos": "noun",
             "glosses": ["fixture sense"], "labels": [], "examples": [], "usage_notes": [],
             "source": "https://en.wiktionary.org/wiki/fixture#Yoruba",
             "history": "https://en.wiktionary.org/w/index.php?title=fixture&action=history",
             "license": "CC-BY-SA-4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
             "attribution": "Synthetic fixture, not language evidence",
             "synonyms": [{"word": "other", "tags": ["regional"], "raw_tags": ["test qualifier"]},
                          {"word": "fixture"}, {"word": "two words"}]}
    path.write_text(json.dumps(sense) + "\n")
    return path


def test_source_synonyms_are_private_until_reviewed_and_preserve_decisions(tmp_path):
    corpus = Corpus(tmp_path / "db")
    path = records(tmp_path / "lex.jsonl")
    import_snapshot(corpus, path)
    assert len(queue(corpus)["synonyms"]) == 1
    assert not corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    relation = queue(corpus)["synonyms"][0]
    assert relation["provenance"]["qualifiers"] == ["regional", "test qualifier"]
    assert relation["provenance"]["license"] == "CC-BY-SA-4.0"
    review(corpus, relation["id"], True, "test-editor", "Checked the meaning")
    approved = corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    assert approved[0]["word"] == "other"
    assert approved[0]["review_status"] == "editor_reviewed"
    assert history(corpus)[0]["note"] == "Checked the meaning"
    # A changed snapshot must not reset prior decisions.
    path.write_text(path.read_text() + "\n")
    import_snapshot(corpus, path)
    assert queue(corpus)["total"] == 0
    assert corpus.search("fixture")["entries"][0]["native_speaker_verified"] is False
    review_sense(corpus, "sense-a", False, "test-editor", "Check source spelling")
    assert not corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    review_sense(corpus, "sense-a", True, "test-editor", "Source checked")
    assert corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    review_sense(corpus, "sense-a", False, "test-editor", "Reopen a reviewed meaning")
    assert not corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    review_sense(corpus, "sense-a", True, "test-editor", "Rechecked")
    assert queue(corpus, status="approved")["total"] == 1
    review(corpus, relation["id"], False, "test-editor", "Withdraw incorrect link")
    assert not corpus.search("fixture")["entries"][0]["senses"][0]["synonyms"]
    assert history(corpus)[0]["note"] == "Withdraw incorrect link"


def test_portal_api_authorization_audit_and_synonym_workflow(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    records(directory / "yoruba-lexicon.jsonl")
    headers = {"Authorization": "Bearer editor-secret"}
    with TestClient(create_app(tmp_path / "db", directory, review_token="editor-secret", writable=True)) as client:
        assert client.get("/review").status_code == 200
        assert "noindex" in client.get("/review").text
        for route in ["summary", "history", "synonyms", "contributions", "senses"]:
            response = client.get("/review/" + route)
            assert response.status_code == 401
            assert response.headers["cache-control"] == "no-store"
        assert client.post("/review/synonyms", json={"sense_id": "sense-a", "target": "example", "source": "fixture"}).status_code == 401
        summary = client.get("/review/summary", headers=headers).json()
        assert summary["synonyms"] == 1
        assert client.get("/review/senses", headers=headers).json()["senses"][0]["synonyms"] == []
        assert "editor-secret" not in json.dumps(summary)
        assert client.get("/review/synonyms", params={"q": "%"}, headers=headers).json()["total"] == 0
        assert client.get("/review/synonyms", params={"q": "other"}, headers=headers).json()["total"] == 1
        assert client.get("/review/synonyms", params={"limit": 101}, headers=headers).status_code == 422
        assert client.post("/review/synonyms", headers=headers, json={"sense_id": "sense-a", "target": "test", "source": "   "}).status_code == 422
        for target in ["fixture", "two words"]:
            assert client.post("/review/synonyms", headers=headers, json={"sense_id": "sense-a", "target": target, "source": "test"}).status_code == 422
        assert client.post("/review/synonyms", headers=headers, json={"sense_id": "missing", "target": "test", "source": "test"}).status_code == 422
        body = {"sense_id": "sense-a", "target": "another", "source": "Reviewer reference", "note": "Test context"}
        proposal = client.post("/review/synonyms", headers=headers, json=body).json()
        assert client.post("/review/synonyms", headers=headers, json=body).json()["duplicate"]
        ident = proposal["id"]
        assert client.post("/review/synonyms/" + ident, json={"approve": True}).status_code == 401
        assert client.post("/review/synonyms/" + ident, headers=headers, json={"approve": False, "note": "Not equivalent"}).status_code == 200
        assert client.post("/review/synonyms/" + ident, headers=headers, json={"approve": True}).status_code == 409
        assert client.get("/dictionary/word?headword=fixture").json()["senses"][0]["synonyms"] == []
        client.post("/review/senses/sense-a", headers=headers, json={"approve": False, "note": "Source needs checking"})
        flagged = client.get("/review/senses?status=needs_correction", headers=headers).json()["senses"]
        assert flagged[0]["review_note"] == "Source needs checking"
        original = client.get("/review/synonyms", headers=headers).json()["synonyms"][0]["id"]
        assert client.post("/review/synonyms/" + original, headers=headers, json={"approve": True}).status_code == 409
        client.post("/review/senses/sense-a", headers=headers, json={"approve": True, "note": "Resolved"})
        assert client.post("/review/synonyms/" + original, headers=headers, json={"approve": True, "note": "Source checked"}).status_code == 200
        assert client.get("/dictionary/word?headword=fixture").json()["senses"][0]["synonyms"][0]["word"] == "other"
        actions = client.get("/review/history", headers=headers).json()["actions"]
        assert {action["record_type"] for action in actions} == {"sense", "synonym"}
        assert all("editor-secret" not in json.dumps(action) for action in actions)


def test_read_only_portal_cannot_mutate(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    records(directory / "yoruba-lexicon.jsonl")
    headers = {"Authorization": "Bearer test"}
    with TestClient(create_app(tmp_path / "db", directory, review_token="test", writable=False)) as client:
        assert client.get("/review/summary", headers=headers).json()["writable"] is False
        assert client.post("/review/synonyms", headers=headers, json={"sense_id": "sense-a", "target": "other", "source": "test"}).status_code == 503
        ident = client.get("/review/synonyms", headers=headers).json()["synonyms"][0]["id"]
        assert client.post("/review/synonyms/" + ident, headers=headers, json={"approve": True}).status_code == 503


def test_review_audit_survives_restart_and_community_decisions_are_logged(tmp_path):
    path = tmp_path / "db"
    corpus = Corpus(path)
    suggestion = corpus.contribute({"word": "fixture", "translation": "test", "language": "Yoruba", "username": "fixture", "dialect": "unspecified", "context": "", "source": ""})
    corpus.review(suggestion["id"], False, "test-credential", "Test rejection")
    saved = history(Corpus(path))
    assert saved[0]["record_type"] == "contribution"
    assert saved[0]["note"] == "Test rejection"
