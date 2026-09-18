"""Proposal distributions for the Metropolis-Hastings cipher solver.

A proposal takes the current decryption key and suggests a neighbouring one.
The four here trade off differently between exploring widely and being accepted
often, which is exactly the comparison the report asks for.

Keys arrive and leave as plain Python lists of 27 ints -- see :mod:`ml.scoring`
for why the chain avoids NumPy at this size.

Why symmetry matters
--------------------
The Metropolis acceptance rule ``min(1, exp(new - old))`` is only correct when
``q(k -> k') == q(k' -> k)``; otherwise the Hastings ratio has to be carried as
well.  Three of the four proposals are built to be exactly symmetric, so the
simple rule stays valid:

* ``random_swap``  picks an unordered pair uniformly.  Reversing the move means
  picking the same pair, so the two probabilities are identical.
* ``frequency``    weights pairs by how close the two cipher symbols are in
  *observed ciphertext* frequency rank.  Those ranks are a property of the
  message, not of the key, so the distribution over pairs never changes as the
  chain moves and the reverse move draws the same pair with the same weight.
* ``three_cycle``  picks three symbols uniformly, then one of the two rotation
  directions with probability 1/2.  The inverse of a rotation is the other
  rotation on the same three symbols, drawn with the same probability.
* ``adaptive``     is genuinely asymmetric: it re-weights pairs towards swaps
  that have paid off.  Validity is recovered by *freezing* the weights after a
  burn-in (the diminishing-adaptation condition), after which it behaves as a
  fixed, symmetric pair distribution like the others.
"""

import numpy as np

from ciphers.alphabet import N_LETTERS
from ml.rng import WeightedSampler

# Every unordered pair of letters, indexed once so the weighted proposals can
# sample a single integer instead of two.
PAIRS = [(i, j) for i in range(N_LETTERS) for j in range(i + 1, N_LETTERS)]
PAIR_INDEX = {pair: n for n, pair in enumerate(PAIRS)}


class Proposal:
    """Base class: propose a new key, given the current one."""

    name = "base"

    def __init__(self, stream):
        self.stream = stream

    def propose(self, key):
        """Return ``(new_key, moved_positions)``."""
        raise NotImplementedError

    def update(self, moved, delta, accepted):
        """Optional feedback hook, used only by the adaptive proposal."""

    def reset(self):
        """Called at the start of every restart."""


def _swapped(key, i, j):
    new_key = key[:]
    new_key[i], new_key[j] = key[j], key[i]
    return new_key


class RandomSwapProposal(Proposal):
    """Swap two letters chosen uniformly at random.  The textbook move."""

    name = "random_swap"

    def propose(self, key):
        i, j = self.stream.distinct(N_LETTERS, 2)
        return _swapped(key, i, j), (i, j)


class FrequencyGuidedProposal(Proposal):
    """Prefer swapping cipher symbols of similar observed frequency.

    Swapping the most common cipher symbol with the rarest is almost always a
    ruinous move that gets rejected.  The genuinely uncertain assignments sit
    between symbols that occur about equally often, so concentrating proposals
    there raises the acceptance rate and mixes faster.

    ``tau`` sets how tightly the proposal sticks to nearby ranks: small tau
    means near-neighbour swaps only, large tau decays to the uniform proposal.
    """

    name = "frequency"

    def __init__(self, stream, symbol_counts, tau=3.0):
        super().__init__(stream)
        counts = np.asarray(symbol_counts, dtype=np.float64)[:N_LETTERS]
        rank = np.empty(N_LETTERS, dtype=np.float64)
        rank[np.argsort(-counts, kind="stable")] = np.arange(N_LETTERS)

        weights = [np.exp(-abs(rank[i] - rank[j]) / tau) for i, j in PAIRS]
        self.sampler = WeightedSampler(stream, weights)

    def propose(self, key):
        i, j = PAIRS[self.sampler.draw()]
        return _swapped(key, i, j), (i, j)


