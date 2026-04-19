import json
from datasets import load_dataset
from datetime import date

dataset = load_dataset('Helsinki-NLP/opus-100', 'en-yo')

ede_entries = []

for i, row in enumerate(dataset["train"]):
    entry = {
        "id": f"ede_yor_hel_{i:05d}",
        "source_language": "English",
        "source_text": row["translation"]["en"].strip(),
        "target_language": "Yoruba",
        "target_text": row["translation"]["yo"].strip(),
        "language_family": "Niger-Congo",
        "dialect": "standard",
        "data_type": "text",
        "domain": "software-ui",
        "sources": ["Helsinki-NLP/opus-100"],
        "verified_by": 0,
        "verification_score": 0.0,
        "quality_checked": False,
        "quality_notes": "Technical UI strings from Mozilla localization - not conversational language",
        "license": "unknown",
        "last_updated": str(date.today())
    }
    ede_entries.append(entry)

with open("ede_yoruba_helsinki.json", "w", encoding="utf-8") as f:
    json.dump(ede_entries, f, ensure_ascii=False, indent=2)

print(f"Exported {len(ede_entries)} entries to ede_yoruba_helsinki.json")
