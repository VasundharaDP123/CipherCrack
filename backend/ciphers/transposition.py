"""Columnar transposition: letters are reordered, never replaced.

Unlike the other three, this cipher does not touch letter identity at all --
which is exactly what makes it easy for the identifier to spot (its letter
frequencies stay perfectly English).

The plaintext is written row-wise into a grid ``len(key)`` columns wide, padded
with ``X`` to fill the last row, then read out column by column in the
alphabetical order of the keyword's letters.  Spaces and punctuation are
dropped first, because a transposition of a space carries no information and
real transposition ciphers are always sent as letter blocks.
"""

import random

from .alphabet import LETTERS, letters_only

PAD = "X"


def random_key(length=None, rng=None):
    rng = rng or random
    length = length or rng.randint(4, 8)
    # Distinct letters keep the column order unambiguous.
    return "".join(rng.sample(LETTERS, length))


def _column_order(key):
    """Indices of the key's columns sorted by their letter, ties left-to-right."""
    key = "".join(c for c in key.upper() if "A" <= c <= "Z")
    if len(key) < 2:
        raise ValueError("transposition key needs at least two letters")
    return sorted(range(len(key)), key=lambda i: (key[i], i)), len(key)


def encrypt(text, key):
    order, width = _column_order(key)
    body = letters_only(text)
    if not body:
        return ""
    if len(body) % width:
        body += PAD * (width - len(body) % width)
    rows = [body[i:i + width] for i in range(0, len(body), width)]
    return "".join("".join(row[c] for row in rows) for c in order)


def decrypt(text, key):
    order, width = _column_order(key)
    body = letters_only(text)
    if not body:
        return ""
    height = len(body) // width
    if height == 0:
        return body
    body = body[:height * width]            # ignore a ragged tail
    columns = {}
    for n, c in enumerate(order):
        columns[c] = body[n * height:(n + 1) * height]
    return "".join(columns[c][r] for r in range(height) for c in range(width))
