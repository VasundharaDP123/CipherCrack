"""Turning a ciphertext into numbers a classifier can work with.

The features are chosen so that each cipher class leaves a different
fingerprint, rather than thrown in and left to the forest to sort out:

=============  ==========================================================
Transposition  only reorders letters, so its letter frequencies *are*
               English: chi-squared to English is near zero.  But it
               shreds bigrams and trigrams, so repeats collapse.
Caesar         frequencies are English *rotated*: chi-squared is high at
               shift 0 and near zero at the right shift.
Substitution   frequency *shape* is English but no rotation aligns it, so
               chi-squared stays high at every shift while the sorted
               profile still looks English and the IC stays near 0.066.
Vigenere       averages several alphabets together and flattens the
               distribution: the IC drops towards 0.038 and the sorted
               profile goes level.  Splitting the text into ``k`` columns
               restores a high IC exactly when ``k`` is the key length.
=============  ==========================================================

That gives the three quantities that do most of the separating -- the index of
coincidence, chi-squared at shift 0, and chi-squared minimised over shifts --
with the sorted frequency profile and the repeat statistics behind them.
"""

import numpy as np

from ciphers.alphabet import ENGLISH_FREQ, N_LETTERS, clean, letters_only, to_indices

MAX_PERIOD = 12
FLAT_IC = 1.0 / N_LETTERS          # 0.0385: a uniform random alphabet
ENGLISH_IC = 0.0667                # English prose


def _counts(indices):
    return np.bincount(indices, minlength=N_LETTERS).astype(float)[:N_LETTERS]


def index_of_coincidence(counts):
    """Chance that two letters drawn without replacement match.

    The single most useful number here: it survives any monoalphabetic
    substitution untouched (relabelling letters cannot change how often two
    of them coincide) but collapses under a polyalphabetic one.
    """
    n = counts.sum()
    if n < 2:
        return 0.0
    return float((counts * (counts - 1)).sum() / (n * (n - 1)))


def shannon_entropy(counts):
    """Entropy of the letter distribution, in bits.  Flat alphabets score high."""
    n = counts.sum()
    if n == 0:
        return 0.0
    p = counts[counts > 0] / n
    return float(-(p * np.log2(p)).sum())


def chi_squared_to_english(counts, shift=0):
    n = counts.sum()
    if n == 0:
        return 0.0
    expected = ENGLISH_FREQ * n
    observed = np.roll(counts, -shift)
    return float(np.sum((observed - expected) ** 2 / np.maximum(expected, 1e-9)) / n)


def chi_squared_over_shifts(counts):
    """``(at shift 0, best over all 26 shifts, which shift)``."""
    values = np.array([chi_squared_to_english(counts, s) for s in range(N_LETTERS)])
    return float(values[0]), float(values.min()), int(values.argmin())


def repeat_rate(indices, size):
    """Fraction of ``size``-grams that occur more than once.

    English is full of repeated trigrams (THE, ING, AND) and a substitution
    keeps every one of them; a transposition destroys nearly all of them.
    """
    n = len(indices) - size + 1
    if n < 2:
        return 0.0
    scale = N_LETTERS + 1
    grams = np.zeros(n, dtype=np.int64)
    for offset in range(size):
        grams = grams * scale + indices[offset:offset + n]
    _, counts = np.unique(grams, return_counts=True)
    return float(counts[counts > 1].sum() / n)


def periodic_ic(indices, max_period=MAX_PERIOD):
    """Average IC of every ``k``-th letter, for ``k`` up to ``max_period``.

    A Vigenere ciphertext split into ``k`` columns is ``k`` separate Caesar
    ciphers when ``k`` is the key length, so each column recovers an
    English-like IC.  The peak of this curve is the Kasiski test, done with
    arithmetic instead of by hand.
    """
    letters = indices[indices < N_LETTERS]
    profile = np.full(max_period, FLAT_IC)
    for period in range(1, max_period + 1):
        if len(letters) < period * 8:          # too few letters per column to trust
            break
        ics = [index_of_coincidence(_counts(letters[start::period]))
               for start in range(period)]
        profile[period - 1] = float(np.mean(ics))
    return profile


def doubled_letter_rate(indices):
    """How often a letter is immediately repeated (LL, SS, EE).

    Preserved exactly by substitution and Caesar, destroyed by transposition
    and by Vigenere (which maps the two halves of a double to different
    letters unless the key repeats).
    """
    letters = indices[indices < N_LETTERS]
    if len(letters) < 2:
        return 0.0
    return float(np.mean(letters[:-1] == letters[1:]))


FEATURE_NAMES = (
    ["index_of_coincidence", "entropy", "chi2_shift0", "chi2_best_shift",
     "chi2_shift_gap", "bigram_repeat_rate", "trigram_repeat_rate",
     "doubled_letter_rate", "best_period", "best_period_ic", "period_ic_lift"]
    + [f"sorted_freq_{i:02d}" for i in range(N_LETTERS)]
    + [f"period_ic_{k}" for k in range(1, MAX_PERIOD + 1)]
)


def extract(text):
    """Feature vector for one ciphertext.  Order matches :data:`FEATURE_NAMES`."""
    indices = to_indices(letters_only(text))
    if len(indices) < 4:
        return np.zeros(len(FEATURE_NAMES))

    counts = _counts(indices)
    total = max(counts.sum(), 1.0)
    ic = index_of_coincidence(counts)
    chi0, chi_best, _ = chi_squared_over_shifts(counts)
    profile = periodic_ic(indices)

    # Period 1 is the whole text; the lift over it is what says "polyalphabetic".
    best_period = int(np.argmax(profile)) + 1
    best_period_ic = float(profile.max())

    scalars = [
        ic,
        shannon_entropy(counts),
        chi0,
        chi_best,
        chi0 - chi_best,
        repeat_rate(indices, 2),
        repeat_rate(indices, 3),
        doubled_letter_rate(indices),
        best_period,
        best_period_ic,
        best_period_ic - profile[0],
    ]
    sorted_profile = np.sort(counts / total)[::-1]
    return np.concatenate([scalars, sorted_profile, profile])


def extract_many(texts):
    return np.vstack([extract(t) for t in texts])


def describe(text):
    """Feature vector as a name -> value mapping, for the API to show."""
    return dict(zip(FEATURE_NAMES, extract(text).tolist()))
