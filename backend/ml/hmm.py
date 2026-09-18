"""The cipher as a Hidden Markov Model, solved with Baum-Welch.

Where MCMC *searches* the space of keys, the HMM *learns* the key as a
parameter.  The mapping onto the standard HMM vocabulary is the thing to be
able to recite in the viva:

===================  =========================================================
hidden states        the 27 plaintext symbols (A-Z and space)
observations         the 27 ciphertext symbols
transitions ``A``    the English bigram model -- **known, and held fixed**
emissions ``B``      the key: ``B[i, k] = P(cipher k | plain i)`` -- **unknown**
initial ``pi``       English unigram frequencies
===================  =========================================================

Only ``B`` is estimated.  That is the whole reason this works: English letter
order is not a mystery, so re-learning ``A`` from a few hundred characters
would only throw away good information and make the likelihood surface far
worse.  Freezing ``A`` turns an under-determined problem into one with exactly
27x27 free parameters and a strong prior pulling ``B`` towards a permutation.

Everything here is written from scratch over NumPy:

* :meth:`CipherHMM.forward`   -- scaled forward pass, gives the likelihood
* :meth:`CipherHMM.backward`  -- scaled backward pass
* :meth:`CipherHMM.baum_welch` -- EM over ``B`` alone
* :meth:`CipherHMM.viterbi`   -- most likely plaintext, in log space

Scaling rather than logs
------------------------
The forward pass multiplies many probabilities together and underflows within
a few dozen characters.  Rather than move to log space -- which would replace
each matrix-vector product with a much slower log-sum-exp -- each column is
normalised to sum to one and the normaliser is kept.  The log-likelihood is
then just ``-sum(log c_t)``, exactly, and the arithmetic stays in fast BLAS.
Viterbi *does* run in log space, because it only ever adds.
"""

import time

import numpy as np

from ciphers.alphabet import N_LETTERS, N_SYMBOLS, SPACE_IDX, clean, to_indices, to_text
from ciphers.substitution import array_to_key
from ml.language_model import get_model
from ml.mcmc import CrackResult, frequency_seeded_key

EPS = 1e-12


