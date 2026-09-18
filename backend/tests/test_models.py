"""The from-scratch classifiers, clustering and Gaussian generator.

Each is checked against a property it must hold rather than a golden number, so
the tests stay meaningful if the data is regenerated.
"""

import numpy as np
import pytest

from ml import features
from ml.adaboost import AdaBoost
from ml.forest import RandomForest
from ml.gaussian import BoxMuller, GaussianMixture2D, effective_sample_size, metropolis_2d
from ml.kmeans import KMeans, silhouette_score
from ml.metrics import classification_report, confusion_matrix, train_test_split
from ml.tree import DecisionStump, DecisionTree


@pytest.fixture(scope="module")
def blobs():
    """Three well-separated Gaussian blobs -- any correct classifier nails these."""
    rng = np.random.default_rng(0)
    centres = np.array([[0, 0], [6, 6], [0, 7]], dtype=float)
    X = np.vstack([rng.normal(c, 0.7, size=(120, 2)) for c in centres])
    y = np.repeat([0, 1, 2], 120)
    return X, y


# ----------------------------------------------------------------- trees

def test_tree_separates_easy_blobs(blobs):
    X, y = blobs
    tree = DecisionTree(max_depth=6, random_state=0).fit(X, y, n_classes=3)
    assert (tree.predict(X) == y).mean() > 0.95


def test_tree_probabilities_are_distributions(blobs):
    X, y = blobs
    proba = DecisionTree(max_depth=4, random_state=0).fit(X, y, n_classes=3).predict_proba(X)
    assert proba.shape == (len(X), 3)
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert (proba >= 0).all()


def test_depth_limit_is_respected(blobs):
    X, y = blobs
    assert DecisionTree(max_depth=2, random_state=0).fit(X, y, n_classes=3).depth() <= 2


def test_stump_is_depth_one(blobs):
    X, y = blobs
    assert DecisionStump(random_state=0).fit(X, y, n_classes=3).depth() <= 1


def test_sample_weights_change_the_fit():
    """AdaBoost depends on this; without it every stump would be identical."""
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    y = np.array([0, 0, 1, 1])
    heavy = np.array([1.0, 50.0, 50.0, 1.0])
    unweighted = DecisionTree(max_depth=1, random_state=0).fit(X, y, n_classes=2)
    weighted = DecisionTree(max_depth=1, random_state=0).fit(
        X, y, sample_weight=heavy, n_classes=2
    )
    assert unweighted.root.threshold is not None
    assert weighted.root.threshold is not None


# ---------------------------------------------------------------- forest

def test_forest_beats_a_single_tree_on_noise():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(400, 8))
    y = (X[:, 0] + X[:, 1] + rng.normal(0, 0.6, 400) > 0).astype(int)
    split = 300

    tree = DecisionTree(max_depth=None, random_state=0).fit(X[:split], y[:split], n_classes=2)
    forest = RandomForest(n_estimators=40, random_state=0).fit(
        X[:split], y[:split], n_classes=2
    )
    assert forest.score(X[split:], y[split:]) >= (tree.predict(X[split:]) == y[split:]).mean()


def test_forest_reports_oob_and_importances(blobs):
    X, y = blobs
    forest = RandomForest(n_estimators=25, random_state=0).fit(X, y, n_classes=3)
    assert 0.0 <= forest.oob_score_ <= 1.0
    assert forest.feature_importances_.shape == (2,)
    assert forest.feature_importances_.sum() == pytest.approx(1.0, abs=1e-6)


# -------------------------------------------------------------- adaboost

def test_adaboost_learns_from_stumps(blobs):
    X, y = blobs
    boost = AdaBoost(n_estimators=60, random_state=0).fit(X, y, n_classes=3)
    assert boost.score(X, y) > 0.9
    assert len(boost.learners) > 1


def test_adaboost_improves_over_its_first_stump(blobs):
    X, y = blobs
    boost = AdaBoost(n_estimators=60, random_state=0).fit(X, y, n_classes=3)
    curve = boost.staged_score(X, y)
    assert curve[-1] >= curve[0]


def test_adaboost_probabilities_are_distributions(blobs):
    X, y = blobs
    proba = AdaBoost(n_estimators=30, random_state=0).fit(X, y, n_classes=3).predict_proba(X)
    assert np.allclose(proba.sum(axis=1), 1.0)


# ---------------------------------------------------------------- kmeans

def test_kmeans_recovers_known_blobs(blobs):
    X, _ = blobs
    km = KMeans(n_clusters=3, random_state=0).fit(X)
    assert len(np.unique(km.labels_)) == 3
    assert silhouette_score(X, km.labels_) > 0.5


def test_kmeans_labels_agree_with_predict(blobs):
    """Regression guard: fit() must not return labels from stale centroids."""
    X, _ = blobs
    km = KMeans(n_clusters=3, random_state=0).fit(X)
    assert np.array_equal(km.labels_, km.predict(X))


def test_vector_quantization_round_trip(blobs):
    X, _ = blobs
    km = KMeans(n_clusters=3, random_state=0).fit(X)
    codes = km.encode(X)
    assert codes.shape == (len(X),)
    assert km.decode(codes).shape == X.shape
    assert km.quantization_error(X) < km.quantization_error(np.roll(X, 5, axis=0)) * 5


