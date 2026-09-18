"""The cipher-type identifier: features in, class probabilities out.

Wraps the three from-scratch models around one shared feature extractor:

* :class:`ml.forest.RandomForest`  -- the classifier the app actually uses
* :class:`ml.adaboost.AdaBoost`    -- the comparison model
* :class:`ml.kmeans.KMeans`        -- unsupervised, to show the classes
  separate even when nobody hands over the labels

The trees are fed the raw feature values -- a tree only ever compares a feature
against itself, so scaling it changes nothing.  K-Means and the PCA projection
are fed a standardised, deliberately narrower set: see ``CLUSTER_FEATURES``.
"""

import pathlib
import pickle

import numpy as np

from ciphers import CIPHER_NAMES
from ml import features as feature_module
from ml.adaboost import AdaBoost
from ml.forest import RandomForest
from ml.kmeans import KMeans

# K-Means measures plain euclidean distance, so every feature it is given pulls
# on the result equally.  Handing it all 49 -- including 26 sorted-frequency
# bins and 12 periodic-IC bins that mostly encode passage length -- swamps the
# handful of features that actually separate the cipher types, and the clusters
# come out mixed.  The trees are left on the full set (they pick what they
# need); the unsupervised side gets the compact, discriminative scalars.
CLUSTER_FEATURES = [
    "index_of_coincidence", "entropy", "chi2_shift0", "chi2_best_shift",
    "chi2_shift_gap", "bigram_repeat_rate", "trigram_repeat_rate",
    "doubled_letter_rate", "best_period_ic", "period_ic_lift",
]

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "identifier.pkl"

CLASSES = list(CIPHER_NAMES)


class Standardiser:
    """Zero mean, unit variance per feature.  Fitted on the training set only."""

    def fit(self, X):
        X = np.asarray(X, dtype=np.float64)
        self.mean_ = X.mean(axis=0)
        self.scale_ = X.std(axis=0)
        self.scale_[self.scale_ < 1e-12] = 1.0
        return self

    def transform(self, X):
        return (np.asarray(X, dtype=np.float64) - self.mean_) / self.scale_

    def fit_transform(self, X):
        return self.fit(X).transform(X)