class CipherHMM:
    """An HMM whose transitions are known English and whose emissions are the key."""

    def __init__(self, transitions=None, initial=None, model=None, fix_space=True):
        model = model or get_model()
        self.A = np.asarray(transitions if transitions is not None else model.transitions,
                            dtype=np.float64)
        self.pi = np.asarray(initial if initial is not None else model.initial,
                             dtype=np.float64)
        self.n_states = self.A.shape[0]
        self.log_A = np.log(self.A + EPS)
        self.log_pi = np.log(self.pi + EPS)

        # A substitution cipher leaves word breaks visible, so "space enciphers
        # to space" is a fact about the message, not a guess.  Pinning it costs
        # nothing when the text has no spaces and helps a great deal when it
        # does, because it anchors every word boundary for the transitions.
        self.fix_space = fix_space

    # -------------------------------------------------------------- emissions

    def random_emissions(self, rng, concentration=1.0):
        """A random but valid ``B``, drawn from a symmetric Dirichlet."""
        B = rng.gamma(concentration, size=(self.n_states, N_SYMBOLS))
        return self._normalise(B)

    def emissions_from_key(self, key, confidence=0.55):
        """Turn a decryption key into a ``B`` that leans towards it.

        ``confidence`` is how much probability mass the seeded mapping keeps;
        the rest is spread uniformly so Baum-Welch can still move away from a
        wrong guess.  Seeding at 1.0 would be a fixed point and EM would never
        leave it.
        """
        B = np.full((self.n_states, N_SYMBOLS), (1.0 - confidence) / N_SYMBOLS)
        for cipher_symbol, plain_symbol in enumerate(key):
            B[plain_symbol, cipher_symbol] += confidence
        return self._normalise(B)

    def _normalise(self, B):
        if self.fix_space:
            B[SPACE_IDX, :] = 0.0
            B[:, SPACE_IDX] = 0.0
            B[SPACE_IDX, SPACE_IDX] = 1.0
        B = np.maximum(B, EPS)
        if self.fix_space:
            B[SPACE_IDX, :] = 0.0
            B[:, SPACE_IDX] = 0.0
            B[SPACE_IDX, SPACE_IDX] = 1.0
        return B / B.sum(axis=1, keepdims=True)

    # ---------------------------------------------------------------- forward

    def forward(self, obs, B):
        """Scaled forward pass.

        Returns ``(alpha, scales, loglik)`` where ``alpha[t]`` is
        ``P(state_t = i | O_1..t)`` -- already normalised -- and ``loglik`` is
        the exact log-likelihood of the observation sequence.
        """
        n = len(obs)
        A = self.A
        emit = B[:, obs]                      # (states, n): gathered once
        alpha = np.empty((n, self.n_states))
        scales = np.empty(n)

        a = self.pi * emit[:, 0]
        scales[0] = a.sum() + EPS
        alpha[0] = a / scales[0]
        for t in range(1, n):
            a = (alpha[t - 1] @ A) * emit[:, t]
            scales[t] = a.sum() + EPS
            alpha[t] = a / scales[t]

        return alpha, scales, float(np.log(scales).sum())

    def backward(self, obs, B, scales):
        """Scaled backward pass, reusing the forward pass's scaling factors."""
        n = len(obs)
        A = self.A
        emit = B[:, obs]
        beta = np.empty((n, self.n_states))
        beta[n - 1] = 1.0
        for t in range(n - 2, -1, -1):
            beta[t] = A @ (emit[:, t + 1] * beta[t + 1]) / scales[t + 1]
        return beta

    def posteriors(self, obs, B):
        """``gamma[t, i] = P(state_t = i | O)``, plus the log-likelihood.

        Re-estimating ``B`` needs only these per-state posteriors -- never the
        pairwise ``xi`` that a full Baum-Welch would need for ``A`` -- which is
        why holding ``A`` fixed makes each EM step cheap as well as stable.
        """
        alpha, scales, loglik = self.forward(obs, B)
        beta = self.backward(obs, B, scales)
        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True) + EPS
        return gamma, loglik

    # ------------------------------------------------------------- baum-welch

    def baum_welch(self, obs, B, iterations=100, tol=1e-6, sharpen=1.0,
                   callback=None, should_stop=None):
        """EM over the emission matrix, transitions held fixed.

        M-step:  ``B[i, k] = (expected times in state i emitting k) / (times in i)``
        which for a discrete HMM is just the posterior mass of state ``i`` at
        the positions where symbol ``k`` was observed.

        ``sharpen`` raises the expected counts to a power before renormalising,
        pushing ``B`` towards the hard permutation we know the answer must be.
        It is off by default (1.0) because it breaks the monotonicity guarantee:
        measured over a set of messages it raises the best case and lowers the
        average, trading reliability for the occasional near-perfect solve.
        """
        obs = np.asarray(obs)
        history = []
        previous = -np.inf
        onehot = np.zeros((len(obs), N_SYMBOLS))
        onehot[np.arange(len(obs)), obs] = 1.0

        for step in range(iterations):
            gamma, loglik = self.posteriors(obs, B)

            # expected emission counts: (states x n) @ (n x symbols)
            counts = gamma.T @ onehot
            if sharpen != 1.0:
                counts = counts ** sharpen
            B = self._normalise(counts + EPS)

            history.append(loglik)
            if callback is not None:
                callback(step, loglik, B)
            if should_stop is not None and should_stop():
                break
            if abs(loglik - previous) < tol * max(abs(previous), 1.0):
                break
            previous = loglik

        return B, history

    # ---------------------------------------------------------------- viterbi

    def viterbi(self, obs, B):
        """Most likely state sequence, in log space.

        Log space is the right choice here: Viterbi only ever *adds*, so there
        is no log-sum-exp to pay for, and it cannot underflow.
        """
        n = len(obs)
        log_B = np.log(B + EPS)
        emit = log_B[:, obs]

        delta = self.log_pi + emit[:, 0]
        backpointers = np.empty((n, self.n_states), dtype=np.int64)
        for t in range(1, n):
            scores = delta[:, None] + self.log_A      # (from, to)
            backpointers[t] = np.argmax(scores, axis=0)
            delta = scores[backpointers[t], np.arange(self.n_states)] + emit[:, t]

        path = np.empty(n, dtype=np.int64)
        path[n - 1] = int(np.argmax(delta))
        for t in range(n - 1, 0, -1):
            path[t - 1] = backpointers[t, path[t]]
        return path, float(delta.max())


def key_from_emissions(B):
    """Read the most likely permutation key out of an emission matrix.

    ``B[i, k]`` is ``P(cipher k | plain i)``, so the decryption key wants, for
    each cipher symbol ``k``, the plaintext symbol ``i`` that emits it.  Taking
    a column-wise argmax can produce a non-permutation (two cipher letters
    claiming the same plaintext letter), so cells are claimed greedily in
    descending confidence and each side is used once.  By the time Baum-Welch
    has converged ``B`` is close to a permutation matrix and the greedy pass is
    effectively exact.
    """
    scores = B[:N_LETTERS, :N_LETTERS]
    key = [-1] * N_SYMBOLS
    key[SPACE_IDX] = SPACE_IDX
    order = np.dstack(np.unravel_index(np.argsort(scores, axis=None)[::-1],
                                       scores.shape))[0]
    used_plain, used_cipher = set(), set()
    for plain, cipher in order:
        plain, cipher = int(plain), int(cipher)
        if plain in used_plain or cipher in used_cipher:
            continue
        key[cipher] = plain
        used_plain.add(plain)
        used_cipher.add(cipher)
        if len(used_cipher) == N_LETTERS:
            break
    # Anything still unclaimed (a symbol absent from the ciphertext) gets a
    # leftover letter so the key stays a valid permutation.
    spare = [i for i in range(N_LETTERS) if i not in used_plain]
    for cipher in range(N_LETTERS):
        if key[cipher] == -1:
            key[cipher] = spare.pop()
    return key


