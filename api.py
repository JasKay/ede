from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date
import json
import os

app = FastAPI(title="Ede API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Load data at startup
yoruba_rich = {}
word_sense_db = {}
contributions = {}

@app.on_event("startup")
async def load_data():
    global yoruba_rich, word_sense_db, contributions
    
    print("Loading datasets...")
    
    # Try to load rich Yoruba data (may not exist on HF Spaces)
    try:
        with open("ede_yoruba_rich.json", "r", encoding="utf-8") as f:
            yoruba_rich = json.load(f)
        print(f"Loaded {len(yoruba_rich)} Yoruba phrases (rich)")
    except FileNotFoundError:
        print("ede_yoruba_rich.json not found, will fall back to word_sense")
        yoruba_rich = {}
    
    # Load word sense (always available)
    try:
        with open("ede_word_sense.json", "r", encoding="utf-8") as f:
            word_sense_db = json.load(f)
        print(f"Loaded {len(word_sense_db)} word sense entries")
    except FileNotFoundError:
        print("ede_word_sense.json not found")
    
    # If rich not available, use word_sense as fallback
    if not yoruba_rich and word_sense_db:
        yoruba_rich = word_sense_db
        print("Using word_sense as fallback for searches")
    
    print("Loading contributions.json...")
    try:
        with open("contributions.json", "r", encoding="utf-8") as f:
            contributions = json.load(f)
        print(f"Loaded {len(contributions)} contributions")
    except FileNotFoundError:
        contributions = []

@app.get("/")
def root():
    return FileResponse("index.html", media_type="text/html")

@app.get("/app")
def app_route():
    return FileResponse("index.html", media_type="text/html")

@app.get("/stats")
def stats():
    try:
        with open("ede_master.json", "r", encoding="utf-8") as f:
            master_data = json.load(f)
        
        total = len(master_data)
        
        domains = {}
        for entry in master_data:
            domain = entry.get("domain", "general")
            domains[domain] = domains.get(domain, 0) + 1
        
        languages = {}
        for entry in master_data:
            lang = entry.get("target_language", "Unknown")
            languages[lang] = languages.get(lang, 0) + 1
        
        return {
            "total_entries": total,
            "domains": domains,
            "languages": languages,
            "contributions": len(contributions) if isinstance(contributions, list) else 0
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/search-suggestions")
def search_suggestions(q: str, limit: int = 8):
    q_lower = q.lower().strip()
    
    if not q_lower or len(q_lower) < 2:
        return {"suggestions": []}
    
    try:
        suggestions = []
        for phrase in yoruba_rich.keys():
            if q_lower in phrase.lower():
                suggestions.append(phrase)
        
        suggestions.sort(key=lambda x: (not x.lower().startswith(q_lower), len(x)))
        
        return {"suggestions": suggestions[:limit]}
    except Exception as e:
        return {"suggestions": [], "error": str(e)}

@app.get("/word-sense")
def word_sense(word: str):
    word_lower = word.lower().strip()
    
    if not word_lower:
        return {"found": False, "error": "No word provided"}
    
    try:
        # EXACT MATCH FIRST
        if word_lower in yoruba_rich:
            word_data = yoruba_rich[word_lower]
            return {
                "found": True,
                "type": "exact",
                "word": word_data["word"],
                "definitions": word_data.get("definitions", [])
            }
        
        # PHRASE MATCH - Find phrases containing the word
        phrase_matches = []
        for phrase, data in yoruba_rich.items():
            if word_lower in phrase.lower():
                phrase_matches.append({
                    "phrase": phrase,
                    "translations": data.get("definitions", [{}])[0].get("translations", [])
                })
        
        if phrase_matches:
            phrase_matches.sort(key=lambda x: len(x["phrase"]))
            
            return {
                "found": True,
                "type": "phrase_match",
                "word": word,
                "message": f"'{word}' found in these phrases",
                "matches": phrase_matches[:10]
            }
        
        # NOT FOUND
        return {
            "found": False,
            "word": word,
            "contribution_needed": True,
            "missing_languages": ["Yoruba", "Swahili", "Xhosa", "Tamazight"]
        }
    
    except Exception as e:
        return {"found": False, "error": str(e)}

@app.post("/contribute")
def contribute(word: str, language: str, translation: str, username: str = "Anonymous"):
    try:
        contributions_file = "contributions.json"
        if os.path.exists(contributions_file):
            with open(contributions_file, "r", encoding="utf-8") as f:
                contribs = json.load(f)
        else:
            contribs = []
        
        new_contribution = {
            "id": int(date.today().timestamp() * 1000),
            "username": username,
            "word": word,
            "translation": translation,
            "language": language,
            "votes": 0,
            "timestamp": str(date.today())
        }
        
        contribs.append(new_contribution)
        
        with open(contributions_file, "w", encoding="utf-8") as f:
            json.dump(contribs, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Contribution saved"}
    except Exception as e:
        return {"success": False, "error": str(e)}
