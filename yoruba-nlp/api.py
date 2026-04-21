from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date
import json

app = FastAPI(title="Ede API", description="Unified African Language Dataset API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load word sense data at startup
try:
    with open("ede_word_sense.json", "r", encoding="utf-8") as f:
        word_sense_db = json.load(f)
except FileNotFoundError:
    print("Warning: ede_word_sense.json not found.")
    word_sense_db = {}

@app.get("/app")
def frontend():
    return FileResponse("index.html")

@app.get("/")
def frontend_root():
    return FileResponse("index.html")

@app.get("/stats")
def stats():
    return {
        "total_entries": 1693776,
        "domains": {
            "conversational": 121311,
            "multi-domain": 9991,
            "software-ui": 1578,
            "general": 1560196
        },
        "languages": {
            "Yoruba": 132880,
            "Swahili": 563294,
            "Xhosa": 993668,
            "Tamazight": 6194
        }
    }

@app.get("/word-sense")
def word_sense(word: str = Query(..., description="English word to look up")):
    word_clean = word.lower().strip()
    
    if word_clean not in word_sense_db:
        return {
            "word": word,
            "found": False,
            "translations": [],
            "missing_languages": ["Yoruba", "Swahili", "Xhosa", "Tamazight"],
            "message": "Word not found in our high-confidence set. Help us translate it!"
        }
    
    entry = word_sense_db[word_clean]
    
    # Expand short keys back to full format for frontend
    translations = []
    for trans in entry.get("t", []):
        translations.append({
            "language": trans["l"],
            "word": trans["w"],
            "confidence": trans["c"],
            "frequency": trans["f"]
        })
    
    translations = sorted(translations, key=lambda x: x["confidence"], reverse=True)
    
    # Find which languages have this word
    languages_with_translation = {t["language"] for t in translations}
    all_languages = ["Yoruba", "Swahili", "Xhosa", "Tamazight"]
    missing_languages = [l for l in all_languages if l not in languages_with_translation]
    
    return {
        "word": entry["word"],
        "language": "English",
        "found": True,
        "total_translations": len(translations),
        "translations": translations,
        "missing_languages": missing_languages,
        "contribution_needed": len(missing_languages) > 0
    }

@app.post("/contribute")
def contribute(word: str = Query(...), language: str = Query(...), translation: str = Query(...)):
    """User submits a missing translation"""
    contribution = {
        "word": word.lower().strip(),
        "language": language,
        "translation": translation.strip(),
        "timestamp": str(date.today())
    }
    
    # Load existing contributions
    try:
        with open("contributions.json", "r", encoding="utf-8") as f:
            contributions = json.load(f)
    except FileNotFoundError:
        contributions = []
    
    # Add new contribution
    contributions.append(contribution)
    
    # Save
    with open("contributions.json", "w", encoding="utf-8") as f:
        json.dump(contributions, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "received",
        "message": f"Thank you! Your translation '{translation}' for '{word}' in {language} has been submitted."
    }
