"""Score the batch-warning study (docs/batch-warning-study.md §0).

Median discharge capacity at cycle 2 per batch, for every MATR batch on disk,
against the pre-registered hypotheses H1-H3. Writes figures/batch_warning.{json,png}.

    .venv/bin/python scripts/batch_warning.py
"""

import datetime as dt
import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import load_batch  # noqa: E402

D = os.path.join(ROOT, "data")
BATCHES = {  # name: (start date, path, role)
    "b1": ("2017-05-12", f"{D}/2017-05-12_batchdata_updated_struct_errorcorrect.mat", "released"),
    "b2": ("2017-06-30", f"{D}/2017-06-30_batchdata_updated_struct_errorcorrect.mat", "released"),
    "2018-02-20": ("2018-02-20", f"{D}/matr_extra/2018-02-20_batchdata_updated_struct_errorcorrect.mat", "new"),
    "varcharge": ("2018-04-03", f"{D}/matr_extra/2018-04-03_varcharge_batchdata_updated_struct_errorcorrect.mat", "new"),
    "b3": ("2018-04-12", f"{D}/2018-04-12_batchdata_updated_struct_errorcorrect.mat", "released"),
    "CLO round 1": ("2018-08-28", f"{D}/matr_extra/2018-08-28_batchdata_updated_struct_errorcorrect.mat", "closed-loop"),
    "CLO round 2": ("2018-09-02", f"{D}/matr_extra/2018-09-02_batchdata_updated_struct_errorcorrect.mat", "closed-loop"),
    "CLO round 3": ("2018-09-06", f"{D}/matr_extra/2018-09-06_batchdata_updated_struct_errorcorrect.mat", "closed-loop"),
    "CLO round 4": ("2018-09-10", f"{D}/matr_extra/2018-09-10_batchdata_updated_struct_errorcorrect.mat", "closed-loop"),
    "b4": ("2019-01-24", f"{D}/2019-01-24_batchdata_updated_struct_errorcorrect.mat", "released"),
}
SEEN = {"b1": 1.0784, "b2": 1.0717, "b3": 1.0653, "b4": 1.0506}  # disclosed in §0
BARS = {"h1_range": 0.007, "h2_rho": -0.7}


def main():
    rows = {}
    for name, (date, path, role) in BATCHES.items():
        cells = load_batch(path, "x", max_qdlin_cycle=2)
        qd2 = [float(np.asarray(c["summary"]["QD"])[1]) for c in cells.values() if len(c["summary"]["QD"]) > 1]
        qd2 = [q for q in qd2 if np.isfinite(q) and q > 0.5]  # drop empty/aborted channels
        rows[name] = {"date": date, "role": role, "n": len(qd2),
                      "median": float(np.median(qd2)) if qd2 else None,
                      "iqr": [float(np.percentile(qd2, 25)), float(np.percentile(qd2, 75))] if qd2 else None}
        print(f"{name:12s} {date}  n={len(qd2):3d}  median {rows[name]['median']:.4f}  ({role})")

    use = {k: v for k, v in rows.items() if v["n"] >= 10}
    clo = [use[k]["median"] for k in use if use[k]["role"] == "closed-loop"]
    h1 = max(clo) - min(clo) if len(clo) == 4 else None
    days = [(dt.date.fromisoformat(v["date"]) - dt.date(2017, 1, 1)).days for v in use.values()]
    rho = float(spearmanr(days, [v["median"] for v in use.values()])[0])
    lo, hi = SEEN["b4"], SEEN["b3"]
    h3 = all(lo <= m <= hi for m in clo) if len(clo) == 4 else None
    checks = {"H1_stable": h1 is not None and h1 <= BARS["h1_range"],
              "H2_calendar_trend": rho <= BARS["h2_rho"], "H3_placement": bool(h3)}
    if not checks["H1_stable"]:
        decision = "DROP: too noisy within a campaign to serve as a warning"
    elif not checks["H2_calendar_trend"]:
        decision = "DESCRIPTIVE ONLY: stable, but does not track calendar time"
    else:
        decision = "CALENDAR-AGE PROXY: stated as such in the lot report; gates nothing"
    out = {"batches": rows, "used": list(use), "h1_range": h1, "h2_spearman": rho, "h3_all_between": h3,
           "checks": checks, "decision": decision, "bars": BARS}
    with open(os.path.join(ROOT, "figures", "batch_warning.json"), "w") as fp:
        json.dump(out, fp, indent=1)
    print(json.dumps({k: out[k] for k in ("h1_range", "h2_spearman", "h3_all_between", "checks", "decision")}, indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"released": "#1a1a17", "new": "#b0653a", "closed-loop": "#2a78d6"}
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for k, v in use.items():
        d = dt.date.fromisoformat(v["date"])
        ax.errorbar(d, v["median"], yerr=[[v["median"] - v["iqr"][0]], [v["iqr"][1] - v["median"]]],
                    fmt="o", color=col[v["role"]], capsize=3)
        ax.annotate(k, (d, v["median"]), textcoords="offset points", xytext=(6, 4), fontsize=8)
    for r, c in col.items():
        ax.plot([], [], "o", color=c, label=r)
    ax.legend(fontsize=8, frameon=False)
    ax.set_ylabel("discharge capacity at cycle 2, Ah (median, IQR)")
    ax.set_title(f"Batch warning signal vs test start date: Spearman ρ = {rho:.2f}; {decision.split(':')[0]}",
                 fontsize=10, loc="left")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "batch_warning.png"), dpi=150)


if __name__ == "__main__":
    main()
