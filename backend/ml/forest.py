"""Random forest, written from scratch on top of :mod:`ml.tree`.

Bagging plus random feature subsets.  Two separate sources of randomness, and
it is worth being clear about why *both* are there:

* **Bootstrap sampling** gives each tree a different draw of the data, so their
  errors are at least partly independent and averaging cancels some of them.
* **A random feature subset at every split** goes further.  With bagging alone,
  one dominant feature -- here the index of coincidence, which by itself nearly
  separates Vigenere from the rest -- would sit at the root of every tree and
  the ensemble would be 200 near-identical trees.  Hiding most features from
  each split forces trees to find the other signals, and decorrelated trees are
  what makes the average better than its members.

Out-of-bag scoring comes free with the bootstrap: each tree's own left-out
third of the data is a ready-made validation set, so the forest can report an
honest accuracy without a separate split.
"""

import numpy as np

from ml.tree import DecisionTree


class RandomForest:
    """Bagged decision trees with random feature subsets at each split."""

    def __init__(
        self,
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features="sqrt",
        criterion="gini",
        bootstrap=True,
        random_state=None,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.criterion = criterion
        self.bootstrap = bootstrap
        self.random_state = random_state
        self.trees = []
        self.oob_score_ = None

    def fit(self, X, y, n_classes=None, progress=None):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        n = len(y)
        self.n_classes = int(n_classes or y.max() + 1)
        self.n_features = X.shape[1]
        rng = np.random.default_rng(self.random_state)

        self.trees = []
        oob_votes = np.zeros((n, self.n_classes))

        for i in range(self.n_estimators):
            if self.bootstrap:
                rows = rng.integers(0, n, size=n)
            else:
                rows = np.arange(n)

            tree = DecisionTree(
                max_depth=self.max_depth,
                min_samples_split=self.min_samples_split,
                min_samples_leaf=self.min_samples_leaf,
                max_features=self.max_features,
                criterion=self.criterion,
                random_state=int(rng.integers(0, 2**31 - 1)),
            )
            tree.fit(X[rows], y[rows], n_classes=self.n_classes)
            self.trees.append(tree)

            if self.bootstrap:
                out_of_bag = np.setdiff1d(np.arange(n), rows, assume_unique=False)
                if len(out_of_bag):
                    oob_votes[out_of_bag] += tree.predict_proba(X[out_of_bag])

            if progress is not None:
                progress(i + 1, self.n_estimators)

        if self.bootstrap:
            seen = oob_votes.sum(axis=1) > 0
            if seen.any():
                self.oob_score_ = float(
                    np.mean(np.argmax(oob_votes[seen], axis=1) == y[seen])
                )

        importances = np.array([t.feature_importances_ for t in self.trees])
        self.feature_importances_ = importances.mean(axis=0)
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=np.float64)
        total = np.zeros((len(X), self.n_classes))
        for tree in self.trees:
            total += tree.predict_proba(X)
        return total / len(self.trees)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)

    def score(self, X, y):
        return float(np.mean(self.predict(X) == np.asarray(y)))

    def describe(self):
        return {
            "n_estimators": len(self.trees),
            "mean_depth": float(np.mean([t.depth() for t in self.trees])),
            "mean_leaves": float(np.mean([t.n_leaves() for t in self.trees])),
            "oob_score": self.oob_score_,
        }
