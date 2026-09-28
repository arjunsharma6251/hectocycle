"""Pilot-cell batch recalibration and the provisional-pull policy.

The out-of-sample study found that a new batch can shift every cell's log
life by a common offset (batch 4: -0.11 in log10, i.e. ~18% shorter) while
the DeltaQ(V) ranking survives. Offsets also differ among the training
batches themselves (b1 about +0.05, b2 about -0.05), and within a batch the scatter
is smaller than the pooled model's. So life is modelled as

    log10 life = x . beta + alpha_batch + e,   e ~ N(0, sigma_w^2)

with the slope shared across batches and one intercept per batch. For a new
batch, alpha is unknown until some of its cells reach end of life: k pilot
cells from the lot are run to failure (or to a cycle cap, as censored
observations), and alpha_hat is their mean residual (censored MLE if capped). The prediction interval for the batch's other cells has variance
sigma_w^2 (1 + 1/k), plus the slope's own uncertainty.

Provisional pull (docs/batch-recalibration-study.md): every cell starts
together. At checkpoints up to cycle 100 the shipped classifier's
confirmed-call rule pulls cells off the cycler provisionally. When the
pilots have died, an audit re-checks each pulled cell with the pilot-
calibrated interval: agreement makes the verdict final, anything else
sends the cell back on test (a reversal, charged as if never pulled).
"""

from dataclasses import dataclass, field

import numpy as np
from scipy import optimize, stats


class BatchOffsetLife:
    """OLS with a shared slope and per-batch intercepts on log10(life)."""

    def fit(self, X, life, batch):
        X = np.asarray(X, float)
        y = np.log10(np.asarray(life, float))
        self.batches_ = sorted(set(batch))
        D = np.array([[b == g for g in self.batches_] for b in batch], float)
        A = np.c_[X, D]
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        p = X.shape[1]
        self.beta_ = coef[:p]
        self.alpha_ = dict(zip(self.batches_, coef[p:]))
        resid = y - A @ coef
        self.df_ = len(y) - A.shape[1]
        self.sigma_w_ = float(np.sqrt(resid @ resid / self.df_))
        # covariance of the slope, for the prediction variance
        cov = self.sigma_w_ ** 2 * np.linalg.pinv(A.T @ A)
        self.cov_beta_ = cov[:p, :p]
        self.x_mean_ = X.mean(axis=0)
        return self

    def offset_from_pilots(self, X_pilot, life_pilot, cap=None):
        """alpha_hat for a new batch from its pilots.

        With no cap (or every pilot dead before it) this is the mean pilot
        residual after the shared slope. A pilot still alive at `cap` cycles
        only says log life >= log cap; alpha is then the censored (Tobit)
        maximum-likelihood estimate with the within-batch sigma.
        """
        xb = np.asarray(X_pilot, float) @ self.beta_
        life = np.asarray(life_pilot, float)
        if cap is None or np.all(life < cap):
            return float(np.mean(np.log10(life) - xb))
        dead = life < cap
        y = np.where(dead, np.log10(life), np.log10(cap))
        s = self.sigma_w_

        def nll(a):
            z = (y - xb - a) / s
            return -(stats.norm.logpdf(z[dead]).sum() + stats.norm.logsf(z[~dead]).sum())

        start = float(np.mean(y - xb))
        res = optimize.minimize_scalar(nll, bounds=(start - 1.0, start + 1.0), method="bounded")
        return float(res.x)

    def predict(self, X, alpha, k, level=0.90):
        """(point, lo, hi) in cycles for cells of a batch whose intercept came from k pilots."""
        X = np.asarray(X, float)
        mu = X @ self.beta_ + alpha
        d = X - self.x_mean_
        slope_var = np.einsum("ij,jk,ik->i", d, self.cov_beta_, d)
        sd = np.sqrt(self.sigma_w_ ** 2 * (1 + 1 / k) + slope_var)
        q = stats.t.ppf(0.5 + level / 2, self.df_)
        return 10 ** mu, 10 ** (mu - q * sd), 10 ** (mu + q * sd)


@dataclass
class PullOutcome:
    n_cells: int = 0
    pulled: int = 0
    confirmed: int = 0
    reversals: int = 0
    wrong_final: int = 0
    wrong_unaudited: int = 0
    cost_cycles: float = 0.0
    baseline_cycles: float = 0.0
    final_day: float = 0.0
    wrong_ids: list = field(default_factory=list)

    @property
    def saved_frac(self):
        return 1 - self.cost_cycles / self.baseline_cycles


def provisional_pull(cells, pilots, audit, threshold, minutes_per_cycle, pilot_cap=None):
    """Account one lot under provisional pull.

    cells: [{id, life, label, pull: (stop_cycle, verdict) or None}] for the
      non-pilot cells; `pull` is the stage-1 decision (None = never pulled).
    pilots: [{id, life}] run to end of life, or to `pilot_cap` cycles if
      they outlive it (the audit then uses them as censored).
    audit(cell, stop_cycle) -> (lo, hi) pilot-calibrated life interval in
      cycles from data up to stop_cycle; None disables the audit (the shipped
      behaviour, reported for comparison).
    """
    out = PullOutcome()
    cap = float("inf") if pilot_cap is None else pilot_cap
    for p in pilots:
        out.cost_cycles += min(p["life"], cap)
        out.baseline_cycles += min(p["life"], threshold)
    out.final_day = max((min(p["life"], cap) for p in pilots), default=0) * minutes_per_cycle / 1440
    for c in cells:
        out.n_cells += 1
        base = min(c["life"], threshold)
        out.baseline_cycles += base
        if c["pull"] is None or c["pull"][0] >= base:
            out.cost_cycles += base
            continue
        stop, v = c["pull"]
        out.pulled += 1
        if v != c["label"]:
            out.wrong_unaudited += 1
        if audit is None:
            ok = True
        else:
            lo, hi = audit(c, stop)
            ok = (v == 1 and lo >= threshold) or (v == 0 and hi < threshold)
        if ok:
            out.confirmed += 1
            out.cost_cycles += stop
            if v != c["label"]:
                out.wrong_final += 1
                out.wrong_ids.append(c["id"])
        else:
            out.reversals += 1
            out.cost_cycles += base
    return out
