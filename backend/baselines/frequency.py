"""Frequency analysis: the classical, pre-computer attack.

Rank the ciphertext letters by how often they occur, rank the English letters
the same way, and line the two lists up.  It needs no search at all, which is
its charm and its ceiling: single-letter frequencies are far too noisy to pin
down a 26-letter key, so it usually lands around a quarter of the letters
correct and stops there.  It is in the project as the floor that MCMC and the
HMM have to beat.

The Caesar version of the same idea *is* enough, because a Caesar key is one
number rather than a permutation: score all 26 shifts and keep the best.
"""

import time

import numpy as np

from ciphers.alphabet import (
    ENGLISH_FREQ,
    ENGLISH_ORDER,
    LETTERS,
    N_LETTERS,
    N_SYMBOLS,
    clean,
    to_indices,
    to_text,
)
from ciphers.substitution import array_to_key
from ml.language_model import get_model
from ml.mcmc import CrackResult, frequency_seeded_key
from ml.scoring import KeyScorer


def letter_counts(text):
    indices = to_indices(clean(text))
    return np.bincount(indices, minlength=N_SYMBOLS).astype(float)


def crack(ciphertext, model=None, **_):
    """Map cipher letters to English letters purely by frequency rank."""
    started = time.perf_counter()
    model = model or get_model()
    text = clean(ciphertext)
    indices = to_indices(text)
    if len(indices) < 2:
        raise ValueError("ciphertext is too short to analyse")

    counts = np.bincount(indices, minlength=N_SYMBOLS).astype(float)
    key = frequency_seeded_key(counts)

    scorer = KeyScorer(indices, model.log_probs)
    score = scorer.score_list(key)
    symbols = LETTERS + " "

    return CrackResult(
        key=array_to_key(key[:N_LETTERS]),
        plaintext="".join(symbols[key[int(i)]] for i in indices),
        score=score,
        score_per_char=scorer.per_char(score),
        iterations=1,
        elapsed=time.perf_counter() - started,
        restarts=1,
        accepted=0,
        proposal="none",
        solver="frequency_analysis",
    )


def chi_squared_caesar(ciphertext):
    """Best Caesar shift by chi-squared distance to English letter frequencies.

    Returns ``(shift, distances)`` where ``distances[s]`` is the chi-squared
    statistic for shift ``s`` -- lower is more English-like.
    """
    counts = letter_counts(ciphertext)[:N_LETTERS]
    total = counts.sum()
    if total == 0:
        return 0, np.zeros(N_LETTERS)

    expected = ENGLISH_FREQ * total
    distances = np.empty(N_LETTERS)
    for shift in range(N_LETTERS):
        observed = np.roll(counts, -shift)     # undo the shift
        distances[shift] = np.sum((observed - expected) ** 2 / np.maximum(expected, 1e-9))
    return int(np.argmin(distances)), distances


def index_of_coincidence(text):
    """Probability that two letters drawn at random from the text match.

    English sits near 0.067 and a flat random distribution near 0.038, so this
    one number separates the ciphers that preserve letter frequencies (Caesar,
    substitution, transposition) from the one that flattens them (Vigenere).
    """
    counts = letter_counts(text)[:N_LETTERS]
    n = counts.sum()
    if n < 2:
        return 0.0
    return float((counts * (counts - 1)).sum() / (n * (n - 1)))
