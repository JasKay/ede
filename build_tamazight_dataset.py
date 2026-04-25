from datasets import load_dataset
import json

print("=" * 70)
print("BUILDING EDE TAMAZIGHT DATASET")
print("=" * 70 + "\n")

tamazight_rich = {}
total_merged = 0

# DATASET 1: Tamazight English pairs
print("DATASET 1: Loading Tamazight-NLP/NLLB-Seed_Standard-Moroccan-Tamazight...\n")

try:
    ds = load_dataset('Tamazight-NLP/NLLB-Seed_Standard-Moroccan-Tamazight', split='train')
    print(f"  Found {len(ds)} entries")
    
    for i, example in enumerate(ds):
        if i % 5000 == 0 and i > 0:
            print(f"    Processed {i}...")
        
        eng = example.get('source_sentence', '').lower().strip()
        tz = example.get('target_sentence', '').strip()
        
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
                "sources": ["Tamazight-NLP/NLLB-Seed"]
            })
            total_merged += 1
    
    print(f"  ✓ Merged {total_merged} entries\n")

except Exception as e:
    print(f"  ✗ Error: {e}\n")

# Save rich Tamazight dataset
with open("ede_tamazight_rich.json", "w", encoding="utf-8") as f:
    json.dump(tamazight_rich, f, ensure_ascii=False, indent=2)

print("=" * 70)
print("BUILD COMPLETE - TAMAZIGHT")
print("=" * 70)
print(f"ede_tamazight_rich.json: {len(tamazight_rich):,} unique English-Tamazight phrases")
print(f"Total entries merged: {total_merged:,}")
print("=" * 70)
