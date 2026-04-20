import json
from datasets import load_dataset
from datetime import date

dataset = load_dataset('emuchogu/swahili-english-translation')

ede_entries = []

for i, row in enumerate(dataset["train"]):
    entry = {
        "id": f"ede_swa_001_{i:07d}",
        "source_language": "English",
        "source_text": row["input"].strip(),
        "target_language": "Swahili",
        "target_text": row["output"].strip(),
        "language_family": "Niger-Congo",
        "dialect": "standard",
        "data_type": "text",
        "domain": "conversational",
        "sources": ["emuchogu/swahili-english-translation"],
        "verified_by": 0,
        "verification_score": 0.0,
        "quality_checked": False,
        "quality_notes": "English-Swahili translation pairs",
        "license": "unknown",
        "last_updated": str(date.today())
    }
    ede_entries.append(entry)

with open("ede_swahili.json", "w", encoding="utf-8") as f:
    json.dump(ede_entries, f, ensure_ascii=False, indent=2)

print(f"Exported {len(ede_entries)} entries to ede_swahili.json")
