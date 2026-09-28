"""Phase A (exploratory, disclosed as adaptive): tune the pilot-cell audit on
batches 1-4 before its gate is pre-registered (docs/batch-recalibration-study.md).

Each held-out batch is treated as a new lot: k pilots drawn at random run to
end of life, the rest go through provisional pull (stage-1 pulls by the
shipped classifier's confirmed-call rule, audited when the pilots die).
Batch 4 has been seen before (docs/out-of-sample-study.md), so nothing here is
confirmatory. Writes figures/batch_recal_explore.json.

    .venv/bin/python scripts/batch_recal_explore.py
"""

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import build_dataset  # noqa: E402
from src.features import dq_frame  # noqa: E402
from src.life_model import JackknifePlusLife  # noqa: E402
from src.matr_b4 import load_b4  # noqa: E402
from src.policy import CUTOFFS, _stop_confirmed  # noqa: E402
from src.recal import BatchOffsetLife, provisional_pull  # noqa: E402
from src.split import canonical_split  # noqa: E402

T = 700
KS = [2, 3, 4, 6, 8]
DRAWS = 500
LEVEL = float(os.environ.get("AUDIT_LEVEL", 0.90))  # swept in Phase A
CAP = float(os.environ["PILOT_CAP"]) if os.environ.get("PILOT_CAP") else None  # pilot cycle cap


def load():
    sev = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    b4 = load_b4(os.path.join(ROOT, "data"), verbose=False)
    train, primary, secondary = canonical_split(sev.keys())
    bundle = json.load(open(os.path.join(ROOT, "app", "static", "cockpit_data.json")))
    ev = {c["id"]: c["evidence"] for c in bundle["qual"]["cells"] if c.get("evidence")}
    oos = json.load(open(os.path.join(ROOT, "figures", "out_of_sample.json")))
    for c in oos["cells"]:
        ev[c["id"]] = None if c["violations"] else c["evidence"]  # refused: never pulled
    mins = json.load(open(os.path.join(ROOT, "data", "cycle_minutes.json")))
    mins_b4 = json.load(open(os.path.join(ROOT, "data", "cycle_minutes_b4.json")))
    mpc = {b: float(np.median([v for k, v in mins.items() if k.startswith(b)])) for b in ("b1", "b2", "b3")}
    mpc["b4"] = float(np.median(list(mins_b4.values())))
    lots = {
        "b1 test": ({k: sev[k] for k in primary if k.startswith("b1")}, mpc["b1"]),
        "b2 test": ({k: sev[k] for k in primary if k.startswith("b2")}, mpc["b2"]),
        "b3": ({k: sev[k] for k in secondary}, mpc["b3"]),
        "b4": (b4, mpc["b4"]),
    }
    return sev, train, lots, ev


