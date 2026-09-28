"""Cross-lab transfer support for the early qualification call.

Two pieces, both born from the OOD finding in docs/early-call-study.md (transfer section):
- DQ_FEATURES: the protocol-invariant feature subset (within-cell DeltaQ(V)
  statistics). Protocol covariates (charge time, IR) fail catastrophically
  across labs; these transfer.
- Envelope guard: a verdict is only emitted when every input feature lies
  inside the training envelope (+/- margin). Outside it, the honest output is
  OUT-OF-ENVELOPE, not a confident number.

Also provides the Severson-style DeltaQ(V) featurizer for raw per-cycle
curves (BatteryLife pickles, cycler files) rather than Qdlin arrays.
"""

import pickle

import numpy as np

from .features import EPS

DQ_FEATURES = ["log_var_dq", "log_min_dq", "log_mean_dq"]
ENVELOPE_MARGIN = 0.10  # fraction of the training span allowed beyond min/max


def feature_envelope(train_df, margin=ENVELOPE_MARGIN):
    """{feature: (lo, hi)} from the training frame, widened by `margin`."""
    env = {}
    for col in train_df.columns:
        lo, hi = float(train_df[col].min()), float(train_df[col].max())
        pad = (hi - lo) * margin
        env[col] = (lo - pad, hi + pad)
    return env


def envelope_violations(row, env):
    """Feature names in `row` that fall outside the envelope."""
    return [k for k, (lo, hi) in env.items() if k in row and not (lo <= row[k] <= hi)]


def _discharge_qv(cyc, deadband=0.05, min_pts=20):
    """Discharge branch of one cycle as (V strictly ascending, Q).

    `cyc` uses the BatteryLife keys (current_in_A, voltage_in_V,
    discharge_capacity_in_Ah); src/ingest.py normalises cycler files to them.
    """
    I = np.asarray(cyc["current_in_A"], float)
    V = np.asarray(cyc["voltage_in_V"], float)
    qd = np.asarray(cyc["discharge_capacity_in_Ah"], float)
    m = (I < -deadband) & (qd >= 0)
    if m.sum() < min_pts:
        return None
    # repeated voltage readings (cycler resolution) collapse to their mean
    # capacity, so interpolation is well defined and order-independent
    v, inv = np.unique(V[m], return_inverse=True)
    q = np.bincount(inv, weights=qd[m]) / np.bincount(inv)
    if len(v) < 2:
        return None
    return v, q


def dq_stats(dq):
    """The three log-statistics of a DeltaQ(V) curve (DQ_FEATURES order)."""
    return {
        "log_var_dq": float(np.log10(np.var(dq) + EPS)),
        "log_min_dq": float(np.log10(abs(dq.min()) + EPS)),
        "log_mean_dq": float(np.log10(abs(dq.mean()) + EPS)),
    }


def dq_features_from_cycles(cycles, cyc_late=100, cyc_early=10, n_grid=1000):
    """Severson-style DeltaQ(V) statistics from raw per-cycle curves.

    `cycles` maps cycle number -> {current_in_A, voltage_in_V,
    discharge_capacity_in_Ah}. Q(V) at the early and late cycles is
    interpolated onto a shared voltage grid spanning the overlap of the two
    discharge branches. Returns None if either cycle is missing or has no
    usable discharge segment.
    """
    if cyc_early not in cycles or cyc_late not in cycles:
        return None
    a, b = _discharge_qv(cycles[cyc_early]), _discharge_qv(cycles[cyc_late])
    if a is None or b is None:
        return None
    v_lo = max(a[0][0], b[0][0]) + 0.01
    v_hi = min(a[0][-1], b[0][-1]) - 0.01
    if v_hi <= v_lo:
        return None
    grid = np.linspace(v_lo, v_hi, n_grid)
    return dq_stats(np.interp(grid, *b) - np.interp(grid, *a))


def snl_dq_features(pkl_path, cyc_late=100, cyc_early=10, n_grid=1000):
    """dq_features_from_cycles on a BatteryLife-format cell pickle."""
    d = pickle.load(open(pkl_path, "rb"))
    cd = {c["cycle_number"]: c for c in d["cycle_data"]}
    return dq_features_from_cycles(cd, cyc_late, cyc_early, n_grid)
