"""The four classical ciphers, behind one dispatch table.

Every cipher module exposes the same three functions -- ``encrypt(text, key)``,
``decrypt(text, key)`` and ``random_key()`` -- so the API layer and the dataset
generator can treat them interchangeably.
"""

from . import alphabet, caesar, substitution, transposition, vigenere

CIPHERS = {
    "caesar": caesar,
    "substitution": substitution,
    "vigenere": vigenere,
    "transposition": transposition,
}

CIPHER_NAMES = list(CIPHERS)

# Human-facing labels and key hints, reused by the Encrypt Lab page.
CIPHER_INFO = {
    "caesar": {
        "label": "Caesar",
        "key_hint": "A shift from 1 to 25",
        "key_type": "int",
    },
    "substitution": {
        "label": "Substitution",
        "key_hint": "A permutation of all 26 letters",
        "key_type": "permutation",
    },
    "vigenere": {
        "label": "Vigenere",
        "key_hint": "A keyword, e.g. LEMON",
        "key_type": "word",
    },
    "transposition": {
        "label": "Transposition",
        "key_hint": "A keyword of distinct letters, e.g. ZEBRA",
        "key_type": "word",
    },
}


def get(name):
    try:
        return CIPHERS[name.lower()]
    except (KeyError, AttributeError):
        raise ValueError(f"unknown cipher {name!r}; expected one of {CIPHER_NAMES}")


def encrypt(name, text, key=None, rng=None):
    """Encrypt with the named cipher, inventing a key if none was given.

    Returns ``(ciphertext, key)`` so callers always learn the key that was used.
    """
    module = get(name)
    if key in (None, ""):
        key = module.random_key(rng=rng)
    return module.encrypt(text, key), key


def decrypt(name, text, key):
    return get(name).decrypt(text, key)


def random_key(name, rng=None):
    return get(name).random_key(rng=rng)


__all__ = [
    "CIPHERS", "CIPHER_NAMES", "CIPHER_INFO",
    "alphabet", "caesar", "substitution", "transposition", "vigenere",
    "get", "encrypt", "decrypt", "random_key",
]
