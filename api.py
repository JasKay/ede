"""Ede: Yoruba corpus search and a moderated contribution queue."""
import hmac
import logging
import sqlite3
import hashlib
import psycopg
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from corpus import Corpus

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("ede")


class Contribution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word: str = Field(min_length=1, max_length=500)
    translation: str = Field(min_length=1, max_length=1000)
    language: Literal["Yoruba"] = "Yoruba"
    username: str = Field(default="Anonymous", max_length=80)
    dialect: str = Field(default="unspecified", max_length=100)
    context: str = Field(default="", max_length=1000)
    source: str = Field(default="", max_length=500)
    consent: Literal[True]

    @field_validator("word", "translation", "username", "dialect", "context", "source")
    @classmethod
    def clean_text(cls, value):
        if any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("Control characters are not allowed")
        return value.strip()

    @field_validator("word", "translation")
    @classmethod
    def not_blank(cls, value):
        if not value:
            raise ValueError("Text cannot be blank")
        return value


class Review(BaseModel):
    approve: bool


def create_app(db_path=None, data_dir=None, review_token=None, writable=None):
    remote_url = os.getenv("DATABASE_URL") if db_path is None else None
    data_dir = Path(data_dir or os.getenv("EDE_DATA_DIR", str(ROOT / "data")))
    default_db = Path("/data/ede.db") if Path("/data").is_dir() else ROOT / "data" / "ede.db"
    db_path = db_path or os.getenv("EDE_DB_PATH", str(default_db))
    review_token = review_token if review_token is not None else os.getenv("EDE_REVIEW_TOKEN", "")
    # Spaces local disks are ephemeral. Do not accept submissions there by default.
    if writable is None:
        writable = bool(remote_url) or (not os.getenv("SPACE_ID") and not os.getenv("VERCEL")) or os.getenv("EDE_PERSISTENT_STORAGE") == "1"
    if os.getenv("VERCEL") and not remote_url and writable:
        raise RuntimeError("Vercel contribution writes require a remote database")

    @asynccontextmanager
    async def lifespan(app):
        if remote_url:
            from postgres_corpus import PostgresCorpus
            app.state.corpus = PostgresCorpus(remote_url)
        else:
            app.state.corpus = Corpus(db_path)
        app.state.data_errors = []
        candidates = [data_dir / "ede_yoruba_rich.json", data_dir / "ede_yoruba_rich_enhanced.json",
                      data_dir / "ede_master.json", data_dir / "ede_word_sense.json",
                      ROOT / "ede_yoruba_rich.json", ROOT / "ede_master.json", ROOT / "ede_word_sense.json"]
        for path in dict.fromkeys(candidates):
            if path.is_file():
                try:
                    app.state.corpus.import_file(path)
                except (ValueError, KeyError, TypeError, OSError) as error:
                    logger.exception("Corpus import failed: %s", path.name)
                    app.state.data_errors.append(path.name)
        lexical_path = data_dir / "yoruba-lexicon.jsonl"
        if lexical_path.is_file():
            from lexicon import import_snapshot
            try:
                import_snapshot(app.state.corpus, lexical_path)
            except (ValueError, KeyError, TypeError, OSError):
                logger.error("Dictionary snapshot import failed")
                app.state.data_errors.append(lexical_path.name)
        yield

    app = FastAPI(title="Ede Yoruba Corpus API", version="0.4.0", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def headers(request, call_next):
        if request.method == "POST" and request.headers.get("content-length", "0").isdigit():
            if int(request.headers.get("content-length", "0")) > 16000:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        if request.method == "POST":
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 16000:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self' data:; base-uri 'none'; object-src 'none'; frame-ancestors 'self' https://huggingface.co")
        if request.url.path.startswith(("/contribute", "/review")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    @app.get("/app", include_in_schema=False)
    def index():
        return FileResponse(ROOT / "index.html")

    @app.get("/static/{name}", include_in_schema=False)
    def static(name: Literal["app.js", "style.css"]):
        return FileResponse(ROOT / "static" / name)

    @app.get("/attribution", include_in_schema=False)
    def attribution():
        return FileResponse(ROOT / "NOTICE.md", media_type="text/plain")

    @app.get("/stats")
    def stats(request: Request):
        data = request.app.state.corpus.stats()
        return {**data, "data_errors": request.app.state.data_errors,
                "contributions_enabled": writable, "moderation_configured": bool(review_token),
                "storage_note": "Submissions are stored in the server database." if writable else
                    "Submissions are disabled until persistent storage is configured."}

    @app.get("/health")
    def health(request: Request):
        stats = request.app.state.corpus.stats()
        return {"status": "ready" if stats["ready"] else "no_data",
                "data_errors": request.app.state.data_errors,
                "contributions_enabled": writable}

    @app.get("/search")
    def search(request: Request, q: str = Query(min_length=1, max_length=500),
               kind: Literal["all", "word", "phrase"] = "all", limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0, le=1000000)):
        if not q.strip():
            raise HTTPException(422, "Enter a word or phrase")
        return request.app.state.corpus.search(q, limit, offset, kind)

    @app.get("/browse")
    def browse(request: Request, kind: Literal["all", "word", "phrase"] = "word",
               limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0, le=1000000)):
        return request.app.state.corpus.search("", limit, offset, kind)

    @app.get("/dictionary/headwords")
    def dictionary_index(request: Request, prefix: str = Query(default="", max_length=100),
                         limit: int = Query(default=30, ge=1, le=100), offset: int = Query(default=0, ge=0, le=1000000)):
        from lexicon import headwords
        return headwords(request.app.state.corpus, prefix, limit, offset)

    @app.get("/dictionary/word")
    def dictionary_word(request: Request, headword: str = Query(min_length=1, max_length=500)):
        from lexicon import word
        result = word(request.app.state.corpus, headword)
        if not result["senses"]:
            raise HTTPException(404, "No sourced dictionary headword found; tone marks and underdots are preserved")
        return result

    @app.get("/dictionary/coverage")
    def dictionary_coverage(request: Request):
        from lexicon import coverage
        return coverage(request.app.state.corpus)

    @app.get("/search-suggestions")
    def suggestions(request: Request, q: str = Query(max_length=100), limit: int = Query(default=5, ge=1, le=10)):
        if len(q.strip()) < 2:
            return {"suggestions": []}
        rows = request.app.state.corpus.search(q, limit)["entries"]
        return {"suggestions": list(dict.fromkeys(r["english"] for r in rows))}

    @app.get("/word-sense")
    def word_sense(request: Request, word: str = Query(min_length=1, max_length=500)):
        result = request.app.state.corpus.search(word)
        return {"found": bool(result["entries"]), "word": word, "entries": result["entries"],
                "results": {"Yoruba": result["entries"]}, "total": result["total"]}

    @app.get("/translate")
    def translate(request: Request, word: str = Query(min_length=1, max_length=500)):
        # Compatibility endpoint: corpus matches, not generated sentence translation.
        result = request.app.state.corpus.search(word)
        return {"found": bool(result["entries"]), "word": word, "entries": result["entries"],
                "notice": "These are corpus matches, not generated translations."}

    @app.post("/contribute", status_code=201)
    def contribute(request: Request, contribution: Contribution):
        if not writable:
            raise HTTPException(503, "Persistent storage is not configured. Your submission has not been saved.")
        host = request.client.host if request.client else "unknown"
        if os.getenv("VERCEL"):
            host = request.headers.get("x-vercel-forwarded-for") or host
        client_key = hashlib.sha256(host.encode()).hexdigest()
        try:
            if not request.app.state.corpus.allow_submission(client_key):
                raise HTTPException(429, "Too many submissions. Try again in ten minutes.")
            result = request.app.state.corpus.contribute(contribution.model_dump())
        except (sqlite3.Error, psycopg.Error):
            logger.error("Contribution database operation failed")
            raise HTTPException(503, "Could not save your submission. Please try again.")
        return {"success": True, **result, "message": "Saved for review. This is not yet a verified dictionary entry."}

    def authorize(authorization):
        if not review_token:
            raise HTTPException(503, "Review access is not configured")
        if not hmac.compare_digest(authorization.encode(), ("Bearer " + review_token).encode()):
            raise HTTPException(401, "Review authorization required")

    @app.get("/review/contributions")
    def queue(request: Request, authorization: str = Header(default=""),
              limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        authorize(authorization)
        return {"contributions": request.app.state.corpus.queue(limit, offset)}

    @app.post("/review/contributions/{ident}")
    def review(ident: str, decision: Review, request: Request, authorization: str = Header(default="")):
        authorize(authorization)
        if not writable:
            raise HTTPException(503, "Persistent storage is not configured")
        try:
            return request.app.state.corpus.review(ident, decision.approve)
        except ValueError as error:
            raise HTTPException(404, str(error))

    @app.get("/review/senses")
    def source_queue(request: Request, authorization: str = Header(default=""), q: str = Query(default="", max_length=500),
                     limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        authorize(authorization)
        from lexicon import queue
        return {"senses": queue(request.app.state.corpus, limit, offset, q)}

    @app.post("/review/senses/{ident}")
    def source_review(ident: str, decision: Review, request: Request, authorization: str = Header(default="")):
        authorize(authorization)
        if not writable:
            raise HTTPException(503, "Persistent storage is not configured")
        from lexicon import review
        try:
            return review(request.app.state.corpus, ident, decision.approve)
        except ValueError as error:
            raise HTTPException(404, str(error))

    return app


app = create_app()
