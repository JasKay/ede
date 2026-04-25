from datasets import load_dataset
import json

print("Loading additional English-Yoruba datasets...\n")

# Load existing
with open("ede_yoruba_rich.json", "r", encoding="utf-8") as f:
    yoruba_rich = json.load(f)

print(f"Starting with {len(yoruba_rich)} words\n")

datasets = [
    ("ccibeekeoc42/DollyHHRLHF_yoruba", "dolly"),
    ("saillab/alpaca-yoruba-cleaned", "alpaca"),
]

total_new = 0

for dataset_id, name in datasets:
    try:
        print(f"Loading {name}...")
        ds = load_dataset(dataset_id, split='train')
        print(f"  Found {len(ds)} entries")
        
        for i, example in enumerate(ds):
            # Handle different field names
            eng = example.get('instruction', example.get('text', example.get('english', '')))
            yor = example.get('output', example.get('yoruba', ''))
            
            if isinstance(eng, dict):
                eng = eng.get('en', '')
            if isinstance(yor, dict):
                yor = yor.get('yo', '')
            
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
                    "sources": [name]
                })
                
                if name not in yoruba_rich[eng]['definitions'][0]['sources']:
                    yoruba_rich[eng]['definitions'][0]['sources'].append(name)
                
                total_new += 1
        
        print(f"  ✓ Merged {name}\n")
        
    except Exception as e:
        print(f"  ✗ Error loading {name}: {e}\n")

# Save
with open("ede_yoruba_rich.json", "w", encoding="utf-8") as f:
    json.dump(yoruba_rich, f, ensure_ascii=False, indent=2)

print("=" * 60)
print(f"Total new entries: {total_new}")
print(f"Total unique words now: {len(yoruba_rich)}")
print(f"✓ Saved to ede_yoruba_rich.json")
