"""Metropolis-Hastings solver for monoalphabetic substitution ciphers.

The search space has 26! ~ 4e26 keys, so it is never enumerated.  Instead the
chain wanders it, always willing to move to a more English-looking key and
*sometimes* willing to move to a worse one -- which is the only reason it can
climb back out of a local optimum.  Plain hill climbing is the same algorithm
with that second behaviour switched off, and it gets stuck far more often; the
Arena page puts the two side by side.

The loop
--------
1. start from a key (random, or seeded by frequency analysis)
2. propose a neighbouring key (see :mod:`ml.proposals`)
3. accept it with probability ``min(1, exp((new - old) / T))``
4. remember the best key ever seen, and repeat
5. run several independent restarts, because some chains do get stuck

Cost per iteration is set by :class:`ml.scoring.KeyScorer`, which rescores only
the handful of bigram terms a proposal actually disturbs.
"""

import math
import time
from dataclasses import dataclass, field

from ciphers.alphabet import (
    ENGLISH_ORDER,
    N_LETTERS,
    N_SYMBOLS,
    clean,
    to_indices,
    to_text,
)
from ciphers.substitution import array_to_key
from ml.language_model import get_model
from ml.proposals import PROPOSAL_NAMES, build_proposal
from ml.rng import RandomStream
from ml.scoring import KeyScorer


@dataclass
class CrackResult:
    """What a solver run produced, plus the diagnostics the report wants."""

    key: str                       # decryption key: cipher letter -> plain letter
    plaintext: str
    score: float
    score_per_char: float
    iterations: int
    elapsed: float
    restarts: int
    accepted: int
    proposal: str = ""
    history: list = field(default_factory=list)
    stopped_early: bool = False
    solver: str = "mcmc"
    extra: dict = field(default_factory=dict)

    @property
    def acceptance_rate(self):
        return self.accepted / self.iterations if self.iterations else 0.0

    @property
    def rate(self):
        return self.iterations / self.elapsed if self.elapsed else 0.0

    def to_dict(self):
        payload = {
            "solver": self.solver,
            "key": self.key,
            "plaintext": self.plaintext,
            "score": self.score,
            "score_per_char": self.score_per_char,
            "iterations": self.iterations,
            "elapsed": self.elapsed,
            "restarts": self.restarts,
            "accepted": self.accepted,
            "acceptance_rate": self.acceptance_rate,
            "iterations_per_second": self.rate,
            "proposal": self.proposal,
            "history": self.history,
            "stopped_early": self.stopped_early,
        }
        payload.update(self.extra)
        return payload


def identity_key():
    """A key that changes nothing; index 26 (space) is always fixed."""
    return list(range(N_SYMBOLS))


def random_key(stream):
    """Uniformly random permutation of the 26 letters, space left alone."""
    key = identity_key()
    letters = stream.rng.permutation(N_LETTERS).tolist()
    key[:N_LETTERS] = letters
    return key


def frequency_seeded_key(symbol_counts):
    """Match the cipher's letter ranks to English letter ranks.

    A poor key on its own -- single-letter frequencies are noisy on short texts
    -- but a much better starting point than random, and it is what we use to
    initialise Baum-Welch as well.
    """
    counts = list(symbol_counts[:N_LETTERS])
    cipher_order = sorted(range(N_LETTERS), key=lambda i: -counts[i])
    key = identity_key()
    for rank, symbol in enumerate(cipher_order):
        key[symbol] = ord(ENGLISH_ORDER[rank]) - 65
    return key


def decode_indices(indices, key):
    """Apply a decryption key to an index array, returning text."""
    return "".join(_SYMBOLS[key[int(i)]] for i in indices)


_SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ "


def letter_accuracy(guess_text, truth_text):
    """Fraction of letter positions decoded correctly.  The headline metric."""
    pairs = [(a, b) for a, b in zip(guess_text, truth_text) if b != " "]
    if not pairs:
        return 0.0
    return sum(1 for a, b in pairs if a == b) / len(pairs)


