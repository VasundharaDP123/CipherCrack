"""AdaBoost with decision stumps, written from scratch.

Bagging and boosting both build a committee, but for opposite reasons, and that
contrast is the point of running both on the same problem:

* a **random forest** trains its trees independently on different samples and
  averages away their *variance*;
* **AdaBoost** trains stumps in sequence, each one on a reweighted dataset that
  emphasises what the previous ones got wrong, and drives down *bias*.  A
  single stump here is barely better than guessing -- it can only ask one
  question, say "is the index of coincidence below 0.05?" -- yet a few hundred
  of them, each with a vote weighted by its own accuracy, catch up with the
  forest.

This is SAMME (Zhu et al. 2009), the multi-class generalisation: with ``K``
classes a learner only has to beat ``1/K`` rather than ``1/2`` to be useful, and
the ``log(K - 1)`` term in the vote weight is what restores that.  With ``K = 2``
it reduces exactly to the original binary AdaBoost.
"""

import numpy as np

from ml.tree import DecisionStump


class AdaBoost:
    """SAMME AdaBoost over depth-one decision trees."""

    def __init__(self, n_estimators=200, learning_rate=1.0, random_state=None):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.learners = []
        self.alphas = []
        self.errors_ = []

    def fit(self, X, y, n_classes=None, progress=None):
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int64)
        n = len(y)
        self.n_classes = int(n_classes or y.max() + 1)
        rng = np.random.default_rng(self.random_state)

        weights = np.full(n, 1.0 / n)
        self.learners, self.alphas, self.errors_ = [], [], []

        for i in range(self.n_estimators):
            stump = DecisionStump(random_state=int(rng.integers(0, 2**31 - 1)))
            stump.fit(X, y, sample_weight=weights, n_classes=self.n_classes)
            predictions = stump.predict(X)

            wrong = predictions != y
            error = float(np.sum(weights[wrong]))

            # A learner no better than random guessing carries no information;
            # one that is perfect would need infinite weight, so stop at both ends.
            if error >= 1.0 - 1.0 / self.n_classes:
                if not self.learners:          # keep at least one, or we cannot predict
                    self.learners.append(stump)
                    self.alphas.append(1e-6)
                break
            if error <= 0:
                self.learners.append(stump)
                self.alphas.append(1.0)
                self.errors_.append(0.0)
                break

            alpha = self.learning_rate * (
                np.log((1.0 - error) / error) + np.log(self.n_classes - 1)
            )
            weights = weights * np.exp(alpha * wrong)
            weights /= weights.sum()

            self.learners.append(stump)
            self.alphas.append(float(alpha))
            self.errors_.append(error)

            if progress is not None:
                progress(i + 1, self.n_estimators)

        self.alphas = np.asarray(self.alphas, dtype=np.float64)
        return self

    def decision_function(self, X):
        """Weighted vote per class."""
        X = np.asarray(X, dtype=np.float64)
        votes = np.zeros((len(X), self.n_classes))
        for stump, alpha in zip(self.learners, self.alphas):
            predictions = stump.predict(X)
            votes[np.arange(len(X)), predictions] += alpha
        return votes

    def predict_proba(self, X):
        """Softmax over the weighted votes, so the UI has confidence bars.

        SAMME votes are unnormalised margins rather than probabilities; the
        usual fix is to exponentiate and normalise, which preserves the ranking
        and gives a calibrated-looking spread.
        """
        votes = self.decision_function(X)
        votes = votes - votes.max(axis=1, keepdims=True)
        scaled = np.exp(votes / max(self.alphas.sum() / len(self.alphas), 1e-9))
        return scaled / scaled.sum(axis=1, keepdims=True)

    def predict(self, X):
        return np.argmax(self.decision_function(X), axis=1)

    def score(self, X, y):
        return float(np.mean(self.predict(X) == np.asarray(y)))

    def staged_score(self, X, y):
        """Accuracy after each additional stump -- the boosting curve."""
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y)
        votes = np.zeros((len(X), self.n_classes))
        out = []
        for stump, alpha in zip(self.learners, self.alphas):
            votes[np.arange(len(X)), stump.predict(X)] += alpha
            out.append(float(np.mean(np.argmax(votes, axis=1) == y)))
        return out

    def describe(self):
        return {
            "n_estimators": len(self.learners),
            "mean_alpha": float(np.mean(self.alphas)) if len(self.alphas) else 0.0,
            "final_weighted_error": self.errors_[-1] if self.errors_ else None,
        }
