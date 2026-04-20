import json
from datasets import load_dataset
from datetime import date

dataset = load_dataset('newadays/menyo_20k_a_multi_domain_english_yoruba_corpus_for_machine_translation')

ede_entries = []

for i, row in enumerate(dataset["train"]):
    entry = {
        "id": f"ede_yor_menyo_{i:05d}",
        "source_language": "English",
        "source_text": row["English"].strip(),
        "target_language": "Yoruba",
        "target_text": row["Yoruba"].strip().lstrip('\ufeff'),
        "language_family": "Niger-Congo",
        "dialect": "standard",
        "data_type": "text",
        "domain": "multi-domain",
        "sources": ["newadays/menyo_20k"],
        "verified_by": 0,
        "verification_score": 0.0,
        "quality_checked": False,
        "quality_notes": "Multi-domain English-Yoruba parallel corpus - clean translation pairs",
        "license": "unknown",
        "last_updated": str(date.today())
    }
    ede_entries.append(entry)

with open("ede_yoruba_menyo.json", "w", encoding="utf-8") as f:
    json.dump(ede_entries, f, ensure_ascii=False, indent=2)

print(f"Exported {len(ede_entries)} entries to ede_yoruba_menyo.json")
