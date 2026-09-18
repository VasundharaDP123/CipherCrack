"""Exercise the HMM solver and check the from-scratch algorithms are right.

    python -m scripts.bench_hmm

Three correctness checks before the timing, because an HMM that silently
computes the wrong likelihood still "works":

1. the scaled forward likelihood matches a plain log-space forward pass
2. Baum-Welch never decreases the log-likelihood (the EM guarantee)
3. Viterbi's own score matches rescoring its returned path by hand
"""

import argparse
import random
import textwrap

import numpy as np

from ciphers import substitution as sub
from ciphers.alphabet import clean, to_indices
from ml.hmm import CipherHMM, HMMSolver, key_from_emissions
from ml.language_model import get_model
from ml.mcmc import letter_accuracy
from scripts.bench_mcmc import SAMPLE


def log_space_forward(hmm, obs, B):
    """Deliberately slow reference implementation, used only to check scaling."""
    log_B = np.log(B + 1e-12)
    log_alpha = hmm.log_pi + log_B[:, obs[0]]
    for t in range(1, len(obs)):
        stacked = log_alpha[:, None] + hmm.log_A
        peak = stacked.max(axis=0)
        log_alpha = peak + np.log(np.exp(stacked - peak).sum(axis=0)) + log_B[:, obs[t]]
    peak = log_alpha.max()
    return float(peak + np.log(np.exp(log_alpha - peak).sum()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=int, default=400)
    parser.add_argument("--iterations", type=int, default=120)
    parser.add_argument("--restarts", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    model = get_model()
    plaintext = clean(SAMPLE)[: args.length]
    true_key = sub.random_key(random.Random(args.seed))
    ciphertext = sub.encrypt(plaintext, true_key)
    obs = to_indices(ciphertext)

    hmm = CipherHMM(model=model)
    rng = np.random.default_rng(args.seed)
    B = hmm.random_emissions(rng)

    scaled = hmm.forward(obs[:200], B)[2]
    reference = log_space_forward(hmm, obs[:200], B)
    print(f"forward: scaled={scaled:.6f}  log-space reference={reference:.6f}  "
          f"diff={abs(scaled - reference):.2e}")

    _, history = hmm.baum_welch(obs, B, iterations=30)
    drops = [i for i in range(1, len(history)) if history[i] < history[i - 1] - 1e-6]
    print(f"baum-welch: {len(history)} steps, log-lik {history[0]:.1f} -> {history[-1]:.1f}, "
          f"monotone={'yes' if not drops else f'NO (drops at {drops})'}")

    path, score = hmm.viterbi(obs[:200], B)
    manual = float(hmm.log_pi[path[0]] + np.log(B[path[0], obs[0]] + 1e-12))
    for t in range(1, 200):
        manual += float(hmm.log_A[path[t - 1], path[t]] + np.log(B[path[t], obs[t]] + 1e-12))
    print(f"viterbi: reported={score:.6f}  recomputed={manual:.6f}  "
          f"diff={abs(score - manual):.2e}\n")

    solver = HMMSolver(
        ciphertext, model=model, iterations=args.iterations,
        restarts=args.restarts, seed=args.seed,
    )
    result = solver.run(report_every=0)
    key_accuracy = sub.key_accuracy(result.key, sub.invert_key(true_key))
    print(f"HMM solve: {result.elapsed:.2f}s  {result.iterations} EM steps  "
          f"log-lik={result.score:.1f}")
    print(f"  key accuracy      : {key_accuracy:.1%}")
    print(f"  letter accuracy   : {letter_accuracy(result.plaintext, plaintext):.1%} (via key)")
    print(f"  letter accuracy   : {letter_accuracy(result.extra['viterbi_text'], plaintext):.1%} (via Viterbi)")
    print(f"  emission sharpness: {result.extra['emission_sharpness']:.3f}")
    print("\ndecoded (via key):")
    print(textwrap.fill(result.plaintext[:280], 78, initial_indent="  ", subsequent_indent="  "))
    print("\ndecoded (via Viterbi):")
    print(textwrap.fill(result.extra["viterbi_text"][:280], 78, initial_indent="  ",
                        subsequent_indent="  "))


if __name__ == "__main__":
    main()
