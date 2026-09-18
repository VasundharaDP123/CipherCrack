"""A CART decision tree, written from scratch.

The building block for both ensemble methods in the project: bagged into a
random forest (:mod:`ml.forest`) and stumped into AdaBoost (:mod:`ml.adaboost`).

Finding the best split without a Python loop over thresholds
------------------------------------------------------------
The textbook description -- "try every threshold and keep the best" -- is
quadratic if taken literally.  Instead, for each candidate feature the samples
are sorted once and the class counts are accumulated along that order, so the
class distribution on either side of *every* possible threshold is read
straight off a cumulative sum.  Gini impurity for all thresholds then falls out
as one vectorised expression, and the whole split search for a node costs one
sort per feature.

Sample weights are carried throughout, because AdaBoost needs to train stumps
on a reweighted dataset and re-deriving a separate weighted implementation
would be a second thing to get wrong.
"""

import numpy as np


class _Node:
    __slots__ = ("feature", "threshold", "left", "right", "proba", "n_samples")

    def __init__(self, proba, n_samples):
        self.feature = None
        self.threshold = None
        self.left = None
        self.right = None
        self.proba = proba
        self.n_samples = n_samples

    @property
    def is_leaf(self):
        return self.feature is None


def _gini(counts, total):
    """Gini impurity of a class-count vector (or a stack of them)."""
    safe = np.maximum(total, 1e-12)
    p = counts / safe[..., None]
    return 1.0 - np.sum(p * p, axis=-1)


def _entropy(counts, total):
    safe = np.maximum(total, 1e-12)
    p = counts / safe[..., None]
    p = np.clip(p, 1e-12, 1.0)
    return -np.sum(p * np.log2(p), axis=-1)


CRITERIA = {"gini": _gini, "entropy": _entropy}


class DecisionTree:
    """Classification tree with Gini or entropy splitting."""

    def __init__(
        self,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features=None,
        criterion="gini",
        random_state=None,
    ):
        self.max_depth = max_depth if max_depth is not None else 2**31
        self.min_samples_split = min_samples_split
        self.min_samples_leaf = min_samples_leaf
        self.max_features = max_features
        self.criterion = criterion
        self.random_state = random_state
        self.root = None
        self.n_classes = 0
        self.n_features = 0

    # -------------------------------------------------------------- splitting

    def _n_features_to_try(self):
        if self.max_features is None:
            return self.n_features
        if self.max_features == "sqrt":
            return max(1, int(np.sqrt(self.n_features)))
        if self.max_features == "log2":
            return max(1, int(np.log2(self.n_features)))
        if isinstance(self.max_features, float):
            return max(1, int(self.max_features * self.n_features))
        return min(int(self.max_features), self.n_features)

    def _best_split(self, X, y, weights, onehot):
        """Return ``(feature, threshold, gain)`` for the best split, or ``None``."""
        impurity_fn = CRITERIA[self.criterion]
        total_weight = weights.sum()
        parent_counts = onehot.T @ weights
        parent_impurity = impurity_fn(parent_counts, total_weight)

        candidates = self._rng.choice(
            self.n_features, size=self._n_features_to_try(), replace=False
        )

        best = None
        best_gain = 1e-12                     # require a real improvement
        for feature in candidates:
            column = X[:, feature]
            order = np.argsort(column, kind="stable")
            values = column[order]
            w = weights[order]

            # Cumulative weighted class counts for every prefix of the order.
            left_counts = np.cumsum(onehot[order] * w[:, None], axis=0)[:-1]
            left_weight = np.cumsum(w)[:-1]
            right_counts = parent_counts - left_counts
            right_weight = total_weight - left_weight

            # A split is only legal between two *different* feature values.
            legal = values[:-1] < values[1:]
            legal &= left_weight > 0
            legal &= right_weight > 0
            if self.min_samples_leaf > 1:
                sizes = np.arange(1, len(values))
                legal &= sizes >= self.min_samples_leaf
                legal &= (len(values) - sizes) >= self.min_samples_leaf
            if not legal.any():
                continue

            child = (
                left_weight * impurity_fn(left_counts, left_weight)
                + right_weight * impurity_fn(right_counts, right_weight)
            ) / total_weight
            gains = parent_impurity - child
            gains[~legal] = -np.inf

            at = int(np.argmax(gains))
            if gains[at] > best_gain:
                best_gain = float(gains[at])
                threshold = (values[at] + values[at + 1]) / 2.0
                best = (int(feature), float(threshold), best_gain)
        return best

    # ------------------------------------------------------------------ fit

    def fit(self, X, y, sample_weight=None, n_classes=None):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        self.n_features = X.shape[1]
        self.n_classes = int(n_classes or y.max() + 1)
        self._rng = np.random.default_rng(self.random_state)

        weights = (
            np.ones(len(y), dtype=np.float64)
            if sample_weight is None
            else np.asarray(sample_weight, dtype=np.float64)
        )
        onehot = np.zeros((len(y), self.n_classes))
        onehot[np.arange(len(y)), y] = 1.0

        self.feature_importances_ = np.zeros(self.n_features)
        self.root = self._grow(X, y, weights, onehot, depth=0)
        total = self.feature_importances_.sum()
        if total > 0:
            self.feature_importances_ /= total
        return self

    def _leaf(self, weights, onehot):
        counts = onehot.T @ weights
        total = counts.sum()
        proba = counts / total if total > 0 else np.full(self.n_classes, 1.0 / self.n_classes)
        return _Node(proba, int(len(weights)))

    def _grow(self, X, y, weights, onehot, depth):
        node = self._leaf(weights, onehot)

        if (
            depth >= self.max_depth
            or len(y) < self.min_samples_split
            or len(np.unique(y)) == 1
        ):
            return node

        split = self._best_split(X, y, weights, onehot)
        if split is None:
            return node

        feature, threshold, gain = split
        mask = X[:, feature] <= threshold
        if not mask.any() or mask.all():
            return node

        node.feature, node.threshold = feature, threshold
        self.feature_importances_[feature] += gain * weights.sum()
        node.left = self._grow(X[mask], y[mask], weights[mask], onehot[mask], depth + 1)
        node.right = self._grow(X[~mask], y[~mask], weights[~mask], onehot[~mask], depth + 1)
        return node

    # -------------------------------------------------------------- predict

    def predict_proba(self, X):
        X = np.asarray(X, dtype=np.float64)
        out = np.empty((len(X), self.n_classes))
        self._descend(self.root, X, np.arange(len(X)), out)
        return out

    def _descend(self, node, X, rows, out):
        """Push whole blocks of rows down the tree rather than one at a time."""
        if node.is_leaf:
            out[rows] = node.proba
            return
        mask = X[rows, node.feature] <= node.threshold
        if mask.any():
            self._descend(node.left, X, rows[mask], out)
        if not mask.all():
            self._descend(node.right, X, rows[~mask], out)

    def predict(self, X):
        return np.argmax(self.predict_proba(X), axis=1)

    # ----------------------------------------------------------------- info

    def depth(self):
        def walk(node):
            return 0 if node.is_leaf else 1 + max(walk(node.left), walk(node.right))
        return walk(self.root)

    def n_leaves(self):
        def walk(node):
            return 1 if node.is_leaf else walk(node.left) + walk(node.right)
        return walk(self.root)


class DecisionStump(DecisionTree):
    """A tree of depth one -- the weak learner AdaBoost boosts."""

    def __init__(self, criterion="gini", random_state=None):
        super().__init__(max_depth=1, criterion=criterion, random_state=random_state)
