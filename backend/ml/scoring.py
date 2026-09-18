"""Scoring a substitution key against one fixed ciphertext.

Three levels of the same quantity, fastest last:

1. **Walk the text.**  ``sum log P(next | current)`` over the decoded message.
   O(n) per key -- fine once, hopeless inside a chain.

2. **Bigram counts.**  The sum only depends on *how many times* each cipher
   pair occurs, so precompute the ciphertext's own 27x27 count matrix ``C``::

       score(key) = sum_{a,b} C[a,b] * logP[key[a], key[b]]

   Now every evaluation is a fixed 729-cell reduction, independent of message
   length.  :meth:`KeyScorer.score` does this.

3. **Only what moved.**  A proposal swaps two letters, so the only terms that
   change are those whose row or column is one of the two.  For a typical
   message that is ~40 terms instead of 729, and -- crucially -- it is 40 terms
   of *plain Python*.  :meth:`KeyScorer.delta` does this.

Why plain Python for step 3
---------------------------
At this size NumPy is the wrong tool.  A 27x27 array operation is dominated by
per-call dispatch overhead, not arithmetic, so a handful of NumPy calls costs
more than forty list lookups.  The measured crossover is in
``scripts/bench_mcmc.py``; keys are therefore carried through the chain as
plain Python lists and only converted back to arrays when reporting.
"""

import numpy as np

from ciphers.alphabet import N_SYMBOLS
from ml.language_model import count_bigrams


class KeyScorer:
    """Scores decryption keys for one ciphertext.

    A key is a length-27 sequence mapping cipher symbol -> plaintext symbol.
    Index 26 (space) is expected to map to itself, and the scorer never
    proposes otherwise.
    """

    def __init__(self, indices, log_probs):
        self.indices = np.asarray(indices)
        self.counts = count_bigrams(self.indices)
        self.log_probs = np.asarray(log_probs, dtype=np.float64)
        self.n_bigrams = max(len(self.indices) - 1, 1)

        # Plain nested lists: Python-level indexing on these is several times
        # faster than pulling scalars out of a NumPy array.
        self._log = self.log_probs.tolist()

        # Adjacency lists of the ciphertext's bigram graph.  ``_out[a]`` holds
        # every (b, count) with C[a][b] > 0; ``_in[b]`` holds every (a, count).
        counts = self.counts.tolist()
        self._out = [[] for _ in range(N_SYMBOLS)]
        self._in = [[] for _ in range(N_SYMBOLS)]
        for a in range(N_SYMBOLS):
            row = counts[a]
            for b in range(N_SYMBOLS):
                c = row[b]
                if c:
                    self._out[a].append((b, c))
                    self._in[b].append((a, c))

    # ------------------------------------------------------------------ whole

    def score(self, key):
        """Full score of a key.  O(1) in the message length."""
        key = np.asarray(key)
        return float(np.sum(self.counts * self.log_probs[np.ix_(key, key)]))

    def score_list(self, key):
        """Full score without NumPy, for keys already held as Python lists."""
        log, total = self._log, 0.0
        for a in range(N_SYMBOLS):
            out = self._out[a]
            if not out:
                continue
            row = log[key[a]]
            for b, c in out:
                total += c * row[key[b]]
        return total

    # ------------------------------------------------------------- what moved

    def delta(self, key, new_key, moved):
        """Score change from ``key`` to ``new_key``, which differ at ``moved``.

        Works for any rearrangement of the moved positions -- a two-way swap or
        a three-way cycle -- because it simply re-adds every affected term under
        both keys.  Rows of moved positions are visited in full; their columns
        skip sources that are themselves moved, so the overlapping block in the
        corner is counted exactly once.
        """
        log = self._log
        total = 0.0
        moved_set = moved if len(moved) == 2 else set(moved)

        for a in moved:
            old_a, new_a = key[a], new_key[a]
            row_old, row_new = log[old_a], log[new_a]
            for b, c in self._out[a]:
                total += c * (row_new[new_key[b]] - row_old[key[b]])
            for src, c in self._in[a]:
                if src in moved_set:
                    continue                      # already covered by its row
                row = log[key[src]]               # unmoved, so key == new_key
                total += c * (row[new_a] - row[old_a])
        return total

    # ------------------------------------------------------------------ misc

    def symbol_counts(self):
        """How often each of the 27 symbols occurs in the ciphertext."""
        return np.bincount(self.indices, minlength=N_SYMBOLS).astype(float)

    def per_char(self, score):
        return score / self.n_bigrams
