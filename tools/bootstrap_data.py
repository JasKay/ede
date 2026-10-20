"""Recover Ede's existing compact artifact. Does not assert its upstream licence."""
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://huggingface.co/spaces/jaskay/ede-african-nlp/resolve/"
       "1ad68da6eb4e48427c5b3f2358f2e3064f7179e8/ede_word_sense.json")
EXPECTED = "b520e2793cc4b72ccb3cafa00ce04e3685555986ab387ff7de43ebc77f100aa3"


def bootstrap(directory):
    target = Path(directory) / "ede_word_sense.json"
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == EXPECTED:
        print("Pinned corpus artifact is already present.")
        return target
    with urllib.request.urlopen(URL, timeout=60) as response:
        content = response.read(2_000_001)
    if len(content) > 2_000_000 or hashlib.sha256(content).hexdigest() != EXPECTED:
        raise ValueError("Corpus artifact checksum mismatch; nothing was installed.")
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_suffix(".download")
    staged.write_bytes(content)
    staged.replace(target)
    print("Recovered existing corpus artifact. Upstream attribution and licences still require audit.")
    return target


if __name__ == "__main__":
    bootstrap(sys.argv[1] if len(sys.argv) > 1 else ROOT / "data")
