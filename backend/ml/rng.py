"""Batched random-number helpers for the MCMC inner loop.

``numpy.random.Generator`` is excellent per *array* and poor per *scalar*: a
single ``rng.random()`` costs about as much as filling a whole buffer, because
almost all of the time is Python call overhead rather than generation.  The
MCMC chain needs one uniform and one proposal index per iteration, one at a
time, so we draw them thousands at a time and hand them out from a buffer.

Every draw still comes from the same seeded ``Generator``, so runs stay exactly
reproducible for a given seed.
"""

import numpy as np

BLOCK = 8192


class RandomStream:
    """Scalar draws from a numpy Generator, buffered in blocks."""

    def __init__(self, seed=None, block=BLOCK):
        self.rng = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
        self.block = block
        self._uniforms = None
        self._u_pos = block
        self._ints = {}

    def uniform(self):
        if self._u_pos >= self.block:
            self._uniforms = self.rng.random(self.block).tolist()
            self._u_pos = 0
        value = self._uniforms[self._u_pos]
        self._u_pos += 1
        return value

    def index(self, n):
        """A uniform integer in ``[0, n)``."""
        state = self._ints.get(n)
        if state is None or state[1] >= self.block:
            buf = self.rng.integers(0, n, size=self.block).tolist()
            state = [buf, 0]
            self._ints[n] = state
        value = state[0][state[1]]
        state[1] += 1
        return value

    def distinct(self, n, count):
        """``count`` distinct integers from ``[0, n)``, via rejection.

        For ``count`` of 2 or 3 out of 26 the retry probability is tiny, so this
        is far cheaper than ``rng.choice(..., replace=False)``, which builds a
        permutation every call.
        """
        first = self.index(n)
        picks = [first]
        while len(picks) < count:
            candidate = self.index(n)
            if candidate not in picks:
                picks.append(candidate)
        return picks


class WeightedSampler:
    """Buffered draws from a fixed categorical distribution over indices.

    ``numpy``'s weighted ``choice`` normalises and builds a CDF on every call,
    which is ruinous one draw at a time; drawing a block at a time amortises it.
    Call :meth:`set_weights` when the distribution changes (the adaptive
    proposal does this every few hundred steps) and the buffer is refilled.
    """

    def __init__(self, stream, weights, block=1024):
        self.stream = stream
        self.block = block
        self.set_weights(weights)

    def set_weights(self, weights):
        probs = np.asarray(weights, dtype=np.float64)
        total = probs.sum()
        if not np.isfinite(total) or total <= 0:
            probs = np.ones_like(probs)
            total = probs.sum()
        self.probs = probs / total
        self._buf = []
        self._pos = 0

    def draw(self):
        if self._pos >= len(self._buf):
            self._buf = self.stream.rng.choice(
                len(self.probs), size=self.block, p=self.probs
            ).tolist()
            self._pos = 0
        value = self._buf[self._pos]
        self._pos += 1
        return value
