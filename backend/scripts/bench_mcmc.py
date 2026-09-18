"""Crack a cipher from the terminal and time the scoring paths.

    python -m scripts.bench_mcmc
    python -m scripts.bench_mcmc --all-proposals --length 400

This is the Week 2 milestone check -- a long cipher cracked from the command
line -- plus the iterations/second figures quoted in the report.
"""

import argparse
import random
import textwrap
import time

from ciphers import substitution as sub
from ciphers.alphabet import clean
from ml.language_model import get_model
from ml.mcmc import MCMCSolver, letter_accuracy, random_key
from ml.proposals import PROPOSAL_NAMES

SAMPLE = """
It is a truth universally acknowledged, that a single man in possession of a
good fortune, must be in want of a wife. However little known the feelings or
views of such a man may be on his first entering a neighbourhood, this truth is
so well fixed in the minds of the surrounding families, that he is considered
the rightful property of some one or other of their daughters. My dear Mr
Bennet, said his lady to him one day, have you heard that Netherfield Park is
let at last? Mr Bennet replied that he had not. But it is, returned she, for
Mrs Long has just been here, and she told me all about it. Mr Bennet made no
answer. Do not you want to know who has taken it, cried his wife impatiently.
"""


def check_delta_exactness(solver, trials=2000):
    """The incremental delta must equal the difference of two full scores."""
    key = random_key(solver.stream)
    worst = 0.0
    for _ in range(trials):
        new_key, moved = solver.proposal.propose(key)
        incremental = solver.scorer.delta(key, new_key, moved)
        exact = solver.scorer.score_list(new_key) - solver.scorer.score_list(key)
        worst = max(worst, abs(incremental - exact))
        key = new_key
    return worst


def bench_scoring(solver, trials=30000):
    """Iterations per second for each way of evaluating a proposal."""
    key = random_key(solver.stream)
    scorer, proposal = solver.scorer, solver.proposal
    results = {}

    def timed(label, fn, n):
        for _ in range(500):
            fn()
        start = time.perf_counter()
        for _ in range(n):
            fn()
        results[label] = n / (time.perf_counter() - start)

    def propose_only():
        proposal.propose(key)

    def incremental():
        new_key, moved = proposal.propose(key)
        scorer.delta(key, new_key, moved)

    def full_numpy():
        new_key, _ = proposal.propose(key)
        scorer.score(new_key)

    def full_python():
        new_key, _ = proposal.propose(key)
        scorer.score_list(new_key)

    timed("propose only", propose_only, trials)
    timed("propose + incremental delta", incremental, trials)
    timed("propose + full rescore (python)", full_python, max(trials // 5, 2000))
    timed("propose + full rescore (numpy)", full_numpy, max(trials // 10, 1000))
    return results


def bench_proposals(ciphertext, model, seed, trials=20000):
    """Per-proposal cost of one complete chain step."""
    rows = {}
    for name in PROPOSAL_NAMES:
        solver = MCMCSolver(ciphertext, model=model, proposal=name, seed=seed)
        scorer, proposal = solver.scorer, solver.proposal
        key = random_key(solver.stream)

        def step():
            new_key, moved = proposal.propose(key)
            scorer.delta(key, new_key, moved)
            proposal.update(moved, 1.0, True)

        for _ in range(500):
            step()
        start = time.perf_counter()
        for _ in range(trials):
            step()
        rows[name] = trials / (time.perf_counter() - start)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=int, default=400)
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--restarts", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--proposal", default="random_swap", choices=PROPOSAL_NAMES)
    parser.add_argument("--all-proposals", action="store_true")
    args = parser.parse_args()

    model = get_model()
    plaintext = clean(SAMPLE)[: args.length]
    true_key = sub.random_key(random.Random(args.seed))
    ciphertext = sub.encrypt(plaintext, true_key)

    print(f"plaintext  ({len(plaintext)} chars): {plaintext[:68]}...")
    print(f"true key   : {true_key}")
    print(f"ciphertext : {ciphertext[:68]}...\n")

    probe = MCMCSolver(ciphertext, model=model, seed=args.seed)
    print(f"delta exactness (max |incremental - exact|): {check_delta_exactness(probe):.3e}\n")

    names = PROPOSAL_NAMES if args.all_proposals else [args.proposal]
    last = None
    for name in names:
        solver = MCMCSolver(
            ciphertext,
            model=model,
            proposal=name,
            iterations=args.iterations,
            restarts=args.restarts,
            seed=args.seed,
        )
        result = solver.run(report_every=0)
        last = result
        print(
            f"{name:12s} acc={letter_accuracy(result.plaintext, plaintext):6.1%}  "
            f"score/char={result.score_per_char:+.3f}  "
            f"iters={result.iterations:>7,}  {result.elapsed:6.2f}s  "
            f"{result.rate:>8,.0f} it/s  accept={result.acceptance_rate:5.1%}"
        )

    print("\ndecoded:")
    print(textwrap.fill(last.plaintext[:360], 78, initial_indent="  ", subsequent_indent="  "))

    print("\nscoring throughput (random_swap proposal):")
    for label, rate in bench_scoring(probe).items():
        print(f"  {label:32s} {rate:>10,.0f} it/s")

    print("\ncost of one chain step, by proposal:")
    for name, rate in bench_proposals(ciphertext, model, args.seed).items():
        print(f"  {name:32s} {rate:>10,.0f} it/s")


if __name__ == "__main__":
    main()
