import json
from collections import defaultdict

print("Loading Yoruba datasets...")

# Load datasets
with open("data/yoruba/ede_yoruba_helsinki.json", "r", encoding="utf-8") as f:
    helsinki = json.load(f)

with open("data/yoruba/ede_yoruba_mt560.json", "r", encoding="utf-8") as f:
    mt560 = json.load(f)

all_entries = helsinki + mt560
print(f"Loaded {len(all_entries)} total entries\n")

# Group by English word
words = defaultdict(lambda: {
    "definitions": defaultdict(lambda: {
        "translations": [],
        "sources": set()
    })
})

for entry in all_entries:
    source_word = entry["source_text"].lower().strip()
    target_word = entry["target_text"].lower().strip()
    
    if not source_word or not target_word:
        continue
    
    def_id = source_word.replace(" ", "_")[:50]
    
    translation = {
        "language": "Yoruba",
        "word": target_word,
        "confidence": 0.9 if "Helsinki" in str(entry["sources"]) else 0.85,
        "frequency": 1,
        "domain": entry.get("domain", "general"),
        "intent": "informing",
        "expression_mode": "literal",
        "formality": "neutral",
        "code_switching": False,
        "synonyms": [],
        "context": [entry.get("domain", "general")],
        "example": entry["source_text"],
        "sources": entry["sources"]
    }
    
    words[source_word]["definitions"][def_id]["translations"].append(translation)
    words[source_word]["definitions"][def_id]["sources"].update(entry["sources"])

# Build final structure
yoruba_rich = {}

for word, data in words.items():
    definitions = []
    
    for def_id, def_data in data["definitions"].items():
        definitions.append({
            "id": f"{def_id}_001",
            "definition": word,
            "part_of_speech": "phrase",
            "translations": def_data["translations"],
            "sources": list(def_data["sources"])
        })
    
    yoruba_rich[word] = {
        "word": word,
        "language": "English",
        "definitions": definitions
    }

# Save
with open("ede_yoruba_rich.json", "w", encoding="utf-8") as f:
    json.dump(yoruba_rich, f, ensure_ascii=False, indent=2)

print(f"Created {len(yoruba_rich)} unique English words")
print(f"✓ Saved to ede_yoruba_rich.json")
