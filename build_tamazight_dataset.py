from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE TAMAZIGHT DATASET - EXTENDED")
print("=" * 70 + "\n")

tamazight_rich = {}
total_merged = 0

datasets = [
    ("Tamazight-NLP/NLLB-Seed_Standard-Moroccan-Tamazight", "source_sentence", "target_sentence", "nllb-seed"),
    ("Tamazight/Countries_en_zgh", "English", "Tamazight", "countries-en-zgh"),
    ("Abdeljalil-Ounaceur/English-Tamazight-Dictionnary-2007", "English", "Tamazight", "dictionary-2007"),
    ("tamazightdev/tamazight-ar-en-fr", "English", "Tamazight", "tamazightdev"),
]


for dataset_id, eng_field, tz_field, name in datasets:
    try:
        print(f"Loading {name}...")
        ds = load_dataset(dataset_id, split='train', streaming=False)
        print(f"  Found {len(ds)} entries")
        
        added = 0
        for i, example in enumerate(ds):
            if i % 5000 == 0 and i > 0:
                print(f"    Processed {i}...")
            
            eng = str(example.get(eng_field, '')).lower().strip()
            tz = str(example.get(tz_field, '')).strip()
            
            if not eng or not tz or len(eng) < 2:
                continue
            
            if eng not in tamazight_rich:
                tamazight_rich[eng] = {
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
                t['word'] == tz and t['language'] == 'Tamazight'
                for d in tamazight_rich[eng]['definitions']
                for t in d['translations']
            )
            
            if not exists:
                tamazight_rich[eng]['definitions'][0]['translations'].append({
                    "language": "Tamazight",
                    "word": tz,
                    "confidence": 0.85,
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
                total_merged += 1
        
        print(f"  ✓ Merged {added} new entries from {name}\n")
        
    except Exception as e:
        print(f"  ✗ Error loading {name}: {str(e)[:100]}\n")

with open("ede_tamazight_rich.json", "w", encoding="utf-8") as f:
    json.dump(tamazight_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print(f"Total unique words: {len(tamazight_rich):,}")
print(f"New entries merged: {total_merged:,}")
print("✓ Saved to ede_tamazight_rich.json")
print("=" * 70)
