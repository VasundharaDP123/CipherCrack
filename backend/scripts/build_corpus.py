"""Download the public-domain corpus and split it into train / test books.

Training books feed the bigram language model and the HMM transition matrix.
Test books are never seen by either, so the solver evaluation in
``notebooks/`` is honest.

    python -m scripts.build_corpus
"""

import argparse
import pathlib
import re
import socket
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"

# Books the language model learns from.
TRAIN_BOOKS = {
    "pride_and_prejudice": 1342,
    "war_and_peace": 2600,
    "sherlock_holmes": 1661,
    "frankenstein": 84,
    "tale_of_two_cities": 98,
    "jane_eyre": 1260,
}

# Different authors and periods, held out for evaluation passages.
TEST_BOOKS = {
    "alice_in_wonderland": 11,
    "great_expectations": 1400,
    "dracula": 345,
    "moby_dick": 2701,
}

MIRRORS = [
    "https://www.gutenberg.org/files/{id}/{id}-0.txt",
    "https://www.gutenberg.org/files/{id}/{id}.txt",
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
]

START_RE = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)
END_RE = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", re.I)


def strip_boilerplate(text):
    """Cut the Gutenberg licence header and footer off a book."""
    start = START_RE.search(text)
    if start:
        text = text[start.end():]
    end = END_RE.search(text)
    if end:
        text = text[:end.start()]
    return text.strip()


def download(book_id):
    last = None
    for template in MIRRORS:
        url = template.format(id=book_id)
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read().decode("utf-8", errors="ignore")
            if len(raw) > 10_000:
                return raw
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            last = exc
    raise RuntimeError(f"could not download book {book_id}: {last}")


def fetch_set(books, subdir, force=False):
    target = CORPUS / subdir
    target.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, book_id in books.items():
        path = target / f"{name}.txt"
        if path.exists() and not force:
            size = path.stat().st_size
            print(f"  [skip] {name:22s} {size / 1e6:5.2f} MB (already present)")
            total += size
            continue
        print(f"  [get ] {name:22s} id={book_id} ...", end="", flush=True)
        body = strip_boilerplate(download(book_id))
        path.write_text(body, encoding="utf-8")
        print(f" {len(body) / 1e6:5.2f} MB")
        total += len(body)
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download existing books")
    args = parser.parse_args()

    print("Training books (language model + HMM transitions):")
    train_bytes = fetch_set(TRAIN_BOOKS, "train", args.force)
    print("\nTest books (held out for evaluation passages):")
    test_bytes = fetch_set(TEST_BOOKS, "test", args.force)

    print(f"\ntrain {train_bytes / 1e6:.2f} MB   test {test_bytes / 1e6:.2f} MB")
    if train_bytes < 3e6:
        print("warning: training corpus is under the 3 MB target", file=sys.stderr)


if __name__ == "__main__":
    main()