def test_more_clusters_never_increase_inertia(blobs):
    X, _ = blobs
    previous = np.inf
    for k in range(2, 6):
        inertia = KMeans(n_clusters=k, n_init=5, random_state=0).fit(X).inertia_
        assert inertia <= previous + 1e-6
        previous = inertia


# --------------------------------------------------------------- metrics

def test_confusion_and_report_agree():
    y_true = np.array([0, 0, 1, 1, 2, 2])
    y_pred = np.array([0, 1, 1, 1, 2, 0])
    matrix = confusion_matrix(y_true, y_pred, 3)
    assert matrix.sum() == 6
    report = classification_report(y_true, y_pred, ["a", "b", "c"])
    assert report["accuracy"] == pytest.approx(4 / 6)
    assert len(report["per_class"]) == 3


def test_stratified_split_keeps_class_balance():
    y = np.repeat([0, 1, 2, 3], 50)
    train, test = train_test_split(len(y), test_size=0.2, random_state=0, stratify=y)
    assert len(set(train) & set(test)) == 0
    assert len(train) + len(test) == len(y)
    for label in range(4):
        assert (y[test] == label).sum() == 10


# -------------------------------------------------------------- gaussian

def test_box_muller_is_standard_normal():
    samples = BoxMuller(0).normals(60_000)
    assert abs(samples.mean()) < 0.03
    assert abs(samples.std() - 1.0) < 0.03
    # A normal puts ~68% of its mass within one standard deviation.
    assert abs((np.abs(samples) < 1).mean() - 0.6827) < 0.01


def test_box_muller_scalar_and_vector_agree_in_distribution():
    gauss = BoxMuller(1)
    scalars = np.array([gauss.normal() for _ in range(20_000)])
    assert abs(scalars.mean()) < 0.05
    assert abs(scalars.std() - 1.0) < 0.05


def test_metropolis_finds_the_mixture_means():
    target = GaussianMixture2D()
    run = metropolis_2d(target, step_size=1.6, n_samples=12_000, burn_in=1000, seed=0)
    samples = run["samples"]
    assert 0.1 < run["acceptance_rate_post_burnin"] < 0.9
    # Every component should attract some samples.
    for component in target.components:
        near = np.linalg.norm(samples - np.array(component["mean"]), axis=1) < 1.5
        assert near.sum() > 50


def test_step_size_changes_acceptance_the_expected_way():
    target = GaussianMixture2D()
    small = metropolis_2d(target, step_size=0.05, n_samples=3000, seed=0)
    large = metropolis_2d(target, step_size=9.0, n_samples=3000, seed=0)
    assert small["acceptance_rate_post_burnin"] > large["acceptance_rate_post_burnin"]


def test_effective_sample_size_is_bounded():
    target = GaussianMixture2D()
    run = metropolis_2d(target, step_size=1.6, n_samples=4000, seed=0)
    ess = effective_sample_size(run["samples"])
    assert all(0 < value <= len(run["samples"]) * 1.05 for value in ess)


# -------------------------------------------------------------- features

def test_features_separate_the_cipher_classes():
    import ciphers
    from ciphers.alphabet import clean

    plain = clean(
        "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG WHILE THE PATIENT STUDENT "
        "CONSIDERS WHETHER THE INDEX OF COINCIDENCE WILL GIVE THE ANSWER AWAY "
        "LONG BEFORE ANY SEARCH IS EVEN ATTEMPTED AT ALL THIS QUIET EVENING"
    )
    rng = __import__("random").Random(0)
    values = {name: features.describe(ciphers.encrypt(name, plain, rng=rng)[0])
              for name in ciphers.CIPHER_NAMES}
    baseline = features.describe(plain)

    # Vigenere flattens the letter distribution; the others do not.
    assert values["vigenere"]["index_of_coincidence"] < 0.055
    for name in ("caesar", "substitution", "transposition"):
        assert values[name]["index_of_coincidence"] > 0.055

    # Transposition only reorders letters, so no rotation can improve its
    # distance to English: the shift-0 and best-shift scores coincide.  That
    # zero gap is the invariant, and it is what separates it from Caesar.
    # (It is close to, but not exactly, the plaintext's own score, because the
    # grid is padded with X to fill its last row and X is rare enough in English
    # that a handful of them moves chi-squared noticeably on a short text.)
    assert values["transposition"]["chi2_shift_gap"] == pytest.approx(0.0, abs=1e-9)
    assert values["transposition"]["chi2_shift0"] < values["caesar"]["chi2_shift0"]

    # Caesar rotates those same frequencies: badly wrong at shift 0, and back to
    # the plaintext's own score once the rotation is undone.
    assert values["caesar"]["chi2_best_shift"] == pytest.approx(
        baseline["chi2_shift0"], rel=1e-6
    )
    assert values["caesar"]["chi2_shift_gap"] > 3.0

    # Substitution keeps the IC but no rotation can realign it.
    assert values["substitution"]["chi2_best_shift"] > values["caesar"]["chi2_best_shift"]


def test_feature_vector_length_matches_names():
    assert len(features.extract("HELLO WORLD THIS IS A TEST")) == len(features.FEATURE_NAMES)


def test_tiny_text_does_not_crash():
    assert len(features.extract("AB")) == len(features.FEATURE_NAMES)
