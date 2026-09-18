"""Gaussian random numbers from scratch, and the MCMC Playground sampler.

Box-Muller
----------
A uniform random number generator is the only primitive we are given.  Box-
Muller turns a pair of uniforms into a pair of independent standard normals by
sampling in polar coordinates: the squared radius of a 2D standard normal is
exponentially distributed and its angle is uniform, so

    R = sqrt(-2 ln U1),   theta = 2 pi U2
    Z0 = R cos(theta),    Z1 = R sin(theta)

gives two normals for two uniforms, with no rejection and no approximation.

The Playground
--------------
The target is a 2D mixture of Gaussians -- deliberately multi-peaked, because
a single peak hides the failure mode the page exists to show.  A random-walk
Metropolis sampler explores it, and the step size is the slider:

* **too small** -- almost everything is accepted, but the chain shuffles and
  takes forever to cross between peaks (slow mixing, high autocorrelation)
* **too large** -- proposals land in empty space and are rejected, so the chain
  sits still for long stretches
* **about right** -- an acceptance rate near 0.234, the known optimum for
  random-walk Metropolis in high dimensions, and the one that gets the most
  effective samples per step
"""

import math

import numpy as np


class BoxMuller:
    """Standard normal draws built from uniforms, one pair at a time."""

    def __init__(self, seed=None):
        self.rng = np.random.default_rng(seed)
        self._spare = None

    def normal(self):
        """One standard normal.  Each call to Box-Muller yields two, so the
        second is cached and handed out on the next call."""
        if self._spare is not None:
            value, self._spare = self._spare, None
            return value
        u1 = max(self.rng.random(), 1e-12)     # ln(0) is not allowed
        u2 = self.rng.random()
        radius = math.sqrt(-2.0 * math.log(u1))
        angle = 2.0 * math.pi * u2
        self._spare = radius * math.sin(angle)
        return radius * math.cos(angle)

    def normals(self, size):
        """Vectorised Box-Muller: ``size`` standard normals at once."""
        n = int(size)
        half = (n + 1) // 2
        u1 = np.maximum(self.rng.random(half), 1e-12)
        u2 = self.rng.random(half)
        radius = np.sqrt(-2.0 * np.log(u1))
        angle = 2.0 * np.pi * u2
        return np.concatenate([radius * np.cos(angle), radius * np.sin(angle)])[:n]


# The target distribution: three well-separated peaks of different weight.
DEFAULT_MIXTURE = [
    {"weight": 0.4, "mean": [-2.0, -1.0], "cov": [[0.5, 0.25], [0.25, 0.4]]},
    {"weight": 0.35, "mean": [2.2, 1.6], "cov": [[0.6, -0.3], [-0.3, 0.5]]},
    {"weight": 0.25, "mean": [0.0, 3.0], "cov": [[0.3, 0.0], [0.0, 0.8]]},
]


class GaussianMixture2D:
    """The Playground's target density, and its exact log-density."""

    def __init__(self, components=None):
        self.components = components or DEFAULT_MIXTURE
        self.weights = np.array([c["weight"] for c in self.components], dtype=float)
        self.weights /= self.weights.sum()
        self.means = np.array([c["mean"] for c in self.components], dtype=float)
        self.covs = np.array([c["cov"] for c in self.components], dtype=float)
        self.precisions = np.linalg.inv(self.covs)
        self.norms = 1.0 / (2 * np.pi * np.sqrt(np.linalg.det(self.covs)))

    def density(self, points):
        points = np.atleast_2d(points)
        total = np.zeros(len(points))
        for w, mean, precision, norm in zip(
            self.weights, self.means, self.precisions, self.norms
        ):
            offset = points - mean
            exponent = -0.5 * np.einsum("ij,jk,ik->i", offset, precision, offset)
            total += w * norm * np.exp(exponent)
        return total

    def log_density(self, point):
        return float(np.log(max(self.density(point)[0], 1e-300)))

    def grid(self, extent=6.0, resolution=60):
        """Density on a grid, so the UI can draw contours behind the samples."""
        axis = np.linspace(-extent, extent, resolution)
        xx, yy = np.meshgrid(axis, axis)
        values = self.density(np.column_stack([xx.ravel(), yy.ravel()]))
        return axis.tolist(), values.reshape(resolution, resolution).tolist()


def metropolis_2d(target, step_size=1.0, n_samples=5000, burn_in=500, seed=None,
                  start=(0.0, 0.0)):
    """Random-walk Metropolis on a 2D target, using Box-Muller for the steps.

    The proposal is symmetric (a Gaussian centred on the current point), so the
    acceptance ratio is just the density ratio -- the same simplification the
    cipher solver relies on.
    """
    gauss = BoxMuller(seed)
    uniforms = gauss.rng
    current = np.array(start, dtype=float)
    current_logp = target.log_density(current)

    total = n_samples + burn_in
    steps = gauss.normals(2 * total).reshape(total, 2) * step_size

    samples = np.empty((total, 2))
    accepted_flags = np.zeros(total, dtype=bool)
    accepted = 0

    for i in range(total):
        candidate = current + steps[i]
        candidate_logp = target.log_density(candidate)
        if candidate_logp >= current_logp or uniforms.random() < math.exp(
            candidate_logp - current_logp
        ):
            current, current_logp = candidate, candidate_logp
            accepted += 1
            accepted_flags[i] = True
        samples[i] = current

    kept = samples[burn_in:]
    return {
        "samples": kept,
        "acceptance_rate": accepted / total,
        "acceptance_rate_post_burnin": float(accepted_flags[burn_in:].mean()),
        "burn_in": burn_in,
        "step_size": step_size,
        "trace": samples,
    }


def autocorrelation(series, max_lag=100):
    """Normalised autocorrelation of a 1D chain, used for the ESS estimate."""
    series = np.asarray(series, dtype=float)
    series = series - series.mean()
    variance = np.dot(series, series)
    if variance <= 0:
        return np.zeros(max_lag + 1)
    lags = min(max_lag, len(series) - 1)
    out = np.empty(lags + 1)
    for lag in range(lags + 1):
        out[lag] = np.dot(series[: len(series) - lag], series[lag:]) / variance
    return out


def effective_sample_size(samples, max_lag=200):
    """ESS via the initial-positive-sequence rule.

    ``N / (1 + 2 * sum rho_k)``, truncating the sum at the first negative
    autocorrelation.  It answers the question the step-size slider is really
    about: how many *independent* samples did those 5,000 steps actually buy?
    """
    samples = np.asarray(samples, dtype=float)
    if samples.ndim == 1:
        samples = samples[:, None]
    n = len(samples)
    out = []
    for dim in range(samples.shape[1]):
        rho = autocorrelation(samples[:, dim], max_lag)
        total = 0.0
        for k in range(1, len(rho)):
            if rho[k] < 0:
                break
            total += rho[k]
        out.append(float(n / (1.0 + 2.0 * total)))
    return out
