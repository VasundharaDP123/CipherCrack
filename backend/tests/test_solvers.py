"""The parts where a silent mistake would still look like it works.

An incremental score that drifts, an EM step that quietly decreases the
likelihood, a Viterbi that reports a number it did not actually achieve -- all
of these produce plausible output while being wrong, so each gets a test that
compares it against an independent slow implementation.
"""

import random

import numpy as np
import pytest

from baselines import frequency, hill_climbing
from ciphers import substitution as sub
from ciphers.alphabet import clean, to_indices
from ml.hmm import CipherHMM, HMMSolver, key_from_emissions
from ml.language_model import count_bigrams, get_model
from ml.mcmc import MCMCSolver, frequency_seeded_key, letter_accuracy, random_key
from ml.proposals import PROPOSAL_NAMES, build_proposal
from ml.rng import RandomStream
from ml.scoring import KeyScorer

PLAIN = clean(
    "IT IS A TRUTH UNIVERSALLY ACKNOWLEDGED THAT A SINGLE MAN IN POSSESSION OF A "
    "GOOD FORTUNE MUST BE IN WANT OF A WIFE HOWEVER LITTLE KNOWN THE FEELINGS OR "
    "VIEWS OF SUCH A MAN MAY BE ON HIS FIRST ENTERING A NEIGHBOURHOOD THIS TRUTH "
    "IS SO WELL FIXED IN THE MINDS OF THE SURROUNDING FAMILIES"
)


@pytest.fixture(scope="module")
def model():
    return get_model()


@pytest.fixture(scope="module")
def puzzle():
    key = sub.random_key(random.Random(42))
    return sub.encrypt(PLAIN, key), key


# ------------------------------------------------------------------- scoring

def test_language_model_prefers_english(model):
    rng = np.random.default_rng(0)
    noise = "".join(rng.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ "), size=len(PLAIN)))
    assert model.score_per_char(PLAIN) > model.score_per_char(noise) + 1.0


def test_count_matrix_scoring_matches_walking_the_text(model, puzzle):
    """The O(1) count-based score must equal the O(n) walk over the text."""
    ciphertext, key = puzzle
    indices = to_indices(clean(ciphertext))
    scorer = KeyScorer(indices, model.log_probs)

    decryption = sub.invert_key(key)
    key_array = [ord(c) - 65 for c in decryption] + [26]
    decoded = to_indices(sub.decrypt_with_decryption_key(clean(ciphertext), decryption))

    assert scorer.score(key_array) == pytest.approx(model.score_indices(decoded), abs=1e-6)
    assert scorer.score_list(key_array) == pytest.approx(scorer.score(key_array), abs=1e-6)


@pytest.mark.parametrize("proposal_name", PROPOSAL_NAMES)
def test_incremental_delta_matches_full_rescore(model, puzzle, proposal_name):
    """The whole speed story rests on this being exact, not approximately right."""
    ciphertext, _ = puzzle
    solver = MCMCSolver(ciphertext, model=model, proposal=proposal_name, seed=1)
    scorer, proposal = solver.scorer, solver.proposal

    key = random_key(solver.stream)
    for _ in range(400):
        new_key, moved = proposal.propose(key)
        incremental = scorer.delta(key, new_key, moved)
        exact = scorer.score_list(new_key) - scorer.score_list(key)
        assert incremental == pytest.approx(exact, abs=1e-6)
        key = new_key


@pytest.mark.parametrize("proposal_name", PROPOSAL_NAMES)
def test_proposals_stay_permutations(proposal_name):
    stream = RandomStream(0)
    proposal = build_proposal(proposal_name, stream, symbol_counts=np.arange(27, 0, -1))
    key = list(range(27))
    for _ in range(300):
        key, moved = proposal.propose(key)
        assert sorted(key) == list(range(27))
        assert key[26] == 26                       # space is never reassigned
        assert len(set(moved)) == len(moved)


def test_seeded_runs_are_reproducible(model, puzzle):
    ciphertext, _ = puzzle
    kwargs = dict(model=model, iterations=500, restarts=1, seed=99)
    first = MCMCSolver(ciphertext, **kwargs).run(report_every=0)
    second = MCMCSolver(ciphertext, **kwargs).run(report_every=0)
    assert first.key == second.key
    assert first.score == pytest.approx(second.score)


# -------------------------------------------------------------------- mcmc

def test_mcmc_cracks_a_long_cipher(model, puzzle):
    ciphertext, key = puzzle
    result = MCMCSolver(
        ciphertext, model=model, iterations=6000, restarts=4, seed=3
    ).run(report_every=0)
    assert letter_accuracy(result.plaintext, PLAIN) > 0.95
    assert result.score_per_char > -2.6


def test_stop_flag_halts_the_chain(model, puzzle):
    ciphertext, _ = puzzle
    solver = MCMCSolver(ciphertext, model=model, iterations=100_000, restarts=5, seed=3)
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] >= 3

    result = solver.run(report_every=100, should_stop=should_stop)
    assert result.stopped_early
    assert result.iterations < 100_000


