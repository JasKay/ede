import json

with open("ede_master.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Check language distribution
from collections import Counter
domains = Counter(entry["domain"] for entry in data)
sources = Counter(str(entry["sources"]) for entry in data)

print("Domain breakdown:")
for domain, count in domains.items():
    print(f"  {domain}: {count}")

print("\nSource breakdown:")
for source, count in sources.items():
    print(f"  {source}: {count}")
