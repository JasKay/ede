from datasets import load_dataset
import json

print("Loading additional English-Yoruba datasets...\n")

# Load existing
with open("ede_yoruba_rich.json", "r", encoding="utf-8") as f:
    yoruba_rich = json.load(f)

print(f"Starting with {len(yoruba_rich)} words\n")

print("Loading dolly...")
try:
    ds = load_dataset('ccibeekeoc42/DollyHHRLHF_yoruba', split='train')
    print(f"  Found {len(ds)} entries")
    
    total_new = 0
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
            total_new += 1
    
    print(f"  ✓ Merged {total_new} new entries\n")
    
except Exception as e:
    print(f"  ✗ Error: {e}\n")

# Save
with open("ede_yoruba_rich.json", "w", encoding="utf-8") as f:
    json.dump(yoruba_rich, f, ensure_ascii=False, indent=2)

print("=" * 60)
print(f"Total unique words now: {len(yoruba_rich)}")
print(f"✓ Saved to ede_yoruba_rich.json")
