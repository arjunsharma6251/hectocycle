import numpy as np

from src.campaign import EARLY_COST, Replicate, at_budgets, first_budget_reaching, run_campaign


def _arms(noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    means = [2.7, 2.9, 3.0]  # arm 2 lives longest
    return [[Replicate(m + rng.normal(0, noise), m + rng.normal(0, noise), 10 ** m) for _ in range(5)]
            for m in means]


def test_opening_round_observes_every_arm_and_costs_add_up():
    tr = run_campaign(_arms(), early=True, strategy="grid", budget=0, rng=np.random.default_rng(0))
    assert tr == [(3 * EARLY_COST, 2)]
    tr = run_campaign(_arms(), early=False, strategy="grid", budget=0, rng=np.random.default_rng(0))
    assert tr[0][0] == sum(10 ** m for m in (2.7, 2.9, 3.0))


def test_thompson_concentrates_on_the_best_arm():
    arms = _arms(noise=0.05)
    rng = np.random.default_rng(1)
    recs = [run_campaign(arms, True, "ts", 4000, rng, channels=4, sigma=0.05)[-1][1] for _ in range(50)]
    assert np.mean(np.array(recs) == 2) > 0.9


def test_replicates_drawn_without_replacement_first():
    arms = [[Replicate(i, i, 1) for i in range(5)]]
    tr = run_campaign(arms, True, "grid", 4 * EARLY_COST, np.random.default_rng(3), channels=4)
    # opening (1 cell) + one round of 4 = all five distinct replicates, mean = 2
    assert tr[-1][0] == 5 * EARLY_COST


def test_budget_lookup_and_first_crossing():
    trace = [(300, 1), (700, 2), (1100, 2)]
    assert list(at_budgets(trace, np.array([100, 300, 800, 5000]))) == [-1, 1, 2, 2]
    b = np.array([1, 2, 3, 4])
    assert first_budget_reaching(b, [0.9, 0.96, 0.94, 0.97]) == 4
    assert first_budget_reaching(b, [0.1, 0.2, 0.3, 0.4]) is None
