import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from api import create_app
from corpus import Corpus
from lexicon import import_snapshot, review
from tools import build_lexicon


def record(**changes):
    value = {"id": "test-sense", "english": "fixture meaning", "yoruba": "fixtureword", "pos": "noun",
             "glosses": ["fixture meaning"], "labels": ["test label"], "usage_notes": ["Test qualifier"],
             "examples": [{"yoruba": "fixture example", "english": "test example", "source": "https://en.wiktionary.org/wiki/test"}],
             "source": "https://en.wiktionary.org/wiki/test#Yoruba",
             "history": "https://en.wiktionary.org/w/index.php?title=test&action=history",
             "license": "CC-BY-SA-4.0", "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
             "attribution": "Synthetic test fixture, not actual dictionary evidence"}
    return {**value, **changes}


def snapshot(path, *records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def test_lexical_metadata_and_review_are_separate_from_native_verification(tmp_path):
    corpus = Corpus(tmp_path / "db.sqlite")
    path = snapshot(tmp_path / "source.jsonl", record())
    assert import_snapshot(corpus, path) == 1
    assert import_snapshot(corpus, path) == 0
    result = corpus.search("fixture meaning", kind="word")
    assert result["total"] == 1  # A sourced single headword may have a multiword definition.
    entry = result["entries"][0]
    assert entry["senses"][0]["pos"] == "noun"
    assert entry["senses"][0]["review_status"] == "source_imported"
    assert entry["senses"][0]["examples"][0]["english"] == "test example"
    assert entry["native_speaker_verified"] is False
    assert entry["confidence"] is None
    assert corpus.stats()["dictionary_headwords"] == 1
    review(corpus, "test-sense", True)
    assert corpus.search("fixtureword")["entries"][0]["senses"][0]["review_status"] == "editor_reviewed"
    assert import_snapshot(corpus, path) == 0
    assert corpus.stats()["reviewed_senses"] == 1


def test_invalid_licence_rolls_back_the_entire_import_and_flags_are_visible(tmp_path):
    corpus = Corpus(tmp_path / "db.sqlite")
    path = snapshot(tmp_path / "source.jsonl", record(), record(id="bad", license="unknown"))
    with pytest.raises(ValueError):
        import_snapshot(corpus, path)
    assert corpus.stats()["dictionary_senses"] == 0
    assert corpus.stats()["total_entries"] == 0
    path = snapshot(path, record())
    import_snapshot(corpus, path)
    review(corpus, "test-sense", False)
    assert corpus.search("fixtureword")["entries"][0]["senses"][0]["review_status"] == "needs_correction"
    # Flagged meanings can now be resolved through the reviewer portal.
    review(corpus, "test-sense", True)
    with pytest.raises(ValueError):
        review(corpus, "test-sense", True)


def test_builder_preserves_canonical_tones_and_excludes_quotations_and_ambiguity(tmp_path, monkeypatch):
    source = tmp_path / "input.jsonl"
    data = {"lang_code": "yo", "word": "test", "pos": "verb",
            "forms": [{"form": "t\u00e8st", "tags": ["canonical"]}],
            "synonyms": [{"word": "unmapped"}],
            "senses": [{"id": "sense", "glosses": ["test meaning"], "synonyms": [{"word": "another", "tags": ["regional"]}], "examples": [
                {"type": "quotation", "text": "do not copy", "english": "do not copy"},
                {"type": "example", "ref": "External author", "text": "omit", "english": "omit"},
                {"type": "example", "text": "test example", "english": "fixture example"}]}]}
    ambiguous = {**data, "forms": [{"form": "first", "tags": ["canonical"]}, {"form": "second", "tags": ["canonical"]}]}
    source.write_text(json.dumps(data) + "\n" + json.dumps(ambiguous) + "\n")
    monkeypatch.setattr(build_lexicon, "EXPECTED", hashlib.sha256(source.read_bytes()).hexdigest())
    output = tmp_path / "output.jsonl"
    build_lexicon.build(source, output)
    result = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(result) == 1
    assert result[0]["yoruba"] == "t\u00e8st"
    assert len(result[0]["examples"]) == 1
    assert result[0]["history"].startswith("https://en.wiktionary.org/")
    assert result[0]["synonyms"] == [{"word": "another", "tags": ["regional"], "raw_tags": []}]


def test_sense_review_requires_editor_authorization_and_preserves_source_fields(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    snapshot(directory / "yoruba-lexicon.jsonl", record())
    with TestClient(create_app(tmp_path / "db.sqlite", directory, review_token="test-token", writable=True)) as client:
        assert client.get("/review/senses").status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        queue = client.get("/review/senses", headers=headers).json()["senses"]
        assert len(queue) == 1
        assert len(client.get("/review/senses", params={"q":"fixtureword"}, headers=headers).json()["senses"]) == 1
        assert client.get("/review/senses", params={"q":"%"}, headers=headers).json()["senses"] == []
        assert client.get("/review/senses", params={"q":"missing"}, headers=headers).json()["senses"] == []
        assert client.post("/review/senses/test-sense", json={"approve": True}).status_code == 401
        assert client.post("/review/senses/test-sense", json={"approve": True}, headers=headers).status_code == 200
        assert client.get("/stats").json()["reviewed_senses"] == 1
        assert client.get("/stats").json()["native_speaker_verified"] == 0
        assert client.get("/attribution").status_code == 200


def test_headword_index_groups_senses_and_reports_real_gaps(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    accented = "\u1eb9\u0300ka"
    snapshot(directory / "yoruba-lexicon.jsonl",
             record(id="a", yoruba=accented),
             record(id="b", yoruba=accented, english="second meaning", examples=[]),
             record(id="c", yoruba="eka", english="another meaning", examples=[]),
             record(id="d", yoruba="percent%word", examples=[]))
    with TestClient(create_app(tmp_path / "db.sqlite", directory)) as client:
        index = client.get("/dictionary/headwords", params={"limit": 1}).json()
        assert index["total"] == 3
        assert len(index["headwords"]) == 1
        page2 = client.get("/dictionary/headwords", params={"limit": 1, "offset": 1}).json()
        assert index["headwords"] != page2["headwords"]
        exact = client.get("/dictionary/word", params={"headword": accented.upper()}).json()
        assert len(exact["senses"]) == 2
        assert exact["native_speaker_verified"] is False
        assert len(client.get("/dictionary/word", params={"headword": "eka"}).json()["senses"]) == 1
        assert client.get("/dictionary/word", params={"headword": "missing"}).status_code == 404
        assert client.get("/dictionary/headwords", params={"prefix": "%"}).json()["total"] == 0
        assert client.get("/dictionary/headwords", params={"prefix": "percent%"}).json()["total"] == 1
        assert client.get("/dictionary/headwords", params={"limit": 101}).status_code == 422
        data = client.get("/dictionary/coverage").json()
        assert data["headwords"] == 3
        assert data["senses"] == 4
        assert data["headwords_without_examples"] == 2
        assert data["usage_examples"] == 1
        assert data["awaiting_review"] == 4
        assert data["completeness_percent"] is None
