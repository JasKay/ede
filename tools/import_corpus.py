"""Import a local corpus without starting the server. No downloads or generated translations."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corpus import Corpus

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("--database", type=Path, default=Path("data/ede.db"))
args = parser.parse_args()
count = Corpus(args.database).import_file(args.source)
print(f"Imported {count} new Yoruba pairs. All imported entries are unverified.")
