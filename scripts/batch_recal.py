"""Run the frozen batch-recalibration study on one lot (docs/batch-recalibration-study.md).

Everything that decides the outcome is frozen below and was fixed in Phase A
on batches 1-4 before any new lot was scored. The lot can come from:

    --source matr-b4                         MATR batch 4 (reproduces Phase A; not a gate)
    --source matr-mat --paths X.mat          any MATR-format batch file; eligibility (same 4C
                                             discharge and temperature as training) is checked
                                             before any gate metric
    --source batterylife --paths HUST/*.pkl  BatteryLife pickles (the HUST rehearsal)
    --source files --paths lab/*.csv         cycler text exports, one file per cell,
                                             cycle 1 to end of life (a lab's lot)

    .venv/bin/python scripts/batch_recal.py --source files --paths lab/*.csv --name lab-lot-1

Writes figures/batch_recal_<name>.json and prints the gate.
"""

import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import build_dataset  # noqa: E402
from src.evidence import classifier_evidence  # noqa: E402
from src.features import dq_frame  # noqa: E402
from src.labels import make_labels  # noqa: E402
from src.lots import lot_from_batterylife, lot_from_files, lot_from_matr  # noqa: E402
from src.policy import CUTOFFS, _stop_confirmed  # noqa: E402
from src.recal import BatchOffsetLife, provisional_pull  # noqa: E402
from src.split import canonical_split  # noqa: E402
from src.transfer import DQ_FEATURES  # noqa: E402

# ---- frozen in Phase A (figures/batch_recal_explore_80_cap1050.json) ----
K_PILOTS = 4
AUDIT_LEVEL = 0.80
CAP_FACTOR = 1.5          # pilots stop at 1.5 x T; survivors are censored
DRAWS = 1000
SEED = 2026
CLASSIFIER_T = 700        # stage-1 pulls exist only at the spec the classifier was trained for
BARS = {"mean_wrong": 0.5, "p_le1_wrong": 0.95, "saved": 0.0, "coverage": 0.70, "refused_frac": 1 / 3,
        "min_each_side": 5}


def matr_eligibility(mat_path, lot, sev, train):
    """E1-E3 of docs/batch-recalibration-study.md §4, from raw currents and temperatures only."""
    import h5py
    currents, temps = [], []
    with h5py.File(mat_path, "r") as f:
        batch = f["batch"]
        for i in range(batch["cycles"].shape[0]):
            grp = f[batch["cycles"][i, 0]]
            if grp["I"].shape[0] <= 10:
                continue
            I = np.hstack(f[grp["I"][10, 0]][()]).astype(float)  # C-rate units
            dis = I[I < -0.5]
            if dis.size:
                currents.append(float(np.median(dis)))
            s = f[batch["summary"][i, 0]]
            tavg = np.hstack(s["Tavg"][0, :].tolist())
            if len(tavg) > 10:
                temps.append(float(tavg[10]))
    t_train = [float(sev[k]["summary"]["Tavg"][10]) for k in train]
    n_ok = sum(1 for c in lot.values() if c["feats"].get(10 if 10 in c["feats"] else 100) is not None
               and c["feats"].get(100) is not None)
    med_i, med_t = float(np.median(currents)), float(np.median(temps))
    checks = {"E1_cells_with_cycle_100": n_ok >= 20,
              "E2_discharge_4C": -4.4 <= med_i <= -3.6,
              "E3_temperature": min(t_train) - 2 <= med_t <= max(t_train) + 2}
    return checks, {"n_cells_cycle_100": n_ok, "median_discharge_C": med_i, "median_T_cycle10": med_t,
                    "train_T_range": [min(t_train), max(t_train)]}