class MCMCSolver:
    """Runs the Metropolis-Hastings chain over substitution keys."""

    solver_name = "mcmc"

    def __init__(
        self,
        ciphertext,
        model=None,
        proposal="random_swap",
        iterations=10_000,
        restarts=5,
        temperature=1.0,
        anneal_to=None,
        seed=None,
        seed_with_frequency=False,
        hill_climb=False,
    ):
        if proposal not in PROPOSAL_NAMES:
            raise ValueError(f"unknown proposal {proposal!r}")
        self.model = model or get_model()
        self.text = clean(ciphertext)
        self.indices = to_indices(self.text)
        if len(self.indices) < 2:
            raise ValueError("ciphertext is too short to score (need 2+ symbols)")

        self.scorer = KeyScorer(self.indices, self.model.log_probs)
        self.symbol_counts = self.scorer.symbol_counts()

        self.iterations = int(iterations)
        self.restarts = max(int(restarts), 1)
        self.temperature = float(temperature)
        self.anneal_to = anneal_to
        self.seed_with_frequency = seed_with_frequency
        # Hill climbing is this same chain with the "accept a worse key" branch
        # switched off; keeping it here makes the Arena comparison exact.
        self.hill_climb = hill_climb
        self.proposal_name = proposal

        self.stream = RandomStream(seed)
        self.proposal = build_proposal(proposal, self.stream, symbol_counts=self.symbol_counts)

    # ------------------------------------------------------------------ utils

    def decode(self, key):
        return decode_indices(self.indices, key)

    def _temperature_at(self, step, total):
        if self.anneal_to is None:
            return self.temperature
        # Geometric cooling from `temperature` down to `anneal_to`.
        frac = step / max(total - 1, 1)
        return self.temperature * (self.anneal_to / self.temperature) ** frac

    def _record(self, step, restart, current, best, temp, accepted):
        return {
            "iteration": step,
            "restart": restart,
            "score": current,
            "best_score": best,
            "score_per_char": self.scorer.per_char(current),
            "best_score_per_char": self.scorer.per_char(best),
            "temperature": temp,
            "acceptance_rate": accepted / step if step else 0.0,
        }

    # -------------------------------------------------------------------- run

    def run(self, callback=None, report_every=100, should_stop=None):
        started = time.perf_counter()
        scorer, proposal, stream = self.scorer, self.proposal, self.stream
        delta_fn, uniform = scorer.delta, stream.uniform
        exp, constant_temp = math.exp, self.anneal_to is None
        temp = self.temperature
        greedy = self.hill_climb

        best_key, best_score = None, -math.inf
        history, total_steps, total_accepted = [], 0, 0
        stopped = False
        restart = 0

        for restart in range(self.restarts):
            if stopped:
                break
            proposal.reset()
            if self.seed_with_frequency and restart == 0:
                key = frequency_seeded_key(self.symbol_counts)
            else:
                key = random_key(stream)
            current = scorer.score_list(key)

            if current > best_score:
                best_key, best_score = key[:], current

            for step in range(self.iterations):
                if not constant_temp:
                    temp = self._temperature_at(step, self.iterations)
                new_key, moved = proposal.propose(key)
                change = delta_fn(key, new_key, moved)

                # min(1, exp(change / T)): always take an improvement, and take
                # a worsening move with a probability that falls off fast.
                if change > 0:
                    accepted = True
                elif greedy:
                    accepted = False
                else:
                    accepted = uniform() < exp(change / temp)

                if accepted:
                    key, current = new_key, current + change
                    total_accepted += 1
                    if current > best_score:
                        best_key, best_score = key[:], current
                proposal.update(moved, change, accepted)

                total_steps += 1
                if report_every and total_steps % report_every == 0:
                    record = self._record(
                        total_steps, restart, current, best_score, temp, total_accepted
                    )
                    history.append(record)
                    if callback is not None:
                        payload = dict(record)
                        payload["key"] = array_to_key(best_key[:N_LETTERS])
                        payload["text"] = self.decode(best_key)
                        callback(payload)
                    if should_stop is not None and should_stop():
                        stopped = True
                        break

            # Deltas accumulate a little floating-point drift over tens of
            # thousands of additions; re-score the survivor exactly.
            best_score = scorer.score_list(best_key)

        elapsed = time.perf_counter() - started
        return CrackResult(
            key=array_to_key(best_key[:N_LETTERS]),
            plaintext=self.decode(best_key),
            score=best_score,
            score_per_char=scorer.per_char(best_score),
            iterations=total_steps,
            elapsed=elapsed,
            restarts=restart + 1,
            accepted=total_accepted,
            proposal=self.proposal_name,
            history=history,
            stopped_early=stopped,
            solver="hill_climbing" if greedy else self.solver_name,
        )


def crack(ciphertext, **kwargs):
    """Convenience wrapper: solve a ciphertext and return a :class:`CrackResult`."""
    callback = kwargs.pop("callback", None)
    report_every = kwargs.pop("report_every", 100)
    should_stop = kwargs.pop("should_stop", None)
    solver = MCMCSolver(ciphertext, **kwargs)
    return solver.run(callback=callback, report_every=report_every, should_stop=should_stop)