class ThreeCycleProposal(Proposal):
    """Rotate three letters at once: a -> b -> c -> a.

    A bigger jump than a swap.  It can escape a local optimum where every
    single swap is downhill but a three-way rotation is uphill, which is the
    classic case of three letters being circularly misplaced.
    """

    name = "three_cycle"

    def __init__(self, stream, swap_mix=0.5):
        super().__init__(stream)
        # Pure three-cycles alone mix badly: they can never make the single
        # correction a swap makes.  Mixing in plain swaps keeps the chain able
        # to do both, and the mixture of two symmetric kernels is symmetric.
        self.swap_mix = swap_mix

    def propose(self, key):
        if self.stream.uniform() < self.swap_mix:
            i, j = self.stream.distinct(N_LETTERS, 2)
            return _swapped(key, i, j), (i, j)
        i, j, k = self.stream.distinct(N_LETTERS, 3)
        new_key = key[:]
        if self.stream.uniform() < 0.5:
            new_key[i], new_key[j], new_key[k] = key[k], key[i], key[j]
        else:
            new_key[i], new_key[j], new_key[k] = key[j], key[k], key[i]
        return new_key, (i, j, k)


class AdaptiveProposal(Proposal):
    """Learn which swaps tend to help, and propose those more often.

    Every accepted, improving swap adds to that pair's weight; other outcomes
    decay it slightly.  After ``freeze_after`` proposals the weights stop
    changing, which satisfies the diminishing-adaptation condition and leaves
    the chain with a fixed, symmetric proposal for the rest of the run.
    """

    name = "adaptive"

    def __init__(self, stream, reward=1.0, decay=0.995, freeze_after=4000,
                 refresh_every=250):
        super().__init__(stream)
        self.reward = reward
        self.decay = decay
        self.freeze_after = freeze_after
        self.refresh_every = refresh_every
        self.sampler = WeightedSampler(stream, [1.0] * len(PAIRS), block=refresh_every)
        self.reset()

    def reset(self):
        self.weights = [1.0] * len(PAIRS)
        self._proposals_made = 0
        self.sampler.set_weights(self.weights)

    @property
    def frozen(self):
        return self._proposals_made >= self.freeze_after

    def propose(self, key):
        self._proposals_made += 1
        i, j = PAIRS[self.sampler.draw()]
        return _swapped(key, i, j), (i, j)

    def update(self, moved, delta, accepted):
        if self.frozen:
            return
        n = PAIR_INDEX[(moved[0], moved[1]) if moved[0] < moved[1] else (moved[1], moved[0])]
        if accepted and delta > 0:
            self.weights[n] += self.reward
        else:
            self.weights[n] = max(self.weights[n] * self.decay, 1e-3)
        # Rebuilding the sampler every step would dominate the runtime; every
        # few hundred steps is often enough for the weights to steer the search.
        if self._proposals_made % self.refresh_every == 0 or self._proposals_made == self.freeze_after:
            self.sampler.set_weights(self.weights)


PROPOSAL_NAMES = ["random_swap", "frequency", "three_cycle", "adaptive"]

PROPOSAL_LABELS = {
    "random_swap": "Random swap",
    "frequency": "Frequency-guided swap",
    "three_cycle": "Three-letter cycle",
    "adaptive": "Adaptive swap",
}


def build_proposal(name, stream, symbol_counts=None, **kwargs):
    name = (name or "random_swap").lower()
    if name == "random_swap":
        return RandomSwapProposal(stream)
    if name == "frequency":
        if symbol_counts is None:
            raise ValueError("the frequency proposal needs the ciphertext symbol counts")
        return FrequencyGuidedProposal(stream, symbol_counts, **kwargs)
    if name == "three_cycle":
        return ThreeCycleProposal(stream, **kwargs)
    if name == "adaptive":
        return AdaptiveProposal(stream, **kwargs)
    raise ValueError(f"unknown proposal {name!r}; expected one of {PROPOSAL_NAMES}")
