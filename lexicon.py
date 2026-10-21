"""Source-attributed dictionary senses, separate from community verification."""
import hashlib
import json
from pathlib import Path

from corpus import normalize, utcnow


def import_snapshot(corpus, path):
    content = Path(path).read_bytes()
    digest = hashlib.sha256(b"ede-lexicon-v1:" + content).hexdigest()
    records = [json.loads(line) for line in content.splitlines() if line.strip()]
    with corpus.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM imports WHERE digest=?", (digest,)).fetchone():
            return 0
        existing = {r["id"]: dict(r) for r in db.execute("SELECT id, sources FROM entries").fetchall()}
        senses = {r[0] for r in db.execute("SELECT id FROM lexical_senses").fetchall()}
        count = 0
        for record in records:
            if record["license"] != "CC-BY-SA-4.0" or not record["source"].startswith("https://en.wiktionary.org/wiki/"):
                raise ValueError("Dictionary record lacks the expected licence or attribution")
            english, yoruba = record["english"].strip(), record["yoruba"].strip()
            if not english or not yoruba:
                raise ValueError("Empty dictionary record")
            ek, tk = normalize(english), normalize(yoruba)
            ident = hashlib.sha256(json.dumps([ek, tk, "Yoruba", "unspecified"], ensure_ascii=False).encode()).hexdigest()
            sources = [record["source"], record["history"]]
            if ident not in existing:
                db.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    ident, english, yoruba, ek, tk, "Yoruba", json.dumps(sources),
                    "CC-BY-SA-4.0", "unspecified", "dictionary", "imported_unverified",
                    "[]", utcnow(), "word"))
                existing[ident] = {"sources": json.dumps(sources)}
                count += 1
            else:
                sources = sorted(set(json.loads(existing[ident]["sources"]) + sources))
                db.execute("UPDATE entries SET sources=? WHERE id=?", (json.dumps(sources), ident))
                existing[ident]["sources"] = json.dumps(sources)
            if record["id"] not in senses:
                db.execute("INSERT INTO lexical_senses VALUES (?,?,?,?,?)",
                           (record["id"], ident, json.dumps(record, ensure_ascii=False), "source_imported", None))
                senses.add(record["id"])
        db.execute("INSERT INTO imports VALUES (?,?,?,?)", (digest, Path(path).name, utcnow(), count))
    return count


def enrich(db, entry_ids):
    if not entry_ids:
        return {}
    rows = db.execute("SELECT * FROM lexical_senses WHERE entry_id IN (" +
                      ",".join("?" for _ in entry_ids) + ") ORDER BY id", tuple(entry_ids)).fetchall()
    result = {}
    for row in rows:
        payload = json.loads(row["payload"])
        payload.update(review_status=row["review_status"], reviewed_at=row["reviewed_at"])
        result.setdefault(row["entry_id"], []).append(payload)
    return result


def queue(corpus, limit=20, offset=0, query=""):
    where = "review_status='source_imported'"
    params = []
    if query.strip():
        key = normalize(query)
        pattern = "%" + key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where += r" AND entry_id IN (SELECT id FROM entries WHERE english_key LIKE ? ESCAPE '\' OR translation_key LIKE ? ESCAPE '\')"
        params.extend([pattern, pattern])
    with corpus.connect() as db:
        rows = db.execute("SELECT * FROM lexical_senses WHERE " + where + " ORDER BY id LIMIT ? OFFSET ?",
                          tuple(params + [limit, offset])).fetchall()
    return [{**json.loads(row["payload"]), "review_status": row["review_status"]} for row in rows]


def review(corpus, ident, approve):
    status = "editor_reviewed" if approve else "needs_correction"
    with corpus.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM lexical_senses WHERE id=? AND review_status='source_imported'", (ident,)).fetchone()
        if not row:
            raise ValueError("Unreviewed dictionary sense not found")
        db.execute("UPDATE lexical_senses SET review_status=?, reviewed_at=? WHERE id=?", (status, utcnow(), ident))
    return {"id": ident, "status": status}


def headwords(corpus, prefix="", limit=30, offset=0):
    """Browse sourced headwords only; never infer meanings from corpus pairs."""
    key = normalize(prefix.strip())
    pattern = key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    where = "EXISTS (SELECT 1 FROM lexical_senses s WHERE s.entry_id=e.id)"
    if key:
        where += r" AND translation_key LIKE ? ESCAPE '\'"
    params = (pattern,) if key else ()
    with corpus.connect() as db:
        total = db.execute("SELECT COUNT(DISTINCT translation_key) FROM entries e WHERE " + where, params).fetchone()[0]
        rows = db.execute("SELECT translation_key, MIN(translation) AS headword, COUNT(*) AS meaning_records FROM entries e WHERE " + where +
                          " GROUP BY translation_key ORDER BY translation_key LIMIT ? OFFSET ?", params + (limit, offset)).fetchall()
    return {"headwords": [dict(row) for row in rows], "total": total, "offset": offset, "limit": limit,
            "ordering": "Unicode order; prefix matching preserves tone marks and underdots"}


def word(corpus, headword):
    with corpus.connect() as db:
        rows = db.execute("SELECT s.* FROM lexical_senses s JOIN entries e ON e.id=s.entry_id WHERE e.translation_key=? ORDER BY s.id",
                          (normalize(headword.strip()),)).fetchall()
    senses = [{**json.loads(row["payload"]), "review_status": row["review_status"], "reviewed_at": row["reviewed_at"]} for row in rows]
    return {"headword": senses[0]["yoruba"] if senses else headword, "senses": senses,
            "native_speaker_verified": False}


def coverage(corpus):
    with corpus.connect() as db:
        rows = db.execute("SELECT payload, review_status FROM lexical_senses").fetchall()
    words, with_examples = set(), set()
    examples = reviewed = flagged = 0
    for row in rows:
        sense = json.loads(row["payload"])
        key = normalize(sense["yoruba"])
        words.add(key)
        if sense.get("examples"):
            with_examples.add(key)
        examples += len(sense.get("examples", []))
        reviewed += row["review_status"] == "editor_reviewed"
        flagged += row["review_status"] == "needs_correction"
    return {"language": "Yoruba", "headwords": len(words), "senses": len(rows), "usage_examples": examples,
            "headwords_with_examples": len(with_examples), "headwords_without_examples": len(words - with_examples),
            "reviewed_senses": reviewed, "flagged_senses": flagged, "awaiting_review": len(rows) - reviewed - flagged,
            "completeness_percent": None,
            "notice": "No complete inventory of Yoruba words has been established. Coverage counts are not a completeness score. Pronunciation audio and native-speaker verification are not yet available."}