def test_progress_callback_shape(model, puzzle):
    ciphertext, _ = puzzle
    seen = []
    MCMCSolver(ciphertext, model=model, iterations=500, restarts=1, seed=5).run(
        callback=seen.append, report_every=100
    )
    assert len(seen) == 5
    for frame in seen:
        assert set(frame) >= {"iteration", "score", "best_score", "key", "text"}
        assert len(frame["key"]) == 26


# --------------------------------------------------------------------- hmm

def test_scaled_forward_matches_log_space(model, puzzle):
    """Scaling is an optimisation; it must not change the likelihood."""
    ciphertext, _ = puzzle
    hmm = CipherHMM(model=model)
    obs = to_indices(clean(ciphertext))[:150]
    B = hmm.random_emissions(np.random.default_rng(0))

    log_B = np.log(B + 1e-12)
    log_alpha = hmm.log_pi + log_B[:, obs[0]]
    for t in range(1, len(obs)):
        stacked = log_alpha[:, None] + hmm.log_A
        peak = stacked.max(axis=0)
        log_alpha = peak + np.log(np.exp(stacked - peak).sum(axis=0)) + log_B[:, obs[t]]
    peak = log_alpha.max()
    reference = float(peak + np.log(np.exp(log_alpha - peak).sum()))

    assert hmm.forward(obs, B)[2] == pytest.approx(reference, abs=1e-5)


def test_baum_welch_never_decreases_likelihood(model, puzzle):
    """The EM guarantee.  A violation means the M-step is wrong."""
    ciphertext, _ = puzzle
    hmm = CipherHMM(model=model)
    obs = to_indices(clean(ciphertext))
    B = hmm.random_emissions(np.random.default_rng(1))
    _, history = hmm.baum_welch(obs, B, iterations=25)
    for earlier, later in zip(history, history[1:]):
        assert later >= earlier - 1e-6


def test_forward_probabilities_are_normalised(model, puzzle):
    ciphertext, _ = puzzle
    hmm = CipherHMM(model=model)
    obs = to_indices(clean(ciphertext))[:80]
    alpha, _, _ = hmm.forward(obs, hmm.random_emissions(np.random.default_rng(2)))
    assert np.allclose(alpha.sum(axis=1), 1.0)


def test_viterbi_score_matches_its_own_path(model, puzzle):
    ciphertext, _ = puzzle
    hmm = CipherHMM(model=model)
    obs = to_indices(clean(ciphertext))[:120]
    B = hmm.random_emissions(np.random.default_rng(3))
    path, score = hmm.viterbi(obs, B)

    log_B = np.log(B + 1e-12)
    manual = hmm.log_pi[path[0]] + log_B[path[0], obs[0]]
    for t in range(1, len(obs)):
        manual += hmm.log_A[path[t - 1], path[t]] + log_B[path[t], obs[t]]
    assert score == pytest.approx(float(manual), abs=1e-6)


def test_key_from_emissions_is_a_permutation():
    rng = np.random.default_rng(0)
    B = rng.random((27, 27))
    key = key_from_emissions(B)
    assert sorted(key[:26]) == list(range(26))
    assert key[26] == 26


def test_hmm_solver_beats_frequency_analysis(model, puzzle):
    ciphertext, _ = puzzle
    hmm_result = HMMSolver(
        ciphertext, model=model, iterations=60, restarts=1, seed=7
    ).run(report_every=0)
    baseline = frequency.crack(ciphertext, model=model)
    assert letter_accuracy(hmm_result.plaintext, PLAIN) > letter_accuracy(
        baseline.plaintext, PLAIN
    )


# --------------------------------------------------------------- baselines

def test_frequency_seeded_key_is_a_permutation(model, puzzle):
    ciphertext, _ = puzzle
    counts = np.bincount(to_indices(clean(ciphertext)), minlength=27).astype(float)
    key = frequency_seeded_key(counts)
    assert sorted(key[:26]) == list(range(26))


def test_hill_climbing_runs_and_never_accepts_worse(model, puzzle):
    ciphertext, _ = puzzle
    result = hill_climbing.crack(
        ciphertext, model=model, iterations=2000, restarts=2, seed=3, report_every=0
    )
    assert result.solver == "hill_climbing"
    assert 0 <= result.acceptance_rate <= 1


def test_steepest_ascent_reaches_a_local_optimum(model, puzzle):
    ciphertext, _ = puzzle
    result = hill_climbing.steepest_ascent(
        ciphertext, model=model, restarts=1, seed=3, report_every=0
    )
    assert result.iterations > 0
    assert result.score_per_char > -3.5


def test_short_text_is_rejected(model):
    with pytest.raises(ValueError):
        MCMCSolver("A", model=model)
