"""Corpus storage. Imported data is never treated as human verification."""
import hashlib
import json
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def normalize(text):
    return unicodedata.normalize("NFC", text.strip()).casefold()


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def word_tokens(text):
    """Token boundaries only: no cross-language word alignment is inferred."""
    tokens, current = [], ""
    for char in unicodedata.normalize("NFC", text):
        if unicodedata.category(char)[0] in ("L", "M"):
            current += char
        elif char in ("'", "\u2019", "-") and current:
            current += char
        else:
            if current.strip("'-\u2019"):
                tokens.append(current.strip("'-\u2019"))
            current = ""
    if current.strip("'-\u2019"):
        tokens.append(current.strip("'-\u2019"))
    return list(dict.fromkeys(tokens))


def entry_kind(english, translation):
    def single(text):
        tokens = word_tokens(text)
        return len(tokens) == 1 and normalize(tokens[0]) == normalize(text)
    return "word" if single(english) and single(translation) else "phrase"


class Corpus:
    dialect = "sqlite"
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY, english TEXT NOT NULL, translation TEXT NOT NULL,
                    english_key TEXT NOT NULL, translation_key TEXT NOT NULL,
                    language TEXT NOT NULL, sources TEXT NOT NULL, license TEXT NOT NULL,
                    dialect TEXT NOT NULL, domain TEXT NOT NULL, status TEXT NOT NULL,
                    examples TEXT NOT NULL, created_at TEXT NOT NULL,
                    entry_kind TEXT NOT NULL DEFAULT 'unclassified',
                    UNIQUE(english_key, translation_key, language, dialect)
                );
                CREATE INDEX IF NOT EXISTS english_lookup ON entries(english_key);
                CREATE INDEX IF NOT EXISTS translation_lookup ON entries(translation_key);
                CREATE TABLE IF NOT EXISTS imports (
                    digest TEXT PRIMARY KEY, filename TEXT NOT NULL, imported_at TEXT NOT NULL,
                    records INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS contributions (
                    id TEXT PRIMARY KEY, english TEXT NOT NULL, translation TEXT NOT NULL,
                    language TEXT NOT NULL, username TEXT NOT NULL, dialect TEXT NOT NULL,
                    context TEXT NOT NULL, source TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, reviewed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS rate_limits (
                    client_key TEXT PRIMARY KEY, window_start INTEGER NOT NULL, requests INTEGER NOT NULL
                );
            """)
            if self.dialect == "postgres":
                db.execute("ALTER TABLE entries ADD COLUMN IF NOT EXISTS entry_kind TEXT NOT NULL DEFAULT 'unclassified'")
            elif "entry_kind" not in {row[1] for row in db.execute("PRAGMA table_info(entries)")}:
                db.execute("ALTER TABLE entries ADD COLUMN entry_kind TEXT NOT NULL DEFAULT 'unclassified'")
            for row in db.execute("SELECT id, english, translation FROM entries WHERE entry_kind='unclassified'").fetchall():
                db.execute("UPDATE entries SET entry_kind=? WHERE id=?", (entry_kind(row["english"], row["translation"]), row["id"]))
            db.execute("CREATE INDEX IF NOT EXISTS kind_lookup ON entries(entry_kind, english_key)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_file(self, path):
        """Atomic, repeatable import of existing compact, rich, or master JSON."""
        path = Path(path)
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM imports WHERE digest=?", (digest,)).fetchone():
                return 0
            data = json.loads(content)
            count = 0
            source_index = {r["id"]: {"sources": r["sources"]} for r in db.execute("SELECT id, sources FROM entries").fetchall()}
            for record in self.records(data):
                english, translation = record["english"].strip(), record["translation"].strip()
                if not english or not translation or record["language"] != "Yoruba":
                    continue
                ek, tk = normalize(english), normalize(translation)
                ident = hashlib.sha256(json.dumps([ek, tk, "Yoruba", normalize(record.get("dialect") or "unspecified")], ensure_ascii=False).encode()).hexdigest()
                sources = record.get("sources") or [f"Legacy Ede artifact: {path.name}; upstream source not recorded"]
                if not isinstance(sources, list):
                    sources = [str(sources)]
                sources = [s if isinstance(s, str) else json.dumps(s, ensure_ascii=False) for s in sources]
                existing = source_index.get(ident)
                if existing:
                    combined = sorted(set(json.loads(existing["sources"]) + sources))
                    db.execute("UPDATE entries SET sources=? WHERE id=?", (json.dumps(combined, ensure_ascii=False), ident))
                else:
                    db.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        ident, english, translation, ek, tk, "Yoruba",
                        json.dumps(sources, ensure_ascii=False), str(record.get("license") or "unknown"),
                        str(record.get("dialect") or "unspecified"), str(record.get("domain") or "unspecified"),
                        "imported_unverified", json.dumps(record.get("examples") or [], ensure_ascii=False), utcnow(), entry_kind(english, translation)))
                    count += 1
                source_index[ident] = {"sources": json.dumps(combined if existing else sources, ensure_ascii=False)}
            db.execute("INSERT INTO imports VALUES (?,?,?,?)", (digest, path.name, utcnow(), count))
        return count

    @staticmethod
    def records(data):
        if isinstance(data, list):
            for row in data:
                yield {
                    "english": row["source_text"], "translation": row["target_text"],
                    "language": row["target_language"], "sources": row.get("sources"),
                    "license": row.get("license"), "dialect": row.get("dialect"), "domain": row.get("domain"),
                }
        elif isinstance(data, dict):
            for english, entry in data.items():
                if not isinstance(entry, dict):
                    raise ValueError("Unsupported corpus record")
                if "t" in entry:
                    for translation in entry["t"]:
                        yield {"english": english, "translation": translation["w"], "language": translation["l"]}
                else:
                    for definition in entry.get("definitions", []):
                        for translation in definition.get("translations", []):
                            yield {
                                "english": english, "translation": translation["word"],
                                "language": translation["language"],
                                "sources": translation.get("sources") or definition.get("sources"),
                                "dialect": translation.get("dialect"), "domain": translation.get("domain"),
                                "license": translation.get("license"),
                                # Legacy enhancement scripts generated pseudo-examples: do not promote them.
                            }
        else:
            raise ValueError("Unsupported corpus format")

    @staticmethod
    def public_entry(row):
        entry = dict(row)
        entry.pop("english_key")
        entry.pop("translation_key")
        entry["sources"] = json.loads(entry["sources"])
        entry["examples"] = json.loads(entry["examples"])
        entry["confidence"] = None
        entry["native_speaker_verified"] = False
        entry["redistribution_cleared"] = False
        entry["english_words"] = word_tokens(entry["english"])
        entry["yoruba_words"] = word_tokens(entry["translation"])
        return entry

    def search(self, query, limit=20, offset=0, kind="all"):
        if kind not in ("all", "word", "phrase"):
            raise ValueError("Unknown record kind")
        key = normalize(query)
        pattern = "%" + key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where = r"(english_key LIKE ? ESCAPE '\' OR translation_key LIKE ? ESCAPE '\')"
        params = [pattern, pattern]
        if kind != "all":
            where += " AND entry_kind=?"
            params.append(kind)
        with self.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM entries WHERE " + where, tuple(params)).fetchone()[0]
            if key:
                order = r"CASE WHEN english_key=? OR translation_key=? THEN 0 WHEN english_key LIKE ? ESCAPE '\' THEN 1 ELSE 2 END, length(english), english_key, id"
                params.extend([key, key, pattern[1:]])
            else:
                order = "english_key, id"
            rows = db.execute("SELECT * FROM entries WHERE " + where + " ORDER BY " + order + " LIMIT ? OFFSET ?",
                              tuple(params + [limit, offset])).fetchall()
        return {"entries": [self.public_entry(r) for r in rows], "total": total,
                "limit": limit, "offset": offset, "kind": kind}

    def stats(self):
        with self.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            words = db.execute("SELECT COUNT(*) FROM entries WHERE entry_kind='word'").fetchone()[0]
            reviewed = db.execute("SELECT COUNT(*) FROM entries WHERE status='editor_reviewed'").fetchone()[0]
            pending = db.execute("SELECT COUNT(*) FROM contributions WHERE status='pending'").fetchone()[0]
            examples = [r[0] for r in db.execute("SELECT english FROM entries WHERE entry_kind='word' AND english_key != translation_key GROUP BY english ORDER BY length(english), english LIMIT 4")]
            imports = [dict(r) for r in db.execute("SELECT filename, imported_at, records FROM imports ORDER BY imported_at")]
        return {"word_entries": words, "phrase_entries": total - words, "total_entries": total, "languages": {"Yoruba": total}, "editor_reviewed": reviewed,
                "native_speaker_verified": 0, "pending_contributions": pending,
                "examples": examples, "imports": imports, "ready": total > 0}

    def contribute(self, data):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # Serialize duplicate detection with its insert, including concurrent submissions.
            rows = db.execute("SELECT * FROM contributions WHERE status='pending'").fetchall()
            for row in rows:
                if (normalize(row["english"]), normalize(row["translation"]), normalize(row["dialect"])) == (
                    normalize(data["word"]), normalize(data["translation"]), normalize(data["dialect"])):
                    return {"id": row["id"], "status": "pending", "duplicate": True}
            ident = str(uuid4())
            db.execute("INSERT INTO contributions VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                ident, data["word"], data["translation"], "Yoruba", data["username"],
                data["dialect"], data["context"], data["source"], "pending", utcnow(), None))
        return {"id": ident, "status": "pending", "duplicate": False}

    def queue(self, limit=50, offset=0):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM contributions WHERE status='pending' ORDER BY created_at LIMIT ? OFFSET ?", (limit, offset))]

    def review(self, ident, approve):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM contributions WHERE id=?", (ident,)).fetchone()
            if not row or row["status"] != "pending":
                raise ValueError("Pending contribution not found")
            if approve:
                ek, tk = normalize(row["english"]), normalize(row["translation"])
                eid = hashlib.sha256(json.dumps([ek, tk, "Yoruba", normalize(row["dialect"])], ensure_ascii=False).encode()).hexdigest()
                sources = [f"Ede community submission {ident}"]
                if row["source"]:
                    sources.append("Contributor-supplied reference (not independently authenticated): " + row["source"])
                existing = db.execute("SELECT sources FROM entries WHERE id=?", (eid,)).fetchone()
                if existing:
                    sources = sorted(set(sources + json.loads(existing["sources"])))
                    db.execute("UPDATE entries SET status='editor_reviewed', sources=? WHERE id=?",
                               (json.dumps(sources, ensure_ascii=False), eid))
                else:
                    # Contributor context is not a verified usage example.
                    db.execute("INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        eid, row["english"], row["translation"], ek, tk, "Yoruba",
                        json.dumps(sources, ensure_ascii=False), "unknown", row["dialect"], "community",
                        "editor_reviewed", "[]", utcnow(), entry_kind(row["english"], row["translation"])))
            status = "approved" if approve else "rejected"
            db.execute("UPDATE contributions SET status=?, reviewed_at=? WHERE id=?", (status, utcnow(), ident))
        return {"id": ident, "status": status}

    def allow_submission(self, client_key):
        window = int(time.time() // 600)
        with self.connect() as db:
            db.execute("DELETE FROM rate_limits WHERE window_start < ?", (window - 1,))
            count = db.execute("""
                INSERT INTO rate_limits(client_key, window_start, requests) VALUES (?, ?, 1)
                ON CONFLICT(client_key) DO UPDATE SET
                requests=CASE WHEN rate_limits.window_start=excluded.window_start THEN rate_limits.requests+1 ELSE 1 END,
                window_start=excluded.window_start RETURNING requests
            """, (client_key, window)).fetchone()[0]
        return count <= 10
