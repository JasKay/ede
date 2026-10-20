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
