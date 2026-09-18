"""Caesar cipher: every letter is shifted by the same amount."""

import random

from .alphabet import LETTERS, N_LETTERS


def random_key(rng=None):
    rng = rng or random
    return rng.randint(1, N_LETTERS - 1)


def encrypt(text, shift):
    shift = int(shift) % N_LETTERS
    out = []
    for ch in text.upper():
        if "A" <= ch <= "Z":
            out.append(LETTERS[(ord(ch) - 65 + shift) % N_LETTERS])
        else:
            out.append(ch)
    return "".join(out)


def decrypt(text, shift):
    return encrypt(text, -int(shift))


def brute_force(ciphertext):
    """All 26 shifts.  Caesar is the one cipher here that *is* brute-forceable."""
    return [(s, decrypt(ciphertext, s)) for s in range(N_LETTERS)]
