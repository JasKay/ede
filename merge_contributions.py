import json
from datetime import date

print("Loading data...")

# Load word sense
with open("ede_word_sense.json", "r", encoding="utf-8") as f:
    word_sense = json.load(f)

# Load contributions
try:
    with open("contributions.json", "r", encoding="utf-8") as f:
        contributions = json.load(f)
except FileNotFoundError:
    print("No contributions.json found")
    contributions = []

print(f"Processing {len(contributions)} contributions...")

# Merge contributions into word sense
added = 0
for contrib in contributions:
    word = contrib["word"]
    lang = contrib["language"]
    trans = contrib["translation"]
    
    if word not in word_sense:
        word_sense[word] = {"word": word, "t": []}
    
    # Check if this translation already exists
    exists = any(t["l"] == lang and t["w"] == trans for t in word_sense[word]["t"])
    
    if not exists:
        word_sense[word]["t"].append({
            "l": lang,
            "w": trans,
            "c": 0.65,  # Lower confidence for user submissions
            "f": 1
        })
        print(f"✓ {word} -> {trans} ({lang})")
        added += 1

# Save updated word sense
with open("ede_word_sense.json", "w", encoding="utf-8") as f:
    json.dump(word_sense, f, ensure_ascii=False, indent=2)

print(f"\nDone! Added {added} new translations.")
print("Next: Upload ede_word_sense.json to HF Spaces and rebuild.")
