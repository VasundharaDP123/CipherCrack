"""K-Means from scratch, doubling as the vector quantizer.

Clustering and vector quantization are the same algorithm read two ways, which
is why one file covers both syllabus topics:

* as **clustering**, the centroids are groups and we care which group a point
  lands in -- here, whether ciphertexts of the same type fall together without
  ever being told their labels;
* as **vector quantization**, the centroids are a *codebook* and we care about
  the centroid itself -- each ciphertext is replaced by the index of its nearest
  code word, compressing a 49-number feature profile to a single integer.

k-means++ seeding is included because uniform random seeding on this data
regularly drops two centroids into the same dense blob and leaves a real
cluster unclaimed.
"""

import numpy as np


class KMeans:
    """Lloyd's algorithm with k-means++ seeding."""

    def __init__(self, n_clusters=4, max_iter=300, tol=1e-6, n_init=10,
                 init="k-means++", random_state=None):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.n_init = n_init
        self.init = init
        self.random_state = random_state

    # ------------------------------------------------------------------ init

    def _seed(self, X, rng):
        n = len(X)
        if self.init != "k-means++":
            return X[rng.choice(n, size=self.n_clusters, replace=False)].copy()

        # k-means++: each new centre is drawn with probability proportional to
        # its squared distance from the nearest centre already chosen, which
        # spreads the seeds out instead of clumping them.
        centres = [X[rng.integers(n)]]
        closest = np.sum((X - centres[0]) ** 2, axis=1)
        for _ in range(1, self.n_clusters):
            total = closest.sum()
            if total <= 0:
                centres.append(X[rng.integers(n)])
            else:
                centres.append(X[rng.choice(n, p=closest / total)])
            closest = np.minimum(closest, np.sum((X - centres[-1]) ** 2, axis=1))
        return np.array(centres)

    # ------------------------------------------------------------------- fit

    def _distances(self, X, centres):
        """Squared euclidean distances, via the |a-b|^2 = |a|^2 - 2ab + |b|^2 trick."""
        return (
            np.sum(X ** 2, axis=1)[:, None]
            - 2 * X @ centres.T
            + np.sum(centres ** 2, axis=1)[None, :]
        )

    def _run_once(self, X, rng):
        centres = self._seed(X, rng)
        labels = np.zeros(len(X), dtype=np.int64)
        inertia = np.inf

        for _ in range(self.max_iter):
            distances = self._distances(X, centres)
            labels = np.argmin(distances, axis=1)
            new_inertia = float(distances[np.arange(len(X)), labels].sum())

            for k in range(self.n_clusters):
                members = X[labels == k]
                if len(members):
                    centres[k] = members.mean(axis=0)
                else:
                    # An empty cluster is useless; restart it at the point
                    # currently worst served by its own centroid.
                    centres[k] = X[int(np.argmax(distances[np.arange(len(X)), labels]))]

            if abs(inertia - new_inertia) <= self.tol * max(abs(inertia), 1.0):
                inertia = new_inertia
                break
            inertia = new_inertia

        # The loop's labels and inertia were measured against the centroids as
        # they stood *before* the last update, so they do not match the
        # centroids being returned.  One final assignment puts all three in
        # agreement -- without this, `labels_` can disagree with `predict()` on
        # the very data it was fitted to.
        distances = self._distances(X, centres)
        labels = np.argmin(distances, axis=1)
        inertia = float(distances[np.arange(len(X)), labels].sum())
        return centres, labels, inertia

    def fit(self, X):
        X = np.asarray(X, dtype=np.float64)
        rng = np.random.default_rng(self.random_state)
        best = None
        for _ in range(self.n_init):
            centres, labels, inertia = self._run_once(X, rng)
            if best is None or inertia < best[2]:
                best = (centres, labels, inertia)
        self.cluster_centers_, self.labels_, self.inertia_ = best
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=np.float64)
        return np.argmin(self._distances(X, self.cluster_centers_), axis=1)

    fit_predict = lambda self, X: self.fit(X).labels_       # noqa: E731

    # --------------------------------------------------- vector quantization

    def encode(self, X):
        """Quantize: each point becomes the index of its nearest code word."""
        return self.predict(X)

    def decode(self, codes):
        """Dequantize: replace each code with its code word."""
        return self.cluster_centers_[np.asarray(codes)]

    def quantization_error(self, X):
        """Mean squared distance between points and their code words."""
        X = np.asarray(X, dtype=np.float64)
        return float(np.mean(np.sum((X - self.decode(self.encode(X))) ** 2, axis=1)))


def silhouette_score(X, labels):
    """Mean silhouette over all points, from scratch.

    For each point: ``(b - a) / max(a, b)`` where ``a`` is its mean distance to
    its own cluster and ``b`` the best mean distance to any other cluster.
    Runs +1 (tight, well separated) to -1 (in the wrong cluster).
    """
    X = np.asarray(X, dtype=np.float64)
    labels = np.asarray(labels)
    unique = np.unique(labels)
    if len(unique) < 2:
        return 0.0

    distances = np.sqrt(np.maximum(
        np.sum(X ** 2, axis=1)[:, None] - 2 * X @ X.T + np.sum(X ** 2, axis=1)[None, :],
        0.0,
    ))
    scores = np.zeros(len(X))
    for i in range(len(X)):
        own = labels == labels[i]
        own_size = own.sum()
        if own_size <= 1:
            scores[i] = 0.0
            continue
        a = (distances[i][own].sum()) / (own_size - 1)     # exclude self (distance 0)
        b = min(
            distances[i][labels == other].mean()
            for other in unique if other != labels[i]
        )
        scores[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(scores.mean())


def elbow_curve(X, k_values, random_state=0, n_init=5):
    """Inertia for a range of ``k``, for the elbow plot."""
    return [
        {"k": int(k),
         "inertia": float(KMeans(n_clusters=k, n_init=n_init,
                                 random_state=random_state).fit(X).inertia_)}
        for k in k_values
    ]
