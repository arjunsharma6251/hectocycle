"""Cycle-life prediction intervals that answer any spec threshold at once.

The qualification classifier answers "P(life >= 700)". A lab with a different
spec would need another classifier, and a grid of them can contradict itself
(PASS at 800 but FAIL at 750). Here one regression of log10(cycle life) on the
DeltaQ(V) features carries a jackknife+ prediction interval [lo, hi] in
cycles (Barber, Candes, Ramdas & Tibshirani 2021, Ann. Statist.), and every
threshold's verdict falls out of that one interval:

    pass if lo >= T,  fail if hi < T,  keep testing otherwise

which is monotone in T by construction. The fitted object is tiny (n
leave-one-out coefficient vectors + n residuals), so it exports to the
browser for scoring at any T; see to_export().
"""

import math

import numpy as np


def _ols(X, y):
    A = np.c_[np.ones(len(X)), X]
    return np.linalg.lstsq(A, y, rcond=None)[0]


def _predict(beta, X):
    return beta[0] + np.asarray(X, float) @ beta[1:]


class JackknifePlusLife:
    """OLS on log10(life) with jackknife+ intervals at nominal 1 - alpha."""

    def __init__(self, alpha=0.10):
        self.alpha = alpha

    def fit(self, X, life):
        X = np.asarray(X, float)
        y = np.log10(np.asarray(life, float))
        n = len(y)
        self.beta_ = _ols(X, y)
        self.loo_beta_ = np.empty((n, X.shape[1] + 1))
        self.loo_resid_ = np.empty(n)
        for i in range(n):
            keep = np.arange(n) != i
            b = _ols(X[keep], y[keep])
            self.loo_beta_[i] = b
            self.loo_resid_[i] = abs(y[i] - _predict(b, X[i:i + 1])[0])
        return self

    def _ranks(self):
        n = len(self.loo_resid_)
        k_lo = math.floor(self.alpha * (n + 1))       # k-th smallest, 1-based
        k_hi = math.ceil((1 - self.alpha) * (n + 1))
        return k_lo, k_hi

    def predict(self, X):
        """(point, lo, hi) in cycles; lo is 0 / hi is inf when n is too small."""
        X = np.asarray(X, float)
        mu = np.stack([_predict(b, X) for b in self.loo_beta_], axis=1)  # (m, n)
        lo_set = np.sort(mu - self.loo_resid_, axis=1)
        hi_set = np.sort(mu + self.loo_resid_, axis=1)
        k_lo, k_hi = self._ranks()
        n = mu.shape[1]
        lo = lo_set[:, k_lo - 1] if k_lo >= 1 else np.full(len(X), -np.inf)
        hi = hi_set[:, k_hi - 1] if k_hi <= n else np.full(len(X), np.inf)
        return 10 ** _predict(self.beta_, X), 10 ** lo, 10 ** hi

    def to_export(self, digits=8):
        r = lambda a: [round(float(v), digits) for v in a]
        k_lo, k_hi = self._ranks()
        return {"alpha": self.alpha, "k_lo": k_lo, "k_hi": k_hi, "beta": r(self.beta_),
                "loo_beta": [r(b) for b in self.loo_beta_], "loo_resid": r(self.loo_resid_)}


def verdict(lo, hi, threshold):
    """1 pass / 0 fail / -1 keep testing, elementwise."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return np.where(lo >= threshold, 1, np.where(hi < threshold, 0, -1))