class PCA2D:
    """Two-component PCA from scratch, for the cluster scatter plot.

    Computed from the eigenvectors of the covariance matrix -- with 49 features
    that is a 49x49 symmetric eigenproblem, small enough that there is no
    reason to reach for anything cleverer.
    """

    def fit(self, X):
        X = np.asarray(X, dtype=np.float64)
        self.mean_ = X.mean(axis=0)
        centred = X - self.mean_
        covariance = np.cov(centred, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        order = np.argsort(values)[::-1][:2]
        self.components_ = vectors[:, order].T
        self.explained_variance_ratio_ = (values[order] / values.sum()).tolist()
        return self

    def transform(self, X):
        return (np.asarray(X, dtype=np.float64) - self.mean_) @ self.components_.T

    def fit_transform(self, X):
        return self.fit(X).transform(X)


class CipherIdentifier:
    """Trained bundle: scaler, forest, AdaBoost, K-Means and the PCA projection."""

    def __init__(self, classes=None):
        self.classes = list(classes or CLASSES)
        self.feature_names = list(feature_module.FEATURE_NAMES)
        self.cluster_columns = [
            self.feature_names.index(name) for name in CLUSTER_FEATURES
        ]
        self.forest = None
        self.adaboost = None
        self.kmeans = None
        self.scaler = None
        self.pca = None
        self.metrics = {}

    # ------------------------------------------------------------------ train

    def fit(self, X, y, n_estimators=150, n_stumps=200, random_state=0,
            progress=None):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        n_classes = len(self.classes)

        def note(stage):
            if progress:
                progress(stage)

        note("forest")
        self.forest = RandomForest(
            n_estimators=n_estimators, max_features="sqrt",
            min_samples_leaf=2, random_state=random_state,
        ).fit(X, y, n_classes=n_classes)

        note("adaboost")
        self.adaboost = AdaBoost(
            n_estimators=n_stumps, random_state=random_state
        ).fit(X, y, n_classes=n_classes)

        note("kmeans")
        self.scaler = Standardiser().fit(X[:, self.cluster_columns])
        scaled = self.scaler.transform(X[:, self.cluster_columns])
        self.kmeans = KMeans(
            n_clusters=n_classes, n_init=10, random_state=random_state
        ).fit(scaled)

        note("pca")
        self.pca = PCA2D().fit(scaled)
        return self

    # ---------------------------------------------------------------- predict

    def predict_proba(self, texts, model="forest"):
        X = feature_module.extract_many(texts)
        estimator = self.adaboost if model == "adaboost" else self.forest
        return estimator.predict_proba(X)

    def identify(self, text, model="forest"):
        """Full report on one ciphertext, shaped for the UI."""
        X = feature_module.extract(text).reshape(1, -1)
        forest_proba = self.forest.predict_proba(X)[0]
        ada_proba = self.adaboost.predict_proba(X)[0]
        proba = ada_proba if model == "adaboost" else forest_proba

        scaled = self.scaler.transform(X[:, self.cluster_columns])
        cluster = int(self.kmeans.predict(scaled)[0])
        point = self.pca.transform(scaled)[0]

        order = np.argsort(proba)[::-1]
        return {
            "prediction": self.classes[int(order[0])],
            "confidence": float(proba[order[0]]),
            "model": model,
            "probabilities": [
                {"cipher": self.classes[int(i)], "probability": float(proba[i])}
                for i in order
            ],
            "forest_probabilities": {
                self.classes[i]: float(p) for i, p in enumerate(forest_proba)
            },
            "adaboost_probabilities": {
                self.classes[i]: float(p) for i, p in enumerate(ada_proba)
            },
            "cluster": cluster,
            "projection": {"x": float(point[0]), "y": float(point[1])},
            "features": {
                name: float(value)
                for name, value in zip(self.feature_names, X[0])
                if not name.startswith(("sorted_freq_", "period_ic_"))
            },
            "top_features": self.top_features(6),
        }

    def top_features(self, k=10):
        if self.forest is None:
            return []
        order = np.argsort(self.forest.feature_importances_)[::-1][:k]
        return [
            {"feature": self.feature_names[int(i)],
             "importance": float(self.forest.feature_importances_[i])}
            for i in order
        ]

    def cluster_scatter(self, X, y=None, limit=600, random_state=0):
        """Points for the Identify page's 2D cluster map."""
        X = np.asarray(X, dtype=np.float64)
        rng = np.random.default_rng(random_state)
        rows = (
            rng.choice(len(X), size=limit, replace=False) if len(X) > limit
            else np.arange(len(X))
        )
        scaled = self.scaler.transform(X[rows][:, self.cluster_columns])
        points = self.pca.transform(scaled)
        clusters = self.kmeans.predict(scaled)
        return [
            {
                "x": float(points[n, 0]),
                "y": float(points[n, 1]),
                "cluster": int(clusters[n]),
                "label": self.classes[int(y[rows[n]])] if y is not None else None,
            }
            for n in range(len(rows))
        ]

    # ------------------------------------------------------------ persistence

    def save(self, path=MODEL_PATH):
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as handle:
            pickle.dump(self, handle)
        return path

    @staticmethod
    def load(path=MODEL_PATH):
        with open(path, "rb") as handle:
            return pickle.load(handle)


_IDENTIFIER = None


def get_identifier():
    """Process-wide singleton, loaded from disk."""
    global _IDENTIFIER
    if _IDENTIFIER is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"{MODEL_PATH} is missing. Run: python -m scripts.train_identifier"
            )
        _IDENTIFIER = CipherIdentifier.load()
    return _IDENTIFIER


def cluster_matrix(identifier, X):
    """The exact matrix the unsupervised models see, for scripts and notebooks."""
    return identifier.scaler.transform(np.asarray(X)[:, identifier.cluster_columns])
