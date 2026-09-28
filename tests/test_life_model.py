import numpy as np

from src.life_model import JackknifePlusLife, verdict


def _data(n=41, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 3))
    logy = 2.9 - 0.3 * X[:, 0] + 0.05 * X[:, 1] + rng.normal(0, 0.08, n)
    return X, 10 ** logy


def test_interval_brackets_point_and_is_ordered():
    X, life = _data()
    m = JackknifePlusLife().fit(X, life)
    p, lo, hi = m.predict(X[:5] + 0.1)
    assert np.all(lo < hi)
    assert np.all((lo <= p) & (p <= hi))


def test_coverage_near_nominal_on_fresh_draws():
    X, life = _data(seed=1)
    m = JackknifePlusLife(alpha=0.10).fit(X, life)
    Xt, lt = _data(n=2000, seed=2)
    _, lo, hi = m.predict(Xt)
    cov = np.mean((lt >= lo) & (lt <= hi))
    assert 0.82 <= cov <= 0.98  # jackknife+ guarantees >= 1 - 2*alpha


def test_verdict_is_monotone_in_threshold():
    X, life = _data()
    m = JackknifePlusLife().fit(X, life)
    _, lo, hi = m.predict(X)
    prev = None
    for T in range(300, 2000, 25):
        v = verdict(lo, hi, T)
        if prev is not None:
            # raising the spec never turns a fail into a pass or keep-testing
            assert not np.any((prev == 0) & (v != 0))
            # and never turns keep-testing back into a pass
            assert not np.any((prev == -1) & (v == 1))
        prev = v


def test_export_reproduces_predictions():
    X, life = _data()
    m = JackknifePlusLife().fit(X, life)
    e = m.to_export()
    x = X[3] + 0.2
    mu = np.array([b[0] + np.dot(b[1:], x) for b in e["loo_beta"]])
    r = np.array(e["loo_resid"])
    lo = 10 ** np.sort(mu - r)[e["k_lo"] - 1]
    hi = 10 ** np.sort(mu + r)[e["k_hi"] - 1]
    _, lo2, hi2 = m.predict(x[None])
    assert abs(lo - lo2[0]) / lo < 1e-6 and abs(hi - hi2[0]) / hi < 1e-6