class HMMSolver:
    """Cracks a substitution cipher by fitting the emission matrix.

    A note on restarts, from measurement rather than theory: unlike the MCMC
    solver, extra random restarts buy this solver almost nothing.  Baum-Welch
    on a substitution cipher runs downhill into the *same* optimum from
    essentially any starting point, frequency-seeded or random, so eight
    restarts score the same as three.  The default is kept at a modest number
    for that reason, and the honest comparison in the report is that EM
    plateaus where sampling does not -- confusing letters that sit in similar
    bigram contexts (S/J, M/B, D/X) and never escaping.
    """

    solver_name = "hmm"

    def __init__(
        self,
        ciphertext,
        model=None,
        iterations=150,
        restarts=3,
        seed=None,
        seed_with_frequency=True,
        fix_space=True,
        sharpen=1.0,
    ):
        self.model = model or get_model()
        self.text = clean(ciphertext)
        self.obs = to_indices(self.text)
        if len(self.obs) < 2:
            raise ValueError("ciphertext is too short to fit (need 2+ symbols)")

        self.hmm = CipherHMM(model=self.model, fix_space=fix_space)
        self.iterations = int(iterations)
        self.restarts = max(int(restarts), 1)
        self.seed_with_frequency = seed_with_frequency
        self.sharpen = sharpen
        self.rng = np.random.default_rng(seed)
        self.symbol_counts = np.bincount(self.obs, minlength=N_SYMBOLS).astype(float)
        self.n_bigrams = max(len(self.obs) - 1, 1)

    def _initial_emissions(self, restart):
        if restart == 0 and self.seed_with_frequency:
            return self.hmm.emissions_from_key(frequency_seeded_key(self.symbol_counts))
        return self.hmm.random_emissions(self.rng)

    def run(self, callback=None, report_every=1, should_stop=None):
        started = time.perf_counter()
        best = {"loglik": -np.inf, "B": None}
        history, total_steps = [], 0
        stopped = False
        restart = 0

        for restart in range(self.restarts):
            if stopped:
                break

            def on_step(step, loglik, B, restart=restart):
                nonlocal total_steps
                total_steps += 1
                record = {
                    "iteration": total_steps,
                    "restart": restart,
                    "score": float(loglik),
                    "score_per_char": float(loglik / self.n_bigrams),
                    "best_score": float(max(loglik, best["loglik"])),
                    "best_score_per_char": float(
                        max(loglik, best["loglik"]) / self.n_bigrams
                    ),
                }
                history.append(record)
                if callback is not None and report_every and total_steps % report_every == 0:
                    key = key_from_emissions(B)
                    payload = dict(record)
                    payload["key"] = array_to_key(key[:N_LETTERS])
                    payload["text"] = to_text([key[int(o)] for o in self.obs])
                    callback(payload)

            B, _ = self.hmm.baum_welch(
                self.obs,
                self._initial_emissions(restart),
                iterations=self.iterations,
                sharpen=self.sharpen,
                callback=on_step,
                should_stop=should_stop,
            )
            _, _, loglik = self.hmm.forward(self.obs, B)
            if loglik > best["loglik"]:
                best = {"loglik": loglik, "B": B}
            if should_stop is not None and should_stop():
                stopped = True

        B = best["B"]
        path, viterbi_logprob = self.hmm.viterbi(self.obs, B)
        key = key_from_emissions(B)

        # Viterbi is free to emit a sequence no single key could produce, so we
        # report both: the decoded path (what the model believes) and the text
        # implied by the permutation key (what the UI can colour in).
        viterbi_text = to_text(path)
        key_text = to_text([key[int(o)] for o in self.obs])

        elapsed = time.perf_counter() - started
        return CrackResult(
            key=array_to_key(key[:N_LETTERS]),
            plaintext=key_text,
            score=float(best["loglik"]),
            score_per_char=float(best["loglik"] / self.n_bigrams),
            iterations=total_steps,
            elapsed=elapsed,
            restarts=restart + 1,
            accepted=total_steps,
            proposal="baum_welch",
            history=history,
            stopped_early=stopped,
            solver=self.solver_name,
            extra={
                "viterbi_text": viterbi_text,
                "viterbi_logprob": viterbi_logprob,
                "emission_sharpness": float(B[:N_LETTERS, :N_LETTERS].max(axis=0).mean()),
            },
        )


def crack(ciphertext, **kwargs):
    callback = kwargs.pop("callback", None)
    report_every = kwargs.pop("report_every", 1)
    should_stop = kwargs.pop("should_stop", None)
    solver = HMMSolver(ciphertext, **kwargs)
    return solver.run(callback=callback, report_every=report_every, should_stop=should_stop)
