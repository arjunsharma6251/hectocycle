import numpy as np

from src.transfer import DQ_FEATURES, dq_features_from_cycles, dq_stats


def _cycle(scale, n=400):
    """One charge half then one discharge half; Q(V) shrinks with `scale`."""
    v_dis = np.linspace(3.5, 2.0, n)
    q_dis = scale * (3.5 - v_dis) / 1.5 * 1.1
    v_chg = np.linspace(2.0, 3.6, n)
    return {
        "current_in_A": np.r_[np.full(n, 4.4), np.full(n, -4.4)],
        "voltage_in_V": np.r_[v_chg, v_dis],
        "discharge_capacity_in_Ah": np.r_[np.zeros(n), q_dis],
    }


def test_features_match_direct_computation():
    cycles = {10: _cycle(1.0), 100: _cycle(0.98)}
    f = dq_features_from_cycles(cycles)
    assert list(f) == DQ_FEATURES
    # on the overlap grid DeltaQ is linear in V: recompute it directly
    grid = np.linspace(2.01, 3.49, 1000)
    dq = -0.02 * (3.5 - grid) / 1.5 * 1.1
    for k, v in dq_stats(dq).items():
        assert abs(f[k] - v) < 1e-6


def test_missing_or_empty_cycles_return_none():
    assert dq_features_from_cycles({10: _cycle(1.0)}) is None
    empty = {"current_in_A": np.zeros(5), "voltage_in_V": np.ones(5),
             "discharge_capacity_in_Ah": np.zeros(5)}
    assert dq_features_from_cycles({10: _cycle(1.0), 100: empty}) is None
