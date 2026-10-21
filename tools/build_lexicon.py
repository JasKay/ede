"""Build an attributed lexical snapshot from a checksum-pinned Wiktionary extract."""
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from corpus import entry_kind, normalize

EXPECTED = "b1e51d277b749b763ad517f26afbd2f648ed67bf26414edd7b5197b56950d1ea"
SOURCE = "https://kaikki.org/dictionary/Yoruba/kaikki.org-dictionary-Yoruba.jsonl"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"
PARTS = {"noun", "verb", "adj", "adv", "pron", "det", "prep", "conj", "intj", "num", "particle"}


def build(source, destination):
    content = Path(source).read_bytes()
    if hashlib.sha256(content).hexdigest() != EXPECTED:
        raise ValueError("Source checksum differs from the audited snapshot")
    output = {}
    for line in content.splitlines():
        row = json.loads(line)
        if row.get("lang_code") != "yo" or row.get("pos") not in PARTS:
            continue
        canonical = list(dict.fromkeys(f["form"] for f in row.get("forms", [])
                                      if f.get("tags") == ["canonical"]))
        if len(canonical) > 1:
            continue  # No guess about which tone-marked headword belongs to this record.
        head = canonical[0] if canonical else row["word"]
        if entry_kind(head, head) != "word":
            continue
        page = "https://en.wiktionary.org/wiki/" + quote(row["word"], safe="") + "#Yoruba"
        history = "https://en.wiktionary.org/w/index.php?title=" + quote(row["word"], safe="") + "&action=history"
        for sense in row.get("senses", []):
            if sense.get("form_of") or sense.get("alt_of") or "no-gloss" in sense.get("tags", []):
                continue
            glosses = [g.strip() for g in sense.get("glosses", []) if isinstance(g, str) and g.strip()]
            if not glosses:
                continue
            gloss = glosses[-1]
            if len(gloss) > 700:
                continue
            examples = []
            for ex in sense.get("examples", []):
                # Quotations (including song lyrics), unattributed types and third-party refs are excluded.
                if ex.get("type") != "example" or ex.get("ref") or ex.get("author") or ex.get("source"):
                    continue
                if ex.get("text") and ex.get("english"):
                    examples.append({"yoruba": ex["text"], "english": ex["english"],
                                     "source": page, "license": "CC-BY-SA-4.0"})
            ident = sense.get("id") or hashlib.sha256(json.dumps([row["word"], head, row["pos"], glosses],
                                                                ensure_ascii=False).encode()).hexdigest()
            # Include the canonical form to preserve tone-distinguished entries sharing an unmarked page.
            ident = hashlib.sha256(json.dumps([ident, head, row["pos"]], ensure_ascii=False).encode()).hexdigest()
            output[ident] = {
                "id": ident, "english": gloss, "yoruba": head, "pos": row["pos"],
                "glosses": glosses, "labels": list(dict.fromkeys(sense.get("tags", []) + sense.get("raw_tags", []))),
                "usage_notes": sense.get("raw_glosses", []), "dialect": "unspecified",
                "examples": examples[:5], "source": page, "history": history,
                "synonyms": [{"word": item["word"], "tags": item.get("tags", []), "raw_tags": item.get("raw_tags", [])}
                             for item in sense.get("synonyms", []) if isinstance(item.get("word"), str)],
                "source_title": row["word"], "license": "CC-BY-SA-4.0", "license_url": LICENSE,
                "attribution": "English Wiktionary contributors; extracted by Wiktextract / kaikki.org",
                "extract_url": SOURCE, "extract_sha256": EXPECTED,
                "dump_date": "2026-09-02", "extraction_date": "2026-10-03",
                "changes": "Selected Yoruba lexical senses and canonical forms; omitted quotations, nonlexical records and ambiguous canonical forms. Reformatted for Ede."
            }
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(output[key], ensure_ascii=False, sort_keys=True) + "\n"
                                   for key in sorted(output)), encoding="utf-8", newline="\n")
    print("Senses:", len(output), "Distinct headwords:", len({normalize(r["yoruba"]) for r in output.values()}),
          "Usage examples:", sum(len(r["examples"]) for r in output.values()))


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data" / "kaikki-yoruba.jsonl",
          ROOT / "data" / "yoruba-lexicon.jsonl")
