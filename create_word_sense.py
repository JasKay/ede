import json
from collections import defaultdict

print('Loading ede_master.json...')
with open('ede_master.json', 'r', encoding='utf-8') as f:
    entries = json.load(f)

print(f'Processing {len(entries)} entries...')

translation_map = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for entry in entries:
    source = entry['source_text'].lower().strip()
    target = entry['target_text'].lower().strip()
    target_lang = entry['target_language']
    
    translation_map[source][target_lang][target].append(entry)

word_entries = {}

for source_word, langs in translation_map.items():
    has_multiple_langs = len(langs) >= 2
    has_good_frequency = any(
        max(len(entries_list) for entries_list in targets.values()) >= 2
        for targets in langs.values()
    )
    
    if not (has_multiple_langs or has_good_frequency):
        continue
    
    translations = []
    for target_lang, targets in langs.items():
        for target_word, entries_list in targets.items():
            frequency = len(entries_list)
            confidence = min(0.99, frequency / 10.0)
            
            translations.append({
                'l': target_lang,
                'w': target_word,
                'c': round(confidence, 2),
                'f': frequency
            })
    
    word_entries[source_word] = {
        'word': source_word,
        't': translations
    }

with open('ede_word_sense.json', 'w', encoding='utf-8') as f:
    json.dump(word_entries, f, ensure_ascii=False, indent=2)

print(f'Created {len(word_entries)} high-confidence words')
print('✓ Saved to ede_word_sense.json')
