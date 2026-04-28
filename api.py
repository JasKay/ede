from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date
import json
import os
from datetime import datetime


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
    try:
        with open("ede_master.json", "r", encoding="utf-8") as f:
            master_data = json.load(f)
        
        total = len(master_data)
        
        # Count domains
        domains = {}
        for entry in master_data:
            domain = entry.get("domain", "general")
            domains[domain] = domains.get(domain, 0) + 1
        
        # Count languages
        languages = {}
        for entry in master_data:
            lang = entry.get("target_language", "Unknown")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "total_entries": total,
            "domains": domains,
            "languages": languages,
            "contributions": 0
        }
    except Exception as e:
        return {"error": str(e)}

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
def contribute(word: str, language: str, translation: str, username: str = "Anonymous"):
    try:
        # Load existing contributions
        contributions_file = "contributions.json"
        if os.path.exists(contributions_file):
            with open(contributions_file, "r", encoding="utf-8") as f:
                contributions = json.load(f)
        else:
            contributions = []
        
        # Add new contribution
        new_contribution = {
            "id": int(datetime.now().timestamp() * 1000),
            "username": username,
            "word": word,
            "translation": translation,
            "language": language,
            "votes": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        contributions.append(new_contribution)
        
        # Save to file
        with open(contributions_file, "w", encoding="utf-8") as f:
            json.dump(contributions, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Contribution saved"}
    except Exception as e:
        return {"success": False, "error": str(e)}
