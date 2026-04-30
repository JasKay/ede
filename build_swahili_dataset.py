from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE SWAHILI DATASET - EXTENDED")
print("=" * 70 + "\n")

swahili_rich = {}
total_merged = 0

datasets = [
    ("emuchogu/swahili-english-translation", "prompt", "output", "emuchogu"),
    ("Rogendo/English-Swahili-Sentence-Pairs", "English", "Swahili", "Rogendo"),
    ("iamshnoo/alpaca-cleaned-swahili", "instruction", "output", "alpaca-swahili"),
    ("mwitiderrick/SwahiliPlatypus", "instruction", "output", "SwahiliPlatypus"),
    ("Mollel/alpaca-swahili", "instruction", "output", "alpaca-swahili-mollel"),
]

for dataset_id, eng_field, sw_field, name in datasets:
    try:
        print(f"Loading {name}...")
        ds = load_dataset(dataset_id, split='train', streaming=False)
        print(f"  Found {len(ds)} entries")
        
        added = 0
        for i, example in enumerate(ds):
            if i % 50000 == 0 and i > 0:
                print(f"    Processed {i}...")
            
            eng = str(example.get(eng_field, '')).lower().strip()
            sw = str(example.get(sw_field, '')).strip()
            
            if not eng or not sw or len(eng) < 2:
                continue
            
            if eng not in swahili_rich:
                swahili_rich[eng] = {
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
                t['word'] == sw and t['language'] == 'Swahili'
                for d in swahili_rich[eng]['definitions']
                for t in d['translations']
            )
            
            if not exists:
                swahili_rich[eng]['definitions'][0]['translations'].append({
                    "language": "Swahili",
                    "word": sw,
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

# Save
with open("ede_swahili_rich.json", "w", encoding="utf-8") as f:
    json.dump(swahili_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print(f"Total unique words: {len(swahili_rich):,}")
print(f"New entries merged: {total_merged:,}")
print("✓ Saved to ede_swahili_rich.json")
print("=" * 70)
