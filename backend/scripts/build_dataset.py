"""Generate the cipher-type dataset from held-out books.

    python -m scripts.build_dataset --per-class 2000

Passages are drawn from the *test* books, never the ones the language model was
trained on, and each passage is enciphered with a freshly drawn random key.
Lengths are sampled from the same distribution for every class, so the
classifier cannot cheat by learning "long messages are Vigenere".
"""

import argparse
import pathlib
import random

import numpy as np

import ciphers
from ciphers.alphabet import clean
from ml import features

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus"
OUT = ROOT / "data" / "generated"

LENGTH_CHOICES = [80, 120, 200, 300, 500, 800, 1200]


def load_passages(directory, min_length=1400):
    """Chop the books into a pool of clean passages to draw from."""
    pool = []
    for path in sorted(pathlib.Path(directory).glob("*.txt")):
        text = clean(path.read_text(encoding="utf-8", errors="ignore"))
        for start in range(0, len(text) - min_length, min_length):
            pool.append(text[start:start + min_length])
    if not pool:
        raise FileNotFoundError(
            f"no passages in {directory}. Run: python -m scripts.build_corpus"
        )
    return pool


def build(per_class=2000, seed=0, split="test"):
    rng = random.Random(seed)
    pool = load_passages(CORPUS / split)

    texts, labels, lengths = [], [], []
    for label, name in enumerate(ciphers.CIPHER_NAMES):
        for _ in range(per_class):
            passage = rng.choice(pool)
            length = rng.choice(LENGTH_CHOICES)
            start = rng.randint(0, max(len(passage) - length - 1, 0))
            plaintext = passage[start:start + length]
            ciphertext, _ = ciphers.encrypt(name, plaintext, rng=rng)
            texts.append(ciphertext)
            labels.append(label)
            lengths.append(length)
    return texts, np.array(labels), np.array(lengths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-class", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--split", default="test",
                        help="which corpus folder to draw passages from")
    args = parser.parse_args()

    print(f"generating {args.per_class} samples x {len(ciphers.CIPHER_NAMES)} classes "
          f"from the '{args.split}' books ...")
    texts, labels, lengths = build(args.per_class, args.seed, args.split)

    print(f"extracting {len(features.FEATURE_NAMES)} features from {len(texts)} samples ...")
    X = features.extract_many(texts)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "cipher_dataset.npz"
    np.savez_compressed(
        path,
        X=X,
        y=labels,
        lengths=lengths,
        classes=np.array(ciphers.CIPHER_NAMES),
        feature_names=np.array(features.FEATURE_NAMES),
        texts=np.array(texts, dtype=object),
    )
    print(f"saved {path}  X={X.shape}  y={labels.shape}")
    for label, name in enumerate(ciphers.CIPHER_NAMES):
        print(f"  {name:15s} {(labels == label).sum():5d} samples")


if __name__ == "__main__":
    main()
