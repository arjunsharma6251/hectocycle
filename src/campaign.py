"""Offline replay of a protocol-selection campaign (docs/closed-loop-study.md).

A campaign spends cycler time testing cells under candidate protocols ("arms")
and recommends the protocol it believes lives longest. Each arm is a list of
real replicate cells, each carrying its true log10 life and the early
predictor's log10 life at cycle 100. Testing an arm draws one of its
replicates (without replacement until exhausted, then with replacement) and
observes either the true life (run to failure, costs its life in cycles) or
the early prediction (costs 100 cycles).

Strategies fill `channels` cells per round after an opening round of one
cell per arm: round-robin ("grid") or batch Gaussian Thompson sampling
("ts") with known observation noise.
"""

from dataclasses import dataclass

import numpy as np

EARLY_COST = 100


@dataclass
class Replicate:
    true_log: float
    pred_log: float
    life: float


def _observe(rep, early):
    return (rep.pred_log, EARLY_COST) if early else (rep.true_log, rep.life)


class _Arms:
    def __init__(self, arms, rng):
        self.arms, self.rng = arms, rng
        self.order = [list(rng.permutation(len(a))) for a in arms]

    def draw(self, k):
        if self.order[k]:
            return self.arms[k][self.order[k].pop()]
        return self.arms[k][self.rng.integers(len(self.arms[k]))]


def run_campaign(arms, early, strategy, budget, rng, channels=8, sigma=0.1,
                 prior_mean=np.log10(800), prior_sd=0.3):
    """Trace [(cumulative cycles, recommended arm)] after each round.

    Stops at the first round that brings spend to or past `budget`.
    """
    pool = _Arms(arms, rng)
    K = len(arms)
    sums, counts = np.zeros(K), np.zeros(K)
    spent, trace = 0.0, []

    def run(ks):
        nonlocal spent
        for k in ks:
            y, c = _observe(pool.draw(k), early)
            sums[k] += y
            counts[k] += 1
            spent += c

    def recommend():
        return int(np.argmax(np.where(counts > 0, sums / np.maximum(counts, 1), -np.inf)))

    run(range(K))  # opening round: every arm once
    trace.append((spent, recommend()))
    rr = 0
    while spent < budget:
        if strategy == "grid":
            ks = [(rr + i) % K for i in range(channels)]
            rr = (rr + channels) % K
        elif strategy == "ts":
            prec = 1 / prior_sd ** 2 + counts / sigma ** 2
            mean = (prior_mean / prior_sd ** 2 + sums / sigma ** 2) / prec
            draws = rng.normal(mean, 1 / np.sqrt(prec), size=(channels, K))
            ks = list(np.argmax(draws, axis=1))
        else:
            raise ValueError(strategy)
        run(ks)
        trace.append((spent, recommend()))
    return trace


def at_budgets(trace, budgets):
    """Recommended arm at each budget (-1 before the opening round finishes)."""
    spent = np.array([s for s, _ in trace])
    rec = np.array([r for _, r in trace])
    idx = np.searchsorted(spent, budgets, side="right") - 1
    return np.where(idx >= 0, rec[np.clip(idx, 0, None)], -1)


def first_budget_reaching(budgets, frac, level=0.95):
    """Smallest budget from which `frac` stays >= level; None if never."""
    ok = np.asarray(frac) >= level
    for i in range(len(ok)):
        if ok[i:].all():
            return float(budgets[i])
    return None
