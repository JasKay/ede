from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import date
import json
import os

app = FastAPI(title="Ede API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global data storage
yoruba_rich = {}
swahili_rich = {}
xhosa_rich = {}
tamazight_rich = {}
word_sense_db = {}
contributions = {}

@app.on_event("startup")
async def load_data():
    global yoruba_rich, swahili_rich, xhosa_rich, tamazight_rich, word_sense_db, contributions
    
    print("Loading datasets...")
    
    # Try to load all 4 rich datasets (will work locally, fail gracefully on HF)
    for lang_file, lang_var in [
        ("ede_yoruba_rich.json", "yoruba_rich"),
        ("ede_swahili_rich.json", "swahili_rich"),
        ("ede_xhosa_rich.json", "xhosa_rich"),
        ("ede_tamazight_rich.json", "tamazight_rich")
    ]:
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                globals()[lang_var] = data
                print(f"✓ Loaded {len(data)} entries from {lang_file}")
        except FileNotFoundError:
            print(f"⚠ {lang_file} not found (ok on HF Spaces)")
            globals()[lang_var] = {}
    
    # Load word_sense (always available, fallback for HF)
    try:
        with open("ede_word_sense.json", "r", encoding="utf-8") as f:
            word_sense_db = json.load(f)
        print(f"✓ Loaded {len(word_sense_db)} word sense entries")
    except FileNotFoundError:
        print("⚠ ede_word_sense.json not found")
    
    # Load contributions
    try:
        with open("contributions.json", "r", encoding="utf-8") as f:
            contributions = json.load(f)
        print(f"✓ Loaded {len(contributions)} contributions")
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
        return {"error": str(e), "contributions": 0}

@app.get("/search-suggestions")
def search_suggestions(q: str, limit: int = 5):
    q_lower = q.lower().strip()
    
    if not q_lower or len(q_lower) < 2:
        return {"suggestions": []}
    
    try:
        suggestions = []
        
        # Search all 4 languages
        for lang_data in [yoruba_rich, swahili_rich, xhosa_rich, tamazight_rich]:
            if not lang_data:
                continue
            for phrase in lang_data.keys():
                if q_lower in phrase.lower():
                    suggestions.append(phrase)
        
        # Remove duplicates and sort
        suggestions = list(set(suggestions))
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
        all_definitions = []
        found_languages = []
        
        # Search all 4 languages (rich datasets)
        for lang_data, lang_name in [
            (yoruba_rich, "Yoruba"),
            (swahili_rich, "Swahili"),
            (xhosa_rich, "Xhosa"),
            (tamazight_rich, "Tamazight")
        ]:
            if not lang_data:
                continue
            
            if word_lower in lang_data:
                word_data = lang_data[word_lower]
                if "definitions" in word_data:
                    definitions = word_data.get("definitions", [])
                    for d in definitions:
                        if "language" not in d:
                            d["language"] = lang_name
                    all_definitions.extend(definitions)
                    found_languages.append(lang_name)
        
        # If found in any language
        if all_definitions:
            return {
                "found": True,
                "type": "exact",
                "word": word_lower,
                "definitions": all_definitions,
                "found_in": found_languages
            }
        
        # Fallback: check word_sense (for HF Spaces)
        if word_sense_db and word_lower in word_sense_db:
            word_data = word_sense_db[word_lower]
            definitions = [{
                "id": f"{word_lower}_001",
                "definition": word,
                "part_of_speech": "word",
                "translations": [
                    {
                        "language": item["l"],
                        "word": item["w"],
                        "confidence": item.get("c", 0.8),
                        "frequency": item.get("f", 1),
                        "domain": "general",
                        "intent": "informing",
                        "expression_mode": "literal",
                        "formality": "neutral",
                        "code_switching": False,
                        "synonyms": [],
                        "context": ["general"],
                        "example": word,
                        "sources": []
                    }
                    for item in word_data.get("t", [])
                ],
                "sources": []
            }]
            return {
                "found": True,
                "type": "exact",
                "word": word_lower,
                "definitions": definitions,
                "found_in": [t["language"] for t in definitions[0]["translations"]]
            }
        
        # PHRASE MATCH across all languages
        phrase_matches = []
        for lang_data, lang_name in [
            (yoruba_rich, "Yoruba"),
            (swahili_rich, "Swahili"),
            (xhosa_rich, "Xhosa"),
            (tamazight_rich, "Tamazight")
        ]:
            if not lang_data:
                continue
            for phrase, data in lang_data.items():
                if word_lower in phrase.lower():
                    translations = data.get("definitions", [{}])[0].get("translations", [])
                    phrase_matches.append({
                        "phrase": phrase,
                        "language": lang_name,
                        "translations": translations
                    })
        
        if phrase_matches:
            phrase_matches.sort(key=lambda x: len(x["phrase"]))
            return {
                "found": True,
                "type": "phrase_match",
                "word": word,
                "matches": phrase_matches[:10]
            }
        
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
            "upvoters": [],
            "timestamp": str(date.today())
        }
        
        contribs.append(new_contribution)
        
        with open(contributions_file, "w", encoding="utf-8") as f:
            json.dump(contribs, f, ensure_ascii=False, indent=2)
        
        return {"success": True, "message": "Contribution saved"}
    except Exception as e:
        return {"success": False, "error": str(e)}
