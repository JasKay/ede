import json

def analyze_language(language):
    input_file = f"ede_{language.lower()}_rich.json"
    
    print(f"\nAnalyzing {language}...\n")
    
    with open(input_file, "r") as f:
        data = json.load(f)
    
    words = {}
    phrases = {}
    sentences = {}
    
    for eng, entry in data.items():
        word_count = len(eng.split())
        
        if word_count <= 2:
            words[eng] = entry
        elif word_count <= 10:
            phrases[eng] = entry
        else:
            sentences[eng] = entry
    
    print(f"Single words/short (1-2): {len(words):,}")
    print(f"Phrases (3-10 words): {len(phrases):,}")
    print(f"Sentences (11+ words): {len(sentences):,}")
    
    print("\nExample single words:")
    for w in list(words.keys())[:5]:
        print(f"  - {w}")
    
    print("\nExample phrases:")
    for p in list(phrases.keys())[:5]:
        print(f"  - {p}")

if __name__ == "__main__":
    for lang in ["yoruba", "swahili", "xhosa", "tamazight"]:
        analyze_language(lang)