def load_lot(args):
    if args.source == "matr-mat":
        from src.data import compute_cycle_life, load_batch
        cells = load_batch(args.paths[0], "x")
        for c in cells.values():
            qd = np.asarray(c["summary"]["QD"], float)
            reached = bool(np.any(qd[1:] < 0.88)) or (len(qd) > 1 and qd[-1] <= 0.8810)
            # a life only if the log reaches 80% (crossing, or Severson's stop-at-EOL
            # pattern of ending at 0.8801-0.8809 Ah); an early-stopped log is censored,
            # whatever cycle_life the file stores (§4 of the study)
            c["cycle_life"] = compute_cycle_life(c) if reached else float("nan")
        return lot_from_matr(cells)
    if args.source == "matr-b4":
        from src.matr_b4 import load_b4
        return lot_from_matr(load_b4(os.path.join(ROOT, "data"), verbose=False))
    if args.source == "batterylife":
        return lot_from_batterylife(args.paths, nominal_ah=args.nominal)
    return lot_from_files(args.paths, nominal_ah=args.nominal or 1.1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["matr-b4", "matr-mat", "batterylife", "files"], required=True)
    ap.add_argument("--paths", nargs="*", default=[])
    ap.add_argument("--name", required=True)
    ap.add_argument("--T", type=float, default=700)
    ap.add_argument("--nominal", type=float, default=None, help="nominal capacity, Ah (default: from file, else 1.1)")
    ap.add_argument("--minutes-per-cycle", type=float, default=45.0)
    args = ap.parse_args(argv)
    T, cap = args.T, CAP_FACTOR * args.T

    lot_all = load_lot(args)
    censored = [k for k, c in lot_all.items() if c["life"] is None]
    lot = {k: c for k, c in lot_all.items() if c["life"] is not None}
    keys = list(lot)
    life = {k: lot[k]["life"] for k in keys}
    n_pass = sum(life[k] >= T for k in keys)

    sev = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    labels, _ = make_labels(sev, threshold=CLASSIFIER_T, verbose=False, auto_adjust=False)
    train, _, _ = canonical_split(sev.keys())
    tr = {k: sev[k] for k in train}
    life_tr = [sev[k]["cycle_life"] for k in train]

    if args.source == "matr-mat":
        elig, elig_info = matr_eligibility(args.paths[0], lot_all, sev, train)
        print(json.dumps({"eligibility": elig, **elig_info}, indent=1))
        if not all(elig.values()):
            out = {"lot": args.name, "decision": "INELIGIBLE", "eligibility": elig, "eligibility_info": elig_info}
            with open(os.path.join(ROOT, "figures", f"batch_recal_{args.name}.json"), "w") as fp:
                json.dump(out, fp, indent=1)
            print("decision: INELIGIBLE (gate not run)")
            return out
    bo = {c: BatchOffsetLife().fit(dq_frame(tr, c).values, life_tr, [k[:2] for k in train]) for c in CUTOFFS}

    # refusals are about inputs, so they count over every cell, labelled or not
    evidence, viol = classifier_evidence(sev, train, labels, lot_all)
    refused_all = {k for k in lot_all if viol[k]}
    refused = refused_all & set(keys)
    use_classifier = T == CLASSIFIER_T
    pull = {}
    for k in keys:
        ev = sorted(evidence[k], key=lambda e: e["cutoff"])
        stop, v = _stop_confirmed(ev) if (use_classifier and k not in refused and len(ev) == len(CUTOFFS)) else (None, -1)
        pull[k] = None if stop is None else (stop, v)

    X = {c: {k: np.array([lot[k]["feats"][c][f] for f in DQ_FEATURES]) for k in keys if lot[k]["feats"].get(c)}
         for c in CUTOFFS}
    pool = [k for k in keys if k in X[100]]
    rng = np.random.default_rng(SEED)
    outcomes, unaudited, cover, iv_wrong, alphas = [], [], [], [], []
    for _ in range(DRAWS if len(pool) >= K_PILOTS + 1 else 0):
        pil = list(rng.choice(pool, size=K_PILOTS, replace=False))
        a = {c: bo[c].offset_from_pilots(np.array([X[c][p] for p in pil]), [life[p] for p in pil], cap=cap)
             for c in CUTOFFS if all(p in X[c] for p in pil)}
        alphas.append(a[100])

        def audit(cell, stop):
            _, lo, hi = bo[stop].predict(X[stop][cell["id"]][None], a[stop], K_PILOTS, AUDIT_LEVEL)
            return lo[0], hi[0]

        rest = [k for k in keys if k not in pil]
        cells = [{"id": k, "life": life[k], "label": int(life[k] >= T), "pull": pull[k]} for k in rest]
        pilots = [{"id": p, "life": life[p]} for p in pil]
        outcomes.append(provisional_pull(cells, pilots, audit, T, args.minutes_per_cycle, pilot_cap=cap))
        unaudited.append(provisional_pull(cells, [], None, T, args.minutes_per_cycle))
        scored = [k for k in rest if k in X[100] and k not in refused]
        if scored:
            _, lo, hi = bo[100].predict(np.array([X[100][k] for k in scored]), a[100], K_PILOTS, AUDIT_LEVEL)
            L = np.array([life[k] for k in scored])
            cover.append(float(np.mean((L >= lo) & (L <= hi))))
            called = (lo >= T) | (hi < T)
            iv_wrong.append(int(np.sum(called & ((lo >= T) != (L >= T)))))

    wrong = np.array([o.wrong_final for o in outcomes])
    mean = lambda xs: float(np.mean(xs)) if len(xs) else None
    m = {
        "n_files": len(lot_all), "n_labelled": len(keys), "censored_logs": len(censored), "n_pass": n_pass,
        "refused": len(refused_all), "refused_frac": len(refused_all) / max(len(lot_all), 1),
        "mean_wrong": mean(wrong), "p_le1_wrong": mean(wrong <= 1),
        "mean_wrong_unaudited": mean([o.wrong_final for o in unaudited]),
        "reversals": mean([o.reversals for o in outcomes]),
        "pulled": mean([o.pulled for o in outcomes]),
        "saved": mean([o.saved_frac for o in outcomes]),
        "saved_unaudited": mean([o.saved_frac for o in unaudited]),
        "final_day_median": float(np.median([o.final_day for o in outcomes])) if outcomes else None,
        "coverage": mean(cover),
        "interval_wrong_mean": mean(iv_wrong),
        "alpha_median": float(np.median(alphas)) if alphas else None,
        "train_alphas": {b: float(v) for b, v in bo[100].alpha_.items()},
        "qd2_median": float(np.median([c["qd2"] for c in lot.values() if c["qd2"]])) if any(
            c["qd2"] for c in lot.values()) else None,
    }
    informative = min(n_pass, len(keys) - n_pass) >= BARS["min_each_side"] and bool(outcomes)
    checks = {
        "coverage": m["coverage"] is not None and m["coverage"] >= BARS["coverage"],
        "refused": m["refused_frac"] <= BARS["refused_frac"],
    }
    if use_classifier and outcomes:
        checks.update({"wrong": m["mean_wrong"] <= BARS["mean_wrong"] and m["p_le1_wrong"] >= BARS["p_le1_wrong"],
                       "saved": m["saved"] > BARS["saved"]})
    if not informative:
        decision = ("UNINFORMATIVE: fewer than 5 labelled cells on one side of T, or too few labelled cells "
                    "with cycle-100 data to draw pilots")
    elif not use_classifier:
        decision = "REHEARSAL PASS" if all(checks.values()) else "REHEARSAL FAIL"
    elif checks["wrong"] and checks["coverage"] and checks["refused"]:
        decision = "BUILD" if checks["saved"] else "RESCOPE (safe, but pays nothing on this lot)"
    else:
        decision = "KILL"

    out = {"lot": args.name, "source": args.source, "T": T, "pilot_cap": cap,
           "frozen": {"k": K_PILOTS, "audit_level": AUDIT_LEVEL, "cap_factor": CAP_FACTOR, "draws": DRAWS,
                      "seed": SEED, "bars": BARS},
           "mode": "provisional pull" if use_classifier else "life-model only (no stage-1 classifier at this T)",
           "metrics": m, "checks": checks, "informative": informative, "decision": decision}
    # the cycle-2 capacity "batch warning" was dropped (docs/batch-warning-study.md): qd2 stays in
    # metrics as a description only
    path = os.path.join(ROOT, "figures", f"batch_recal_{args.name}.json")
    with open(path, "w") as fp:
        json.dump(out, fp, indent=1)
    print(json.dumps({k: out[k] for k in ("lot", "T", "mode", "checks", "decision")}, indent=1))
    print(json.dumps(m, indent=1))
    return out


if __name__ == "__main__":
    main()
