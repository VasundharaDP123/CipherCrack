"""Hill climbing: MCMC with the interesting part removed.

Two flavours, both greedy:

* **stochastic** -- propose a random swap, take it only if it improves the
  score.  This is literally :class:`ml.mcmc.MCMCSolver` with the
  accept-a-worse-key branch switched off, which makes it the cleanest possible
  control for the report: same proposals, same scoring, same restarts, one
  behavioural difference.
* **steepest ascent** -- try all 325 swaps and take the single best one, until
  no swap improves anything.  Slower per step but converges in very few steps,
  and it is the classical textbook version.

Both get stuck.  That is the point of having them: the gap between these and
the MCMC solver is the experimental evidence that accepting worse keys is what
does the work, not the scoring function or the proposals.
"""

import time

from ciphers.alphabet import N_LETTERS
from ciphers.substitution import array_to_key
from ml.mcmc import CrackResult, MCMCSolver, random_key


def crack(ciphertext, iterations=10_000, restarts=5, seed=None, model=None,
          proposal="random_swap", callback=None, report_every=100,
          should_stop=None, **_):
    """Stochastic hill climbing, sharing every part of the MCMC machinery."""
    solver = MCMCSolver(
        ciphertext,
        model=model,
        proposal=proposal,
        iterations=iterations,
        restarts=restarts,
        seed=seed,
        hill_climb=True,
    )
    return solver.run(callback=callback, report_every=report_every,
                      should_stop=should_stop)


def steepest_ascent(ciphertext, restarts=5, max_passes=200, seed=None, model=None,
                    callback=None, report_every=1, should_stop=None, **_):
    """Repeatedly apply the single best available swap until none helps."""
    started = time.perf_counter()
    solver = MCMCSolver(ciphertext, model=model, seed=seed)
    scorer, stream = solver.scorer, solver.stream

    pairs = [(i, j) for i in range(N_LETTERS) for j in range(i + 1, N_LETTERS)]
    best_key, best_score = None, float("-inf")
    steps, history = 0, []
    stopped = False

    for restart in range(restarts):
        if stopped:
            break
        key = random_key(stream)
        current = scorer.score_list(key)

        for _ in range(max_passes):
            top_gain, top_pair = 0.0, None
            for i, j in pairs:
                candidate = key[:]
                candidate[i], candidate[j] = key[j], key[i]
                gain = scorer.delta(key, candidate, (i, j))
                if gain > top_gain:
                    top_gain, top_pair = gain, (i, j)

            steps += 1
            if top_pair is None:
                break                        # a local optimum: nothing helps
            i, j = top_pair
            key[i], key[j] = key[j], key[i]
            current += top_gain

            record = {
                "iteration": steps,
                "restart": restart,
                "score": current,
                "best_score": max(current, best_score),
                "score_per_char": scorer.per_char(current),
                "best_score_per_char": scorer.per_char(max(current, best_score)),
            }
            history.append(record)
            if callback is not None and report_every and steps % report_every == 0:
                payload = dict(record)
                payload["key"] = array_to_key(key[:N_LETTERS])
                payload["text"] = solver.decode(key)
                callback(payload)
            if should_stop is not None and should_stop():
                stopped = True
                break

        if current > best_score:
            best_key, best_score = key[:], current

    return CrackResult(
        key=array_to_key(best_key[:N_LETTERS]),
        plaintext=solver.decode(best_key),
        score=best_score,
        score_per_char=scorer.per_char(best_score),
        iterations=steps,
        elapsed=time.perf_counter() - started,
        restarts=restarts,
        accepted=steps,
        proposal="steepest_ascent",
        history=history,
        stopped_early=stopped,
        solver="steepest_ascent",
    )
