"""Vigenere cipher: a Caesar shift that cycles through a keyword."""

import random

from .alphabet import LETTERS, N_LETTERS


def random_key(length=None, rng=None):
    rng = rng or random
    length = length or rng.randint(3, 8)
    return "".join(rng.choice(LETTERS) for _ in range(length))


def _shifts(key):
    key = "".join(c for c in key.upper() if "A" <= c <= "Z")
    if not key:
        raise ValueError("vigenere key must contain at least one letter")
    return [ord(c) - 65 for c in key]


def _run(text, key, sign):
    shifts = _shifts(key)
    out, j = [], 0
    for ch in text.upper():
        if "A" <= ch <= "Z":
            out.append(LETTERS[(ord(ch) - 65 + sign * shifts[j % len(shifts)]) % N_LETTERS])
            j += 1                      # non-letters do not consume the keyword
        else:
            out.append(ch)
    return "".join(out)


def encrypt(text, key):
    return _run(text, key, +1)


def decrypt(text, key):
    return _run(text, key, -1)
