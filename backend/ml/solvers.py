"""One dispatch table over every attack, so the API and the Arena agree.

Each entry exposes the same call signature -- ``fn(ciphertext, **options)``
returning a :class:`ml.mcmc.CrackResult` -- and declares which options it
actually understands, so the API can drop anything irrelevant instead of
raising on it.
"""

from baselines import frequency, hill_climbing
from ml import hmm, mcmc
from ml.language_model import get_model

SOLVERS = {
    "mcmc": {
        "label": "MCMC (Metropolis-Hastings)",
        "fn": mcmc.crack,
        "streams": True,
        "options": {
            "iterations", "restarts", "proposal", "temperature", "anneal_to",
            "seed", "seed_with_frequency",
        },
        "defaults": {"iterations": 10_000, "restarts": 10, "proposal": "random_swap"},
        "blurb": "Samples keys, accepting worse ones often enough to escape local optima.",
    },
    "hmm": {
        "label": "HMM (Baum-Welch + Viterbi)",
        "fn": hmm.crack,
        "streams": True,
        "options": {"iterations", "restarts", "seed", "seed_with_frequency",
                    "fix_space", "sharpen"},
        "defaults": {"iterations": 150, "restarts": 3},
        "blurb": "Learns the key as an emission matrix, then decodes with Viterbi.",
    },
    "hill_climbing": {
        "label": "Hill climbing",
        "fn": hill_climbing.crack,
        "streams": True,
        "options": {"iterations", "restarts", "proposal", "seed"},
        "defaults": {"iterations": 10_000, "restarts": 10},
        "blurb": "Same search as MCMC, but never accepts a worse key.",
    },
    "steepest_ascent": {
        "label": "Steepest-ascent hill climbing",
        "fn": hill_climbing.steepest_ascent,
        "streams": True,
        "options": {"restarts", "max_passes", "seed"},
        "defaults": {"restarts": 5},
        "blurb": "Tries all 325 swaps each step and takes the best one.",
    },
    "frequency": {
        "label": "Frequency analysis",
        "fn": frequency.crack,
        "streams": False,
        "options": set(),
        "defaults": {},
        "blurb": "The classical attack: match letter frequency ranks, no search.",
    },
}

SOLVER_NAMES = list(SOLVERS)


def get(name):
    try:
        return SOLVERS[name]
    except KeyError:
        raise ValueError(f"unknown solver {name!r}; expected one of {SOLVER_NAMES}")


def run(name, ciphertext, options=None, **runtime):
    """Run a solver by name, passing only the options it understands.

    ``runtime`` carries ``callback`` / ``report_every`` / ``should_stop``, which
    every solver accepts.
    """
    spec = get(name)
    merged = dict(spec["defaults"])
    merged.update(options or {})
    accepted = {k: v for k, v in merged.items() if k in spec["options"] and v is not None}
    result = spec["fn"](ciphertext, **accepted, **runtime)
    result.extra["plaintext_score_per_char"] = plaintext_score(result.plaintext)
    return result


def plaintext_score(text):
    """Bigram log-probability per character of a solver's output.

    Every solver reports a ``score``, but they are not the same quantity: the
    MCMC chain reports its bigram key score while the HMM reports an HMM
    log-likelihood, which marginalises over all state paths and is routinely
    *higher* for a worse answer.  Comparing those two numbers directly would be
    meaningless, so the Arena ranks solvers by re-scoring the plaintext each
    one actually produced, under the one shared language model.
    """
    return get_model().score_per_char(text)


def catalogue():
    """Serialisable description of every solver, for the UI to render."""
    return [
        {
            "name": name,
            "label": spec["label"],
            "blurb": spec["blurb"],
            "streams": spec["streams"],
            "options": sorted(spec["options"]),
            "defaults": spec["defaults"],
        }
        for name, spec in SOLVERS.items()
    ]
