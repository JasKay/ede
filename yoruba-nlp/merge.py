import json
from datetime import date

def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def merge_datasets(*filenames):
    all_entries = []
    seen = set()
    duplicates = 0

    for filename in filenames:
        entries = load_json(filename)
        for entry in entries:
            key = (
                entry["source_text"].lower().strip(),
                entry["target_text"].lower().strip(),
                entry["target_language"]
            )
            if key not in seen:
                seen.add(key)
                all_entries.append(entry)
            else:
                duplicates += 1

    return all_entries, duplicates

merged, duplicates = merge_datasets(
    "data/yoruba/ede_yoruba_0xnu.json",
    "data/yoruba/ede_yoruba_helsinki.json",
    "data/yoruba/ede_yoruba_menyo.json",
    "data/swahili/ede_swahili.json",
    "data/tamazight/ede_tamazight.json"
)

with open("ede_master.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f"Total entries: {len(merged)}")
print(f"Duplicates removed: {duplicates}")
print(f"Saved to ede_master.json")
