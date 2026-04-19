import json
from datasets import load_dataset
from datetime import date

dataset = load_dataset("0xnu/yoruba")

ede_entries = []

for i, row in enumerate(dataset["train"]):
    entry = {
        "id": f"ede_yor_{i:05d}",
        "source_language": "Yoruba",
        "source_text": row["input"].strip().lower(),
        "target_language": "Yoruba",
        "target_text": row["output"].strip(),
        "language_family": "Niger-Congo",
        "dialect": "standard",
        "data_type": "text",
        "sources": ["0xnu/yoruba"],
        "domain": "software-ui",
        "quality_notes": "Technical UI strings from Mozilla localization - not conversational language",
        "verified_by": 0,
        "verification_score": 0.0,
        "quality_checked": False,
        "quality_notes": "source text appears to be Yoruba not English - needs native speaker review",
        "license": "unknown",
        "last_updated": str(date.today())
    }
    ede_entries.append(entry)

with open("ede_yoruba_v1.json", "w", encoding="utf-8") as f:
    json.dump(ede_entries, f, ensure_ascii=False, indent=2)

print(f"Exported {len(ede_entries)} entries to ede_yoruba_v1.json")
