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
    
    print("Loading enhanced datasets...")
    
    # Try enhanced first, fall back to rich
    for lang_file, lang_var, lang_name in [
        ("ede_yoruba_rich_enhanced.json", "yoruba_rich", "Yoruba"),
        ("ede_swahili_rich_enhanced.json", "swahili_rich", "Swahili"),
        ("ede_xhosa_rich_enhanced.json", "xhosa_rich", "Xhosa"),
        ("ede_tamazight_rich_enhanced.json", "tamazight_rich", "Tamazight")
    ]:
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                globals()[lang_var] = data
                print(f"✓ Loaded {len(data)} enhanced {lang_name} entries")
        except FileNotFoundError:
            # Fall back to non-enhanced
            fallback_file = lang_file.replace("_enhanced", "")
            try:
                with open(fallback_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    globals()[lang_var] = data
                    print(f"✓ Loaded {len(data)} {lang_name} entries (non-enhanced)")
            except:
                print(f"⚠ {lang_name} not found")
                globals()[lang_var] = {}
    
    # Load word_sense
    try:
        with open("ede_word_sense.json", "r", encoding="utf-8") as f:
            word_sense_db = json.load(f)
    except:
        pass
    
    # Load contributions
    try:
        with open("contributions.json", "r", encoding="utf-8") as f:
            contributions = json.load(f)
    except:
        contributions = []

@app.get("/")
def root():
    return FileResponse("index.html", media_type="text/html")

@app.get("/app")
def app_route():
    return FileResponse("index.html", media_type="text/html")

@app.get("/chat")
def chat(message: str):
    msg_lower = message.lower().strip()
    
    # Extract intent and word
    intents = {
        "how do i say": "translate",
        "what's the": "translate",
        "translate": "translate",
        "plural of": "plural",
        "plural for": "plural",
        "conjugate": "conjugate",
        "past tense": "conjugate",
        "examples of": "examples",
        "example of": "examples",
    }
    
    intent = None
    word = None
    
    for trigger, detected_intent in intents.items():
        if trigger in msg_lower:
            intent = detected_intent
            # Extract word after trigger
            idx = msg_lower.find(trigger) + len(trigger)
            word = msg_lower[idx:].strip().rstrip("?").strip()
            break
    
    if not intent or not word:
        return {
            "response": "I can help you translate words between English and African languages (Yoruba, Swahili, Xhosa, Tamazight). Try:\n• 'How do I say person?'\n• 'Plural of person'\n• 'Conjugate walk'\n• 'Examples of person'"
        }
    
    try:
        # Find word in datasets
        for lang_name, lang_data in [
            ("Yoruba", yoruba_rich),
            ("Swahili", swahili_rich),
            ("Xhosa", xhosa_rich),
            ("Tamazight", tamazight_rich)
        ]:
            if not lang_data or word not in lang_data:
                continue
            
            entry = lang_data[word]
            definition = entry['definitions'][0]
            trans = definition['translations'][0] if definition['translations'] else None
            
            if not trans:
                continue
            
            if intent == "translate":
                response = f"The {lang_name} word for '{word}' is **{trans['word']}** (confidence: {int(trans.get('confidence', 0.85) * 100)}%)"
                if trans.get('examples'):
                    ex = trans['examples'][0]
                    response += f"\n\nExample: \"{ex['english']}\" → \"{ex.get(lang_name.lower(), trans['word'])}\""
                return {"response": response}
            
            elif intent == "plural":
                plural = definition.get('conjugations', {}).get('plural', 'Not available')
                response = f"Plural of '{word}' in {lang_name}: **{plural}**"
                return {"response": response}
            
            elif intent == "conjugate":
                conj = definition.get('conjugations', {})
                if not conj:
                    return {"response": f"Conjugation data not available for '{word}'"}
                response = f"Conjugations of '{word}':\n"
                for form, value in conj.items():
                    response += f"• {form}: **{value}**\n"
                return {"response": response}
            
            elif intent == "examples":
                examples = trans.get('examples', [])
                if not examples:
                    return {"response": f"No examples available for '{word}'"}
                response = f"Examples with '{word}':\n"
                for i, ex in enumerate(examples[:3], 1):
                    response += f"{i}. \"{ex['english']}\" → \"{ex.get(lang_name.lower(), trans['word'])}\"\n"
                return {"response": response}
        
        return {"response": f"Sorry, I couldn't find '{word}' in my database. Would you like to add it?"}
    
    except Exception as e:
        return {"response": f"Error: {str(e)}"}


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
def search_suggestions(q: str, limit: int = 3):
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

@app.get("/translate")
def translate(word: str):
    word_lower = word.lower().strip()
    
    if not word_lower:
        return {"found": False}
    
    results = {
        "Yoruba": None,
        "Swahili": None,
        "Xhosa": None,
        "Tamazight": None
    }
    
    try:
        for lang_name, lang_data in [
            ("Yoruba", yoruba_rich),
            ("Swahili", swahili_rich),
            ("Xhosa", xhosa_rich),
            ("Tamazight", tamazight_rich)
        ]:
            if not lang_data or word_lower not in lang_data:
                results[lang_name] = None
                continue
            
            entry = lang_data[word_lower]
            definition = entry['definitions'][0]
            
            if not definition['translations']:
                results[lang_name] = None
                continue
            
            trans = definition['translations'][0]
            
            results[lang_name] = {
                "word": trans['word'],
                "confidence": trans.get('confidence', 0.85),
                "pos": definition.get('pos_tag', 'NN'),
                "examples": trans.get('examples', []),
                "conjugations": definition.get('conjugations', {}),
                "sources": trans.get('sources', [])
            }
        
        found_any = any(v is not None for v in results.values())
        
        return {
            "found": found_any,
            "word": word_lower,
            "results": results
        }
    
    except Exception as e:
        return {"found": False, "error": str(e)}


@app.get("/word-sense")
def word_sense(word: str):
    word_lower = word.lower().strip()
    
    if not word_lower:
        return {"found": False, "error": "No word provided"}
    
    try:
        results = {
            "Yoruba": [],
            "Swahili": [],
            "Xhosa": [],
            "Tamazight": []
        }
        
        # Search all 4 languages
        lang_map = {
            "Yoruba": yoruba_rich,
            "Swahili": swahili_rich,
            "Xhosa": xhosa_rich,
            "Tamazight": tamazight_rich
        }
        
        found_any = False
        
        for lang_name, lang_data in lang_map.items():
            if not lang_data:
                continue
            
            if word_lower in lang_data:
                word_data = lang_data[word_lower]
                if "definitions" in word_data:
                    definitions = word_data.get("definitions", [])
                    for d in definitions:
                        if "language" not in d:
                            d["language"] = lang_name
                    results[lang_name].extend(definitions)
                    found_any = True
        
        # Fallback to word_sense for HF Spaces
        if not found_any and word_sense_db and word_lower in word_sense_db:
            word_data = word_sense_db[word_lower]
            for item in word_data.get("t", []):
                lang = item["l"]
                if lang in results:
                    results[lang].append({
                        "id": f"{word_lower}_001",
                        "definition": word,
                        "translations": [{
                            "language": lang,
                            "word": item["w"],
                            "confidence": item.get("c", 0.8),
                            "frequency": item.get("f", 1),
                            "domain": "general"
                        }]
                    })
                    found_any = True
        
        if found_any:
            return {
                "found": True,
                "type": "exact",
                "word": word_lower,
                "results": results
            }
        
        # Not found - return empty results for all languages
        return {
            "found": False,
            "word": word,
            "results": results,
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