def main():
    sev, train, lots, ev = load()
    tr = {k: sev[k] for k in train}
    life_tr = np.array([sev[k]["cycle_life"] for k in train])
    batch_tr = [k[:2] for k in train]
    feats_tr = {c: dq_frame(tr, c) for c in CUTOFFS}
    bo = {c: BatchOffsetLife().fit(feats_tr[c].values, life_tr, batch_tr) for c in CUTOFFS}
    jk = {c: JackknifePlusLife(alpha=1 - LEVEL).fit(feats_tr[c].values, life_tr) for c in CUTOFFS}
    print("sigma_w (log10) by cutoff:", {c: round(bo[c].sigma_w_, 3) for c in CUTOFFS},
          " train intercepts @100:", {b: round(a, 3) for b, a in bo[100].alpha_.items()})

    results, desc = {}, {}
    for lot, (bd, mpc) in lots.items():
        keys = list(bd)
        F = {c: dq_frame(bd, c).loc[keys] for c in CUTOFFS}
        life = {k: float(bd[k]["cycle_life"]) for k in keys}
        pull = {}
        for k in keys:
            e = ev.get(k)
            stop, v = _stop_confirmed(sorted(e, key=lambda x: x["cutoff"])) if e else (None, -1)
            pull[k] = None if stop is None else (stop, v)
        # log-residual of each cell under each model/cutoff (for pilot offsets)
        jk_pt = {c: dict(zip(keys, jk[c].predict(F[c].values)[0])) for c in CUTOFFS}
        jk_iv = {c: dict(zip(keys, zip(*jk[c].predict(F[c].values)[1:]))) for c in CUTOFFS}
        xb = {c: dict(zip(keys, F[c].values @ bo[c].beta_)) for c in CUTOFFS}
        true_alpha = {c: float(np.mean([np.log10(life[k]) - xb[c][k] for k in keys])) for c in CUTOFFS}

        rng = np.random.default_rng(2026)
        res = {}
        for k_p in KS:
            acc = {m: [] for m in ("none", "jk-shift", "batch-offset", "oracle")}
            for _ in range(DRAWS):
                pil = list(rng.choice(keys, size=k_p, replace=False))
                rest = [x for x in keys if x not in pil]
                cells = [{"id": x, "life": life[x], "label": int(life[x] >= T), "pull": pull[x]} for x in rest]
                pilots = [{"id": x, "life": life[x]} for x in pil]
                sw = {c: bo[c].sigma_w_ / np.sqrt(k_p) for c in CUTOFFS}
                d_jk = {c: np.mean([np.log10(life[x]) - np.log10(jk_pt[c][x]) for x in pil]) for c in CUTOFFS}
                a_bo = {c: bo[c].offset_from_pilots(F[c].loc[pil].values, [life[x] for x in pil], cap=CAP)
                        for c in CUTOFFS}

                def audit_jk(cell, stop):
                    lo, hi = jk_iv[stop][cell["id"]]
                    z = 1.645 * sw[stop]
                    return lo * 10 ** (d_jk[stop] - z), hi * 10 ** (d_jk[stop] + z)

                def audit_bo(cell, stop, alpha=None, kk=k_p):
                    x = F[stop].loc[[cell["id"]]].values
                    _, lo, hi = bo[stop].predict(x, a_bo[stop] if alpha is None else alpha, kk, LEVEL)
                    return lo[0], hi[0]

                def audit_or(cell, stop):
                    return audit_bo(cell, stop, alpha=true_alpha[stop], kk=1e9)

                for m, fn in (("none", None), ("jk-shift", audit_jk), ("batch-offset", audit_bo), ("oracle", audit_or)):
                    acc[m].append(provisional_pull(cells, pilots, fn, T, mpc, pilot_cap=CAP))
            res[k_p] = {m: {"wrong_final": float(np.mean([o.wrong_final for o in v])),
                            "p_any_wrong": float(np.mean([o.wrong_final > 0 for o in v])),
                            "reversals": float(np.mean([o.reversals for o in v])),
                            "pulled": float(np.mean([o.pulled for o in v])),
                            "saved_frac": float(np.mean([o.saved_frac for o in v])),
                            "final_day": float(np.median([o.final_day for o in v]))}
                        for m, v in acc.items()}
        results[lot] = res

        # descriptive: batch-offset intervals as a predictor in their own right (k=4, cutoff 100)
        cov, width = [], []
        for _ in range(DRAWS):
            pil = list(rng.choice(keys, size=4, replace=False))
            rest = [x for x in keys if x not in pil]
            a = bo[100].offset_from_pilots(F[100].loc[pil].values, [life[x] for x in pil])
            _, lo, hi = bo[100].predict(F[100].loc[rest].values, a, 4, LEVEL)
            L = np.array([life[x] for x in rest])
            cov.append(np.mean((L >= lo) & (L <= hi)))
            width.append(np.median(hi - lo))
        _, jlo, jhi = jk[100].predict(F[100].values)
        L = np.array([life[x] for x in keys])
        desc[lot] = {"n": len(keys), "true_offset_100": true_alpha[100], "bo_cov_k4": float(np.mean(cov)),
                     "bo_width_k4": float(np.median(width)),
                     "jk_cov": float(np.mean((L >= jlo) & (L <= jhi))), "jk_width": float(np.median(jhi - jlo))}

        print(f"\n== {lot}  (n={len(keys)}, batch intercept {true_alpha[100]:.3f}, {mpc:.1f} min/cycle, audit level {LEVEL})")
        print(f"   intervals @100: jackknife+ cov {desc[lot]['jk_cov']:.2f} width {desc[lot]['jk_width']:.0f}"
              f" | batch-offset k=4 cov {desc[lot]['bo_cov_k4']:.2f} width {desc[lot]['bo_width_k4']:.0f}")
        for k_p in KS:
            row = "   k=%d " % k_p
            for m in ("none", "jk-shift", "batch-offset", "oracle"):
                r = res[k_p][m]
                row += f"| {m}: wrong {r['wrong_final']:.2f} rev {r['reversals']:.1f} saved {r['saved_frac']:.2f} "
            print(row + f"| day {res[k_p]['none']['final_day']:.0f}")

    tag = ("" if LEVEL == 0.90 else f"_{int(LEVEL * 100)}") + ("" if CAP is None else f"_cap{int(CAP)}")
    with open(os.path.join(ROOT, "figures", f"batch_recal_explore{tag}.json"), "w") as fp:
        json.dump({"threshold": T, "ks": KS, "draws": DRAWS, "level": LEVEL,
                   "sigma_w": {c: bo[c].sigma_w_ for c in CUTOFFS},
                   "results": results, "descriptive": desc}, fp, indent=1)


if __name__ == "__main__":
    main()
