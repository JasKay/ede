from datasets import load_dataset
import json
from collections import defaultdict

print("=" * 70)
print("BUILDING EDE YORUBA DATASET - COMPREHENSIVE INGESTION")
print("=" * 70 + "\n")

# STEP 1: Load base datasets (Helsinki + MT560)
print("STEP 1: Loading base datasets (Helsinki + MT560)...\n")

with open("data/yoruba/ede_yoruba_helsinki.json", "r", encoding="utf-8") as f:
    helsinki = json.load(f)

with open("data/yoruba/ede_yoruba_mt560.json", "r", encoding="utf-8") as f:
    mt560 = json.load(f)

print(f"  Helsinki: {len(helsinki)} entries")
print(f"  MT560: {len(mt560)} entries")
print(f"  Total: {len(helsinki) + len(mt560)} entries\n")

# STEP 2: Transform to rich format
print("STEP 2: Transforming to rich Yoruba format...\n")

all_entries = helsinki + mt560
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

print(f"  Transformed to {len(yoruba_rich)} unique words\n")

# STEP 3: Add Dolly dataset
print("STEP 3: Adding Dolly English-Yoruba dataset...\n")

try:
    ds = load_dataset('ccibeekeoc42/DollyHHRLHF_yoruba', split='train')
    print(f"  Found {len(ds)} entries")
    
    dolly_added = 0
    for example in ds:
        eng = (example.get('Prompt_English', '') + ' ' + example.get('Response_English', '')).lower().strip()
        yor = (example.get('Prompt_Yoruba', '') + ' ' + example.get('Response_Yoruba', '')).strip()
        
        if not eng or not yor or len(eng) < 3:
            continue
        
        if eng not in yoruba_rich:
            yoruba_rich[eng] = {
                "word": eng,
                "language": "English",
                "definitions": [{
                    "id": f"{eng.replace(' ', '_')[:50]}_001",
                    "definition": eng,
                    "part_of_speech": "phrase",
                    "translations": [],
                    "sources": []
                }]
            }
        
        exists = any(
            t['word'] == yor and t['language'] == 'Yoruba'
            for d in yoruba_rich[eng]['definitions']
            for t in d['translations']
        )
        
        if not exists:
            yoruba_rich[eng]['definitions'][0]['translations'].append({
                "language": "Yoruba",
                "word": yor,
                "confidence": 0.87,
                "frequency": 1,
                "domain": "general",
                "intent": "informing",
                "expression_mode": "literal",
                "formality": "neutral",
                "code_switching": False,
                "synonyms": [],
                "context": ["general"],
                "example": eng,
                "sources": ["dolly"]
            })
            dolly_added += 1
    
    print(f"  Added {dolly_added} new entries from Dolly\n")
except Exception as e:
    print(f"  ✗ Error loading Dolly: {e}\n")

# STEP 4: Try additional datasets
print("STEP 4: Attempting additional datasets...\n")

additional = [
    ("bytel0rd/yoruba_audio_translated", "audio"),
    ("ccibeekeoc42/TinyStories_yoruba", "tinystories"),
]

