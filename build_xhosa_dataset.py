from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE XHOSA DATASET")
print("=" * 70 + "\n")

xhosa_rich = {}
total_merged = 0

# DATASET 1: English-Xhosa MT560
print("DATASET 1: Loading michsethowusu/english-xhosa_sentence-pairs_mt560...\n")

try:
    ds = load_dataset('michsethowusu/english-xhosa_sentence-pairs_mt560', split='train')
    print(f"  Found {len(ds)} entries")
    
    for i, example in enumerate(ds):
        if i % 100000 == 0 and i > 0:
            print(f"    Processed {i}...")
        
        eng = example.get('eng', '').lower().strip()
        xh = example.get('xho', '').strip()
        
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
                "sources": ["michsethowusu/english-xhosa_sentence-pairs_mt560"]
            })
            total_merged += 1
    
    print(f"  ✓ Merged {total_merged} entries\n")

except Exception as e:
    print(f"  ✗ Error: {e}\n")

# Save rich Xhosa dataset
with open("ede_xhosa_rich.json", "w", encoding="utf-8") as f:
    json.dump(xhosa_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print("BUILD COMPLETE - XHOSA")
print("=" * 70)
print(f"ede_xhosa_rich.json: {len(xhosa_rich):,} unique English-Xhosa phrases")
print(f"Total entries merged: {total_merged:,}")
print("=" * 70)
