import json
from datasets import load_dataset
from datetime import date

dataset = load_dataset('Tamazight-NLP/NLLB-Seed_Standard-Moroccan-Tamazight')

ede_entries = []

for i, row in enumerate(dataset["train"]):
    entry = {
        "id": f"ede_tzm_001_{i:05d}",
        "source_language": "English",
        "source_text": row["source_sentence"].strip(),
        "target_language": "Tamazight",
        "target_text": row["target_sentence"].strip(),
        "language_family": "Afroasiatic",
        "dialect": "Standard Moroccan",
        "data_type": "text",
        "domain": "general",
        "sources": ["Tamazight-NLP/NLLB-Seed_Standard-Moroccan-Tamazight"],
        "verified_by": 0,
        "verification_score": 0.0,
        "quality_checked": False,
        "quality_notes": "Tifinagh script - North African Berber language",
        "license": "unknown",
        "last_updated": str(date.today())
    }
    ede_entries.append(entry)

with open("data/tamazight/ede_tamazight.json", "w", encoding="utf-8") as f:
    json.dump(ede_entries, f, ensure_ascii=False, indent=2)

print(f"Exported {len(ede_entries)} entries to data/tamazight/ede_tamazight.json")