for dataset_id, name in additional:
    try:
        print(f"  Loading {name}...")
        ds = load_dataset(dataset_id, split='train', streaming=False)
        print(f"    Found {len(ds)} entries")
        
        added = 0
        for example in ds:
            eng = example.get('english', example.get('source', example.get('text', '')))
            yor = example.get('yoruba', example.get('target', example.get('translation', '')))
            
            if isinstance(eng, dict):
                eng = str(eng.get('en', eng.get('English', '')))
            if isinstance(yor, dict):
                yor = str(yor.get('yo', yor.get('Yoruba', '')))
            
            eng = str(eng).lower().strip()
            yor = str(yor).strip()
            
            if not eng or not yor or len(eng) < 2:
                continue
            
            if eng not in yoruba_rich:
                yoruba_rich[eng] = {
                    "word": eng,
                    "language": "English",
                    "definitions": [{
                        "id": f"{eng.replace(' ', '_')[:50]}_001",
                        "definition": eng,
                        "part_of_speech": "phrase",
                        "translations": [],
                        "sources": []
                    }]
                }
            
            exists = any(
                t['word'] == yor and t['language'] == 'Yoruba'
                for d in yoruba_rich[eng]['definitions']
                for t in d['translations']
            )
            
            if not exists:
                yoruba_rich[eng]['definitions'][0]['translations'].append({
                    "language": "Yoruba",
                    "word": yor,
                    "confidence": 0.84,
                    "frequency": 1,
                    "domain": "general",
                    "intent": "informing",
                    "expression_mode": "literal",
                    "formality": "neutral",
                    "code_switching": False,
                    "synonyms": [],
                    "context": ["general"],
                    "example": eng,
                    "sources": [name]
                })
                added += 1
        
        print(f"    Added {added} new entries\n")
    except Exception as e:
        print(f"  ✗ Error loading {name}: {str(e)[:100]}\n")

# STEP 5: Save rich Yoruba dataset
print("STEP 5: Saving ede_yoruba_rich.json...\n")

with open("ede_yoruba_rich.json", "w", encoding="utf-8") as f:
    json.dump(yoruba_rich, f, ensure_ascii=False, indent=2)

print(f"  ✓ Saved {len(yoruba_rich)} unique words\n")

# STEP 6: Create ede_master.json
print("STEP 6: Creating ede_master.json...\n")

ede_master = []
for word_entry in yoruba_rich.values():
    for definition in word_entry['definitions']:
        for translation in definition['translations']:
            ede_master.append({
                "source_text": word_entry['word'],
                "target_text": translation['word'],
                "source_language": word_entry['language'],
                "target_language": translation['language'],
                "domain": translation['domain'],
                "sources": translation['sources']
            })

with open("ede_master.json", "w", encoding="utf-8") as f:
    json.dump(ede_master, f, ensure_ascii=False)

print(f"  ✓ Created with {len(ede_master)} total entries\n")

# STEP 7: Create word sense (simple cross-language)
print("STEP 7: Creating ede_word_sense.json (simple format)...\n")

translation_map = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for entry in ede_master:
    source = entry['source_text'].lower().strip()
    target = entry['target_text'].lower().strip()
    target_lang = entry['target_language']
    
    translation_map[source][target_lang][target].append(entry)

word_entries = {}

for source_word, langs in translation_map.items():
    has_multiple_langs = len(langs) >= 2
    has_good_frequency = any(
        max(len(entries_list) for entries_list in targets.values()) >= 2
        for targets in langs.values()
    )
    
    if not (has_multiple_langs or has_good_frequency):
        continue
    
    translations = []
    for target_lang, targets in langs.items():
        for target_word, entries_list in targets.items():
            frequency = len(entries_list)
            confidence = min(0.99, frequency / 10.0)
            
            translations.append({
                'l': target_lang,
                'w': target_word,
                'c': round(confidence, 2),
                'f': frequency
            })
    
    word_entries[source_word] = {
        'word': source_word,
        't': translations
    }

with open("ede_word_sense.json", "w", encoding="utf-8") as f:
    json.dump(word_entries, f, ensure_ascii=False, indent=2)

print(f"  ✓ Created {len(word_entries)} high-confidence words\n")

# FINAL SUMMARY
print("=" * 70)
print("BUILD COMPLETE")
print("=" * 70)
print(f"ede_yoruba_rich.json:  {len(yoruba_rich):,} unique English-Yoruba phrases")
print(f"ede_master.json:       {len(ede_master):,} total translation entries")
print(f"ede_word_sense.json:   {len(word_entries):,} high-confidence words (2+ languages or frequency >= 2)")
print("\nProgress to 500k: {:.1f}%".format((len(yoruba_rich) / 500000) * 100))
print("=" * 70)
