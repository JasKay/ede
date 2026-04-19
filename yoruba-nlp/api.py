from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import json

app = FastAPI(title="Ede API", description="Unified African Language Dataset API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine("sqlite:///ede.db", echo=False)

@app.get("/app")
def frontend():
    return FileResponse("index.html")

@app.get("/")
def root():
    return {
        "name": "Ede",
        "description": "Unified African Language Dataset API",
        "version": "0.1.0",
        "entries": 132880
    }

@app.get("/search")
def search(
    q: str = Query(..., description="Search term"),
    source_language: str = Query(None, description="Filter by source language"),
    target_language: str = Query(None, description="Filter by target language"),
    domain: str = Query(None, description="Filter by domain"),
    limit: int = Query(10, description="Number of results")
):
    with Session(engine) as session:
        sql = "SELECT * FROM entries WHERE (source_text LIKE :q OR target_text LIKE :q)"
        params = {"q": f"%{q}%"}

        if source_language:
            sql += " AND source_language = :source_language"
            params["source_language"] = source_language

        if target_language:
            sql += " AND target_language = :target_language"
            params["target_language"] = target_language

        if domain:
            sql += " AND domain = :domain"
            params["domain"] = domain

        sql += " LIMIT :limit"
        params["limit"] = limit

        results = session.execute(text(sql), params).fetchall()

        return {
            "query": q,
            "count": len(results),
            "results": [
                {
                    "id": r[0],
                    "source_language": r[1],
                    "source_text": r[2],
                    "target_language": r[3],
                    "target_text": r[4],
                    "domain": r[8],
                    "sources": json.loads(r[9]),
                    "verified_by": r[10],
                    "verification_score": r[11]
                }
                for r in results
            ]
        }

@app.get("/stats")
def stats():
    with Session(engine) as session:
        total = session.execute(text("SELECT COUNT(*) FROM entries")).scalar()
        domains = session.execute(text("SELECT domain, COUNT(*) FROM entries GROUP BY domain")).fetchall()
        languages = session.execute(text("SELECT target_language, COUNT(*) FROM entries GROUP BY target_language")).fetchall()

        return {
            "total_entries": total,
            "domains": {d[0]: d[1] for d in domains},
            "languages": {l[0]: l[1] for l in languages}
        }
