from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE XHOSA DATASET - EXTENDED")
print("=" * 70 + "\n")

xhosa_rich = {}
total_merged = 0

datasets = [
    ("michsethowusu/english-xhosa_sentence-pairs_mt560", "eng", "xho", "mt560"),
    ("Helsinki-NLP/opus_xhosanavy", "src", "tgt", "opus_xhosanavy"),
    ("saillab/alpaca-xhosa-cleaned", "instruction", "output", "alpaca-xhosa"),
]

for dataset_id, eng_field, xh_field, name in datasets:
    try:
        print(f"Loading {name}...")
        ds = load_dataset(dataset_id, split='train', streaming=False)
        print(f"  Found {len(ds)} entries")
        
        added = 0
        for i, example in enumerate(ds):
            if i % 100000 == 0 and i > 0:
                print(f"    Processed {i}...")
            
            eng = str(example.get(eng_field, '')).lower().strip()
            xh = str(example.get(xh_field, '')).strip()
            
            if not eng or not xh or len(eng) < 2:
                continue
            
            if eng not in xhosa_rich:
                xhosa_rich[eng] = {
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
                t['word'] == xh and t['language'] == 'Xhosa'
                for d in xhosa_rich[eng]['definitions']
                for t in d['translations']
            )
            
            if not exists:
                xhosa_rich[eng]['definitions'][0]['translations'].append({
                    "language": "Xhosa",
                    "word": xh,
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

with open("ede_xhosa_rich.json", "w", encoding="utf-8") as f:
    json.dump(xhosa_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print(f"Total unique words: {len(xhosa_rich):,}")
print(f"New entries merged: {total_merged:,}")
print("✓ Saved to ede_xhosa_rich.json")
print("=" * 70)
