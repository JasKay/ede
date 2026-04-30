import json
import sys

def enhance_language(language):
    input_file = f"ede_{language.lower()}_rich.json"
    output_file = f"ede_{language.lower()}_rich_enhanced.json"
    
    print(f"Enhancing {language}...\n")
    
    with open(input_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    
    # POS tagging
    pos_map = {
        "run": "VB", "walks": "VBZ", "walked": "VBD", "walking": "VBG",
        "person": "NN", "people": "NNS", "cat": "NN", "cats": "NNS",
        "big": "JJ", "small": "JJ", "happy": "JJ", "sad": "JJ",
        "the": "DT", "a": "DT", "an": "DT",
    }
    
    # Conjugations
    conjugations = {
        "run": {"base": "run", "singular": "run", "plural": "run", "past": "ran", "ing": "running"},
        "walk": {"base": "walk", "singular": "walks", "plural": "walk", "past": "walked", "ing": "walking"},
        "go": {"base": "go", "singular": "goes", "plural": "go", "past": "went", "ing": "going"},
        "take": {"base": "take", "singular": "takes", "plural": "take", "past": "took", "ing": "taking"},
    }
    
    enhanced = {}
    count = 0
    
    for eng, data in old_data.items():
        pos = pos_map.get(eng.lower(), "NN")
        
        verb_base = None
        for base, conj_forms in conjugations.items():
            if eng.lower() in [base] + list(conj_forms.values()):
                verb_base = base
                break
        
        conj_data = conjugations.get(verb_base) if verb_base else {}
        
        enhanced[eng] = {
            "word": eng,
            "language": "English",
            "definitions": [{
                "id": data['definitions'][0]['id'],
                "definition": data['definitions'][0]['definition'],
                "part_of_speech": "noun" if "NN" in pos else "verb" if "VB" in pos else "adjective",
                "pos_tag": pos,
                "conjugations": conj_data,
                "translations": []
            }]
        }
        
        for trans in data['definitions'][0]['translations']:
            enhanced_trans = {
                "language": trans['language'],
                "word": trans['word'],
                "word_alignment": [trans['word']],
                "pos": "noun" if "NN" in pos else "verb" if "VB" in pos else "adjective",
                "pos_tag": pos,
                "confidence": trans.get('confidence', 0.85),
                "conjugations": {},
                "examples": [{"english": eng, "yoruba": trans['word']}],
                "sources": trans.get('sources', [])
            }
            enhanced[eng]['definitions'][0]['translations'].append(enhanced_trans)
        
        count += 1
        if count % 100 == 0:
            print(f"  Processed {count}...")
    
    print(f"\nEnhanced {count} entries")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, ensure_ascii=False, indent=1)
    
    print(f"✓ Saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 enhance_dataset.py <language>")
        print("Languages: yoruba, swahili, xhosa, tamazight")
        sys.exit(1)
    
    language = sys.argv[1].lower()
    if language not in ["yoruba", "swahili", "xhosa", "tamazight"]:
        print("Invalid language. Choose: yoruba, swahili, xhosa, tamazight")
        sys.exit(1)
    
    enhance_language(language)
