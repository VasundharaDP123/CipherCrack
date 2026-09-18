"""Monoalphabetic substitution cipher.

Key convention used everywhere in CipherCrack
---------------------------------------------
An *encryption key* is a 26-character string where position ``i`` holds the
ciphertext letter that plaintext letter ``i`` becomes::

    key = "QWERTYUIOPASDFGHJKLZXCVBNM"
    A -> Q,  B -> W,  C -> E, ...

A *decryption key* is the inverse permutation: position ``j`` holds the
plaintext letter that ciphertext letter ``j`` came from.  The solvers search
over decryption keys, because that is what turns the ciphertext they are
holding into readable English.
"""

import random

import numpy as np

from .alphabet import LETTERS, N_LETTERS

IDENTITY = LETTERS


def random_key(rng=None):
    rng = rng or random
    letters = list(LETTERS)
    rng.shuffle(letters)
    return "".join(letters)


def is_valid_key(key):
    return isinstance(key, str) and len(key) == N_LETTERS and set(key) == set(LETTERS)


def invert_key(key):
    """Turn an encryption key into a decryption key (and vice versa)."""
    out = [""] * N_LETTERS
    for i, ch in enumerate(key):
        out[ord(ch) - 65] = LETTERS[i]
    return "".join(out)


def _apply(text, key):
    table = str.maketrans(LETTERS, key)
    return text.upper().translate(table)


def encrypt(text, key):
    if not is_valid_key(key):
        raise ValueError("substitution key must be a permutation of A-Z")
    return _apply(text, key)


def decrypt(text, key):
    """``key`` is the *encryption* key; we invert it before applying."""
    if not is_valid_key(key):
        raise ValueError("substitution key must be a permutation of A-Z")
    return _apply(text, invert_key(key))


def decrypt_with_decryption_key(text, dec_key):
    """Apply a decryption key (cipher letter -> plain letter) directly."""
    return _apply(text, dec_key)


def key_to_array(key):
    """26-length int array, ``arr[i]`` = image of letter ``i`` under the key."""
    return np.array([ord(c) - 65 for c in key], dtype=np.int64)


def array_to_key(arr):
    return "".join(LETTERS[int(i)] for i in arr)


def key_accuracy(guess, truth):
    """Fraction of the 26 letters the guessed key gets right."""
    return sum(1 for a, b in zip(guess, truth) if a == b) / N_LETTERS
