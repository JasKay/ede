"""Sense-scoped synonym proposals. Similar glosses are never proof of synonymy."""
import hashlib
import json
from uuid import uuid4
from corpus import normalize, utcnow, entry_kind


def audit(db, kind, ident, decision, actor, note):
    db.execute("INSERT INTO review_actions VALUES (?,?,?,?,?,?,?)",
               (uuid4().hex, kind, ident, decision, actor, note, utcnow()))


def insert(db, sense_id, target, provenance):
    target = target.strip()
    if not target or len(target) > 150 or entry_kind(target, target) != "word":
        raise ValueError("Use one Yoruba headword with its tone marks")
    row = db.execute("SELECT e.translation_key FROM lexical_senses s JOIN entries e ON e.id=s.entry_id WHERE s.id=?", (sense_id,)).fetchone()
    if not row:
        raise ValueError("Dictionary sense not found")
    key = normalize(target)
    if key == row["translation_key"]:
        raise ValueError("A synonym must be a different headword")
    ident = hashlib.sha256(json.dumps([sense_id, key], ensure_ascii=False).encode()).hexdigest()
    existing = db.execute("SELECT id, status FROM synonym_relations WHERE id=?", (ident,)).fetchone()
    if existing:
        return {"id": ident, "status": existing["status"], "duplicate": True}
    db.execute("INSERT INTO synonym_relations VALUES (?,?,?,?,?,?,?,?)",
               (ident, sense_id, target, key, json.dumps(provenance, ensure_ascii=False), "pending", utcnow(), None))
    return {"id": ident, "status": "pending", "duplicate": False}


def import_synonyms(db, sense, existing):
    # Source annotations are candidates, not Ede-reviewed equivalences.
    for candidate in sense.get("synonyms", []):
        target = candidate.get("word", "")
        if not isinstance(target, str) or entry_kind(target, target) != "word" or normalize(target) == normalize(sense["yoruba"]):
            continue
        if len(target) > 150:
            continue
        ident = hashlib.sha256(json.dumps([sense["id"], normalize(target)], ensure_ascii=False).encode()).hexdigest()
        if ident in existing:
            continue
        provenance = {"origin": "source_annotation", "source": sense["source"],
               "history": sense["history"], "license": sense["license"], "license_url": sense["license_url"],
               "attribution": sense["attribution"], "qualifiers": candidate.get("tags", []) + candidate.get("raw_tags", [])}
        db.execute("INSERT INTO synonym_relations VALUES (?,?,?,?,?,?,?,?)",
                   (ident, sense["id"], target.strip(), normalize(target), json.dumps(provenance, ensure_ascii=False), "pending", utcnow(), None))
        existing.add(ident)


def propose(corpus, sense_id, target, source, note, actor):
    with corpus.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        result = insert(db, sense_id, target, {"origin": "editor_suggestion", "source": source, "note": note,
                                              "license": "not established", "submitted_by": actor})
        if not result["duplicate"]:
            audit(db, "synonym", result["id"], "proposed", actor, note)
    return result


def queue(corpus, limit=20, offset=0, query="", status="pending"):
    where, params = "r.status=?", [status]
    if query.strip():
        key = normalize(query).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where += r" AND (e.translation_key LIKE ? ESCAPE '\' OR e.english_key LIKE ? ESCAPE '\' OR r.target_key LIKE ? ESCAPE '\')"
        params.extend(["%" + key + "%"] * 3)
    with corpus.connect() as db:
        total = db.execute("SELECT COUNT(*) FROM synonym_relations r JOIN lexical_senses s ON s.id=r.sense_id JOIN entries e ON e.id=s.entry_id WHERE " + where, tuple(params)).fetchone()[0]
        rows = db.execute("SELECT r.*, s.payload, s.review_status AS sense_status FROM synonym_relations r JOIN lexical_senses s ON s.id=r.sense_id JOIN entries e ON e.id=s.entry_id WHERE " + where + " ORDER BY r.id LIMIT ? OFFSET ?", tuple(params + [limit, offset])).fetchall()
    return {"synonyms": [{**dict(row), "sense": json.loads(row["payload"]), "provenance": json.loads(row["provenance"])} for row in rows], "total": total}


def review(corpus, ident, approve, actor, note):
    status = "approved" if approve else "rejected"
    with corpus.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT r.id, r.status, s.review_status FROM synonym_relations r JOIN lexical_senses s ON s.id=r.sense_id WHERE r.id=? AND r.status IN ('pending', 'approved')", (ident,)).fetchone()
        if not row or row["status"] == status:
            raise ValueError("Reviewable synonym not found")
        if approve and row["review_status"] == "needs_correction":
            raise ValueError("Resolve the flagged source meaning before approving its synonym")
        db.execute("UPDATE synonym_relations SET status=?, reviewed_at=? WHERE id=?", (status, utcnow(), ident))
        audit(db, "synonym", ident, status, actor, note)
    return {"id": ident, "status": status}


def approved_in_db(db, sense_ids):
    if not sense_ids:
        return {}
    rows = db.execute("SELECT r.* FROM synonym_relations r JOIN lexical_senses s ON s.id=r.sense_id WHERE r.status='approved' AND s.review_status<>'needs_correction' AND r.sense_id IN (" + ",".join("?" for _ in sense_ids) + ") ORDER BY r.target_key", tuple(sense_ids)).fetchall()
    result = {}
    for row in rows:
        result.setdefault(row["sense_id"], []).append({"word": row["target"], "review_status": "editor_reviewed",
                    "provenance": json.loads(row["provenance"]), "reviewed_at": row["reviewed_at"]})
    return result


def approved(corpus, sense_ids):
    with corpus.connect() as db:
        return approved_in_db(db, sense_ids)


def summary(corpus):
    with corpus.connect() as db:
        pending = db.execute("SELECT COUNT(*) FROM contributions WHERE status='pending'").fetchone()[0]
        senses = db.execute("SELECT review_status, COUNT(*) AS count FROM lexical_senses GROUP BY review_status").fetchall()
        synonyms = db.execute("SELECT COUNT(*) FROM synonym_relations WHERE status='pending'").fetchone()[0]
    return {"contributions": pending, "senses": {row["review_status"]: row["count"] for row in senses}, "synonyms": synonyms}


def history(corpus, limit=30, offset=0):
    with corpus.connect() as db:
        return [dict(row) for row in db.execute("SELECT * FROM review_actions ORDER BY created_at DESC, id LIMIT ? OFFSET ?", (limit, offset)).fetchall()]
