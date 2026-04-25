from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE SWAHILI DATASET")
print("=" * 70 + "\n")

swahili_rich = {}
total_merged = 0

# DATASET 1: Swahili-English translation
print("DATASET 1: Loading emuchogu/swahili-english-translation...\n")

try:
    ds = load_dataset('emuchogu/swahili-english-translation', split='train')
    print(f"  Found {len(ds)} entries")
    
    for i, example in enumerate(ds):
        if i % 100000 == 0 and i > 0:
            print(f"    Processed {i}...")
        
        prompt = example.get('prompt', '').lower().strip()
        input_text = example.get('input', '').lower().strip()
        output = example.get('output', '').strip()
        
        eng = (prompt + ' ' + input_text).strip()
        sw = output
        
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
                "sources": ["emuchogu/swahili-english-translation"]
            })
            total_merged += 1
    
    print(f"  ✓ Merged {total_merged} entries\n")

except Exception as e:
    print(f"  ✗ Error: {e}\n")

# DATASET 2: Add more Swahili datasets here as you find them
# print("DATASET 2: Loading [dataset_id]...\n")
# (same pattern as above)

# Save rich Swahili dataset
with open("ede_swahili_rich.json", "w", encoding="utf-8") as f:
    json.dump(swahili_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print("BUILD COMPLETE - SWAHILI")
print("=" * 70)
print(f"ede_swahili_rich.json: {len(swahili_rich):,} unique English-Swahili phrases")
print(f"Total entries merged: {total_merged:,}")
print("=" * 70)
