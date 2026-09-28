"""Score the jackknife+ life model against the pre-registered spec-threshold gate
(docs/spec-threshold-study.md §0). Writes figures/spec_threshold.{json,png}.

    .venv/bin/python scripts/spec_threshold.py
"""

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import build_dataset  # noqa: E402
from src.features import dq_frame  # noqa: E402
from src.life_model import JackknifePlusLife, verdict  # noqa: E402
from src.matr_b4 import load_b4  # noqa: E402
from src.policy import CUTOFFS, simulate  # noqa: E402
from src.split import canonical_split  # noqa: E402
from src.transfer import envelope_violations, feature_envelope  # noqa: E402

GRID = [500, 600, 700, 800, 900, 1000]
BARS = {"coverage": 0.85, "saved_ratio_700": 0.90, "wrong_per_T": 2}
BUNDLE = os.path.join(ROOT, "app", "static", "cockpit_data.json")


def life_evidence(bd, keys, train, life_tr):
    """{key: [{cutoff, point, lo, hi}]} from a life model refit at each cutoff."""
    ev = {k: [] for k in keys}
    for cutoff in CUTOFFS:
        f_tr = dq_frame(train, cutoff)
        m = JackknifePlusLife().fit(f_tr.values, life_tr)
        f = dq_frame({k: bd[k] for k in keys}, cutoff)
        p, lo, hi = m.predict(f.values)
        for k, pv, a, b in zip(keys, p, lo, hi):
            ev[k].append({"cutoff": cutoff, "point": float(pv), "lo": float(a), "hi": float(b)})
    return ev


def policy_at(ev, lives, T, keys):
    cells = [{"id": k, "label": int(lives[k] >= T), "cycle_life": float(lives[k]),
              "evidence": [{"cutoff": e["cutoff"], "call": int(verdict(e["lo"], e["hi"], T))}
                           for e in ev[k]]} for k in keys]
    return simulate(cells, T, rule="confirmed-call")


def main():
    sev = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    train, primary, secondary = canonical_split(sev.keys())
    test = primary + secondary
    tr = {k: sev[k] for k in train}
    life_tr = np.array([sev[k]["cycle_life"] for k in train])
    lives = {k: sev[k]["cycle_life"] for k in sev}

    ev = life_evidence(sev, test, tr, life_tr)
    at100 = {k: ev[k][-1] for k in test}
    cover = np.mean([at100[k]["lo"] <= lives[k] <= at100[k]["hi"] for k in test])
    width = np.median([at100[k]["hi"] - at100[k]["lo"] for k in test])

    # shipped classifier at T = 700 on the same test cells, same stopping rule
    bundle = json.load(open(BUNDLE))
    clf_cells = [{"id": c["id"], "label": c["label"], "cycle_life": c["cycle_life"], "evidence": c["evidence"]}
                 for c in bundle["qual"]["cells"] if c["split"] in ("primary", "secondary")]
    clf = simulate(clf_cells, 700, rule="confirmed-call")

    per_T = {}
    for T in GRID:
        r = policy_at(ev, lives, T, test)
        per_T[T] = {**r.summary(), "wrong_ids": [o.cell for o in r.wrong],
                    "n_pass": int(sum(lives[k] >= T for k in test))}
    r700 = per_T[700]
    checks = {
        "coverage": bool(cover >= BARS["coverage"]),
        "wrong_700": r700["wrong_calls"] <= len(clf.wrong),
        "saved_700": r700["saved_frac"] >= BARS["saved_ratio_700"] * clf.saved_frac,
        "per_T": {T: per_T[T]["wrong_calls"] <= BARS["wrong_per_T"] for T in GRID},
    }
    core = checks["coverage"] and checks["wrong_700"] and checks["saved_700"]
    if core and all(checks["per_T"].values()):
        decision = "BUILD"
    elif core:
        decision = "RESCOPE"
    else:
        decision = "KILL"
    valid_T = [T for T in GRID if checks["per_T"][T]] if core else [700]

    # descriptive: batch 4 (envelope-guarded, as the classifier)
    b4 = load_b4(os.path.join(ROOT, "data"), verbose=False)
    env = feature_envelope(dq_frame(tr, 100))
    f_b4 = dq_frame(b4, 100)
    b4_keys = [k for k in b4 if not envelope_violations(f_b4.loc[k].to_dict(), env)]
    ev_b4 = life_evidence(b4, b4_keys, tr, life_tr)
    b4_lives = {k: b4[k]["cycle_life"] for k in b4}
    b4_cover = np.mean([ev_b4[k][-1]["lo"] <= b4_lives[k] <= ev_b4[k][-1]["hi"] for k in b4_keys])
    b4_per_T = {T: policy_at(ev_b4, b4_lives, T, b4_keys).summary() for T in GRID}

    out = {"bars": BARS, "grid": GRID, "coverage": float(cover), "median_width": float(width),
           "classifier_700": {**clf.summary(), "wrong_ids": [o.cell for o in clf.wrong]},
           "per_T": per_T, "checks": checks, "decision": decision, "valid_T": valid_T,
           "b4": {"n": len(b4_keys), "coverage": float(b4_cover), "per_T": b4_per_T}}
    with open(os.path.join(ROOT, "figures", "spec_threshold.json"), "w") as fp:
        json.dump(out, fp, indent=1, default=str)

    print(f"coverage {cover:.3f} (bar {BARS['coverage']}), median width {width:.0f} cycles")
    print(f"classifier @700: {clf.summary()}")
    for T in GRID:
        r = per_T[T]
        print(f"  T={T}: called {r['called_early']}/{r['n']}  wrong {r['wrong_calls']} {r['wrong_ids']}"
              f"  saved {r['saved_frac']:.3f}   | b4 wrong {b4_per_T[T]['wrong_calls']} saved {b4_per_T[T]['saved_frac']:.3f}")
    print("checks", checks, "->", decision, "valid T", valid_T)
    print(f"b4 coverage {b4_cover:.3f} over {len(b4_keys)} cells")
    _figure(out, ev, lives, test)


def _figure(out, ev, lives, test):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    order = sorted(test, key=lambda k: lives[k])
    for i, k in enumerate(order):
        e = ev[k][-1]
        inside = e["lo"] <= lives[k] <= e["hi"]
        ax.plot([e["lo"], e["hi"]], [i, i], color="#9a9a9a" if inside else "#c0392b", lw=1.6)
        ax.plot(lives[k], i, "o", ms=3, color="#1a1a17")
    ax.set_xscale("log")
    ax.set_xlabel("cycle life (log)")
    ax.set_yticks([])
    ax.set_title(f"90% jackknife+ intervals @ cycle 100 vs true life (dots)\n"
                 f"coverage {out['coverage']:.2f}, median width {out['median_width']:.0f} cycles",
                 fontsize=10, loc="left")
    Ts = out["grid"]
    ax2.bar([str(T) for T in Ts], [out["per_T"][T]["saved_frac"] * 100 for T in Ts], color="#b0653a")
    for i, T in enumerate(Ts):
        r = out["per_T"][T]
        ax2.text(i, r["saved_frac"] * 100 + 1.5, f"{r['wrong_calls']} wrong", ha="center", fontsize=8)
    ax2.set_ylim(0, 100)
    ax2.set_xlabel("spec threshold T (cycles)")
    ax2.set_ylabel("cycler-cycles saved vs run-to-spec (%)")
    ax2.set_title(f"Confirmed-call policy at each spec (83 test cells)\ngate: {out['decision']}",
                  fontsize=10, loc="left")
    for a in (ax, ax2):
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "spec_threshold.png"), dpi=150)


if __name__ == "__main__":
    main()
