"""The English bigram model: a 27x27 table of letter-pair log-probabilities.

This is the single scoring function behind every solver in the project.  The
idea is the whole trick of the MCMC decipherment method: we cannot recognise
the *right* key directly, but we can measure how English-like a decoded text
looks, and then climb that measure.

Build
-----
* clean the training books to the 27 symbols A-Z and space
* count every adjacent pair into a 27x27 matrix
* add 1 to every cell (Laplace smoothing) so an unseen pair costs a lot but
  never costs ``-inf``, which would freeze the MCMC chain
* normalise each row to a conditional distribution and take logs

Scoring a key in O(1) with respect to text length
-------------------------------------------------
The naive score walks the decoded text and adds ``log P(next | current)``, so
it costs O(n) per proposal.  But the sum only depends on *how many times* each
cipher pair occurs, not where::

    score(key) = sum_t  logP[ key[c_t], key[c_{t+1}] ]
               = sum_{a,b}  C[a, b] * logP[ key[a], key[b] ]

where ``C`` is the ciphertext's own 27x27 bigram count matrix, computed once.
Every later evaluation is a fixed 729-cell dot product no matter whether the
message is 400 characters or 400,000.  This is what gets us to the ~50k
iterations/second target.
"""

import pathlib

import numpy as np

from ciphers.alphabet import N_SYMBOLS, SPACE_IDX, clean, to_indices

ROOT = pathlib.Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "corpus"
MODEL_PATH = ROOT / "data" / "bigram_model.npz"


def count_bigrams(indices, n_symbols=N_SYMBOLS):
    """27x27 matrix of adjacent-pair counts, via a single bincount."""
    if len(indices) < 2:
        return np.zeros((n_symbols, n_symbols), dtype=np.float64)
    flat = indices[:-1] * n_symbols + indices[1:]
    counts = np.bincount(flat, minlength=n_symbols * n_symbols)
    return counts.reshape(n_symbols, n_symbols).astype(np.float64)


class LanguageModel:
    """Holds the trained log-probability table and scores text against it."""

    def __init__(self, counts, sources=None):
        self.counts = np.asarray(counts, dtype=np.float64)
        self.sources = list(sources or [])

        smoothed = self.counts + 1.0                      # Laplace
        self.log_probs = np.log(smoothed / smoothed.sum(axis=1, keepdims=True))

        unigram = self.counts.sum(axis=1) + 1.0
        self.unigram_log_probs = np.log(unigram / unigram.sum())

        # Row-stochastic version, used as the HMM's fixed transition matrix.
        self.transitions = smoothed / smoothed.sum(axis=1, keepdims=True)
        self.initial = unigram / unigram.sum()

    # ---------------------------------------------------------------- scoring

    def score_indices(self, indices):
        """Total log-probability of an index sequence.  O(n)."""
        if len(indices) < 2:
            return 0.0
        return float(self.log_probs[indices[:-1], indices[1:]].sum())

    def score_text(self, text):
        return self.score_indices(to_indices(clean(text)))

    def score_per_char(self, text):
        """Length-normalised score, so 100- and 1000-character texts compare.

        English lands near -2.1, random letters near -3.3.
        """
        indices = to_indices(clean(text))
        if len(indices) < 2:
            return 0.0
        return self.score_indices(indices) / (len(indices) - 1)

    def score_counts(self, counts, key_array):
        """Score a decryption key against precomputed ciphertext bigram counts.

        ``key_array`` maps cipher symbol -> plaintext symbol (length 27).
        Cost is independent of the message length.
        """
        return float(np.sum(counts * self.log_probs[np.ix_(key_array, key_array)]))

    def mapped_log_probs(self, key_array):
        """``L[a, b] = logP(key[a] -> key[b])`` -- the per-key score table."""
        return self.log_probs[np.ix_(key_array, key_array)]

    # ------------------------------------------------------------ persistence

    def save(self, path=MODEL_PATH):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path, counts=self.counts, sources=np.array(self.sources, dtype=object)
        )
        return path

    @classmethod
    def load(cls, path=MODEL_PATH):
        data = np.load(path, allow_pickle=True)
        return cls(data["counts"], list(data["sources"]))

    @classmethod
    def from_corpus(cls, directory=None, pattern="*.txt"):
        directory = pathlib.Path(directory or CORPUS_DIR / "train")
        files = sorted(directory.glob(pattern))
        if not files:
            raise FileNotFoundError(
                f"no corpus files in {directory}. Run: python -m scripts.build_corpus"
            )
        counts = np.zeros((N_SYMBOLS, N_SYMBOLS), dtype=np.float64)
        sources = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            counts += count_bigrams(to_indices(clean(text)))
            sources.append(path.name)
        return cls(counts, sources)

    # ------------------------------------------------------------- reporting

    def summary(self):
        total = self.counts.sum()
        return {
            "sources": self.sources,
            "bigrams_counted": int(total),
            "distinct_pairs_seen": int((self.counts > 0).sum()),
            "space_fraction": float(self.counts[SPACE_IDX].sum() / max(total, 1)),
        }


_MODEL = None


def get_model(rebuild=False):
    """Process-wide singleton.  Builds from the corpus the first time."""
    global _MODEL
    if _MODEL is not None and not rebuild:
        return _MODEL
    if MODEL_PATH.exists() and not rebuild:
        _MODEL = LanguageModel.load()
    else:
        _MODEL = LanguageModel.from_corpus()
        _MODEL.save()
    return _MODEL
