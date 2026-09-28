"""Do features computed from raw cycler curves match the Qdlin features the model trained on?

The production model was trained on Severson's pre-interpolated Qdlin arrays
(src/features.py). Every real file scored by TRY IT, scripts/score_files.py or
the batch-recalibration runner goes through the raw-curve featurizer instead
(src/transfer.py dq_features_from_cycles). The Severson .mat files also carry
each cycle's raw current, voltage and discharge capacity, so both paths can be
computed on the same 124 cells. Bars (from docs/out-of-sample-study.md §0):
median |difference| < 0.05 on each log feature and Spearman rho > 0.98.
Writes figures/raw_vs_qdlin.json.

    .venv/bin/python scripts/raw_vs_qdlin.py
"""

import json
import os
import sys

import h5py
import numpy as np
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import BATCH_FILES, build_dataset  # noqa: E402
from src.features import delta_q_features  # noqa: E402
from src.split import canonical_split  # noqa: E402
from src.transfer import DQ_FEATURES, dq_features_from_cycles  # noqa: E402

CYCLES = (10, 100)
BARS = {"median_abs": 0.05, "spearman": 0.98}


def raw_cycles(mat_path, prefix, keys):
    out = {}
    with h5py.File(mat_path, "r") as f:
        batch = f["batch"]
        for i in range(batch["cycles"].shape[0]):
            k = f"{prefix}c{i}"
            if k not in keys:
                continue
            grp = f[batch["cycles"][i, 0]]
            cm = {}
            for j in CYCLES:
                get = lambda name: np.hstack(f[grp[name][j, 0]][()]).astype(float)
                cm[j] = {"current_in_A": get("I") * 1.1,  # stored in C-rate units (1.1 Ah cell)
                         "voltage_in_V": get("V"), "discharge_capacity_in_Ah": get("Qd")}
            out[k] = cm
    return out


def main():
    data = os.path.join(ROOT, "data")
    sev = build_dataset(data, verbose=False)
    keys = set(sev)
    raw = {}
    for prefix, fname in BATCH_FILES.items():
        raw.update(raw_cycles(os.path.join(data, fname), prefix, keys))
    rows = []
    for k in sev:
        q = delta_q_features(sev[k])
        r = dq_features_from_cycles(raw[k]) if k in raw else None
        rows.append((k, q, r))
    ok = [(k, q, r) for k, q, r in rows if r is not None]
    res = {"n": len(rows), "n_raw_ok": len(ok), "features": {}}
    for f in DQ_FEATURES:
        a = np.array([q[f] for _, q, _ in ok])
        b = np.array([r[f] for _, _, r in ok])
        d = b - a
        res["features"][f] = {"median_abs": float(np.median(np.abs(d))), "median_signed": float(np.median(d)),
                              "p90_abs": float(np.percentile(np.abs(d), 90)),
                              "spearman": float(spearmanr(a, b)[0])}
    res["pass"] = all(v["median_abs"] < BARS["median_abs"] and v["spearman"] > BARS["spearman"]
                      for v in res["features"].values())
    train, primary, secondary = canonical_split(sev.keys())
    res["worst"] = sorted(((k, round(r["log_var_dq"] - q["log_var_dq"], 3)) for k, q, r in ok),
                          key=lambda x: -abs(x[1]))[:8]
    with open(os.path.join(ROOT, "figures", "raw_vs_qdlin.json"), "w") as fp:
        json.dump(res, fp, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
