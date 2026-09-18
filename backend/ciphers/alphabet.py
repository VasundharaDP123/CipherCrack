"""Shared alphabet helpers.

Every module in CipherCrack works over the same 27-symbol alphabet:
A-Z as indices 0..25 and space as index 26.  Keeping this in one place means
the ciphers, the bigram language model, the HMM and the feature extractor can
never drift out of sync about what "index 3" means.
"""

import numpy as np

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPACE = " "
ALPHABET = LETTERS + SPACE          # 27 symbols
N_LETTERS = 26
N_SYMBOLS = 27
SPACE_IDX = 26

_CHAR_TO_IDX = {c: i for i, c in enumerate(ALPHABET)}

# Letter frequencies of English text, in alphabetical order (percent).
ENGLISH_FREQ = np.array([
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153,
    0.772, 4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056,
    2.758, 0.978, 2.360, 0.150, 1.974, 0.074,
]) / 100.0

# Letters ordered from most to least common in English: ETAOIN SHRDLU...
ENGLISH_ORDER = "ETAOINSHRDLCUMWFGYPBVKJXQZ"


def clean(text, keep_spaces=True):
    """Upper-case the text and drop everything that is not A-Z (or space).

    Runs of whitespace collapse to a single space so the bigram counts are not
    swamped by line breaks in the corpus.
    """
    out = []
    prev_space = True                     # leading whitespace is dropped
    for ch in text.upper():
        if "A" <= ch <= "Z":
            out.append(ch)
            prev_space = False
        elif keep_spaces and (ch.isspace() or ch in ",.;:!?-'\"()"):
            if not prev_space:
                out.append(SPACE)
                prev_space = True
    return "".join(out).strip()


def to_indices(text):
    """Map a cleaned string to an int array over the 27-symbol alphabet."""
    return np.fromiter(
        (_CHAR_TO_IDX[c] for c in text if c in _CHAR_TO_IDX),
        dtype=np.int64,
        count=sum(1 for c in text if c in _CHAR_TO_IDX),
    )


def to_text(indices):
    """Inverse of :func:`to_indices`."""
    return "".join(ALPHABET[int(i)] for i in indices)


def letters_only(text):
    """Strip to A-Z, used by the classical ciphers that ignore spacing."""
    return clean(text, keep_spaces=False)


def is_letter_index(indices):
    """Boolean mask selecting the A-Z positions of an index array."""
    return indices < N_LETTERS
