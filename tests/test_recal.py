import numpy as np

from src.recal import BatchOffsetLife, provisional_pull


def _batches(seed=0, offsets=(0.05, -0.05), n=20):
    rng = np.random.default_rng(seed)
    X, life, batch = [], [], []
    for b, a in zip(("b1", "b2"), offsets):
        x = rng.normal(size=(n, 3))
        y = 2.9 + a - 0.3 * x[:, 0] + rng.normal(0, 0.04, n)
        X.append(x); life.append(10 ** y); batch += [b] * n
    return np.vstack(X), np.concatenate(life), batch


def test_recovers_shared_slope_and_batch_intercepts():
    X, life, batch = _batches()
    m = BatchOffsetLife().fit(X, life, batch)
    assert abs(m.beta_[0] + 0.3) < 0.03
    assert abs((m.alpha_["b1"] - m.alpha_["b2"]) - 0.10) < 0.04
    assert 0.03 < m.sigma_w_ < 0.06


def test_pilots_pin_a_shifted_batch():
    X, life, batch = _batches()
    m = BatchOffsetLife().fit(X, life, batch)
    rng = np.random.default_rng(5)
    Xn = rng.normal(size=(200, 3))
    ln = 10 ** (2.9 - 0.12 - 0.3 * Xn[:, 0] + rng.normal(0, 0.04, 200))  # silent -0.12 shift
    a = m.offset_from_pilots(Xn[:4], ln[:4])
    assert abs(a - (2.9 - 0.12)) < 0.08
    _, lo, hi = m.predict(Xn[4:], a, k=4)
    cov = np.mean((ln[4:] >= lo) & (ln[4:] <= hi))
    assert cov > 0.8


def test_provisional_pull_accounting():
    cells = [
        {"id": "a", "life": 900, "label": 1, "pull": (60, 1)},   # right, audit agrees
        {"id": "b", "life": 650, "label": 0, "pull": (60, 1)},   # wrong pass, audit catches
        {"id": "c", "life": 640, "label": 0, "pull": (60, 1)},   # wrong pass, audit misses
        {"id": "d", "life": 800, "label": 1, "pull": None},      # never pulled
    ]
    audits = {"a": (750, 1100), "b": (500, 800), "c": (710, 900)}
    out = provisional_pull(cells, [{"id": "p", "life": 800}], lambda c, s: audits[c["id"]], 700, 60)
    assert (out.pulled, out.confirmed, out.reversals) == (3, 2, 1)
    assert out.wrong_unaudited == 2 and out.wrong_final == 1 and out.wrong_ids == ["c"]
    # cost: pilot 800 + a 60 + b resumed 650 + c 60 + d 700 ; baseline: 700+700+650+640+700
    assert out.cost_cycles == 800 + 60 + 650 + 60 + 700
    assert out.baseline_cycles == 700 + 700 + 650 + 640 + 700
    assert out.final_day == 800 * 60 / 1440
    unaudited = provisional_pull(cells, [], None, 700, 60)
    assert unaudited.reversals == 0 and unaudited.wrong_final == 2


def test_censored_pilots_still_pin_the_offset():
    X, life, batch = _batches()
    m = BatchOffsetLife().fit(X, life, batch)
    rng = np.random.default_rng(9)
    Xn = rng.normal(size=(8, 3))
    ln = 10 ** (2.9 - 0.12 - 0.3 * Xn[:, 0] + rng.normal(0, 0.04, 8))
    full = m.offset_from_pilots(Xn, ln)
    cap = float(np.median(ln))  # half the pilots still alive at the cap
    capped = m.offset_from_pilots(Xn, np.minimum(ln, cap), cap=cap)
    naive = float(np.mean(np.log10(np.minimum(ln, cap)) - Xn @ m.beta_))
    assert abs(capped - full) < abs(naive - full)  # censoring beats treating the cap as death


def test_pilot_cap_limits_cost_and_verdict_day():
    out = provisional_pull([], [{"id": "p", "life": 2000}], None, 700, 60, pilot_cap=1050)
    assert out.cost_cycles == 1050 and out.final_day == 1050 * 60 / 1440
