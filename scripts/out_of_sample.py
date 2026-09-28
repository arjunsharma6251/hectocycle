"""Score MATR batch 4 against the pre-registered gate (docs/out-of-sample-study.md §0).

The model is the production cockpit model, rebuilt exactly as
scripts/build_bundle.py builds it: DeltaQ(V)-only EarlyVerdictModel + cross
Venn-ABERS, trained on the 41 Severson training cells at T = 700. Nothing is
refit on b4. Writes figures/out_of_sample.json and figures/out_of_sample.png.

    .venv/bin/python scripts/out_of_sample.py
"""

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.calibration import abstain_call, cvap_predict  # noqa: E402
from src.data import build_dataset  # noqa: E402
from src.features import dq_frame, featurize  # noqa: E402
from src.gate import expected_calibration_error  # noqa: E402
from src.labels import make_labels  # noqa: E402
from src.matr_b4 import batterylife_labels, load_b4  # noqa: E402
from src.model import EarlyVerdictModel  # noqa: E402
from src.policy import CUTOFFS, simulate  # noqa: E402
from src.split import canonical_split  # noqa: E402
from src.transfer import DQ_FEATURES, envelope_violations, feature_envelope  # noqa: E402

T = 700
BARS = {"balanced_acc": 0.85, "ece": 0.10, "acc_on_called": 0.90,
        "policy_wrong": 1, "refused": 15}


def balanced_accuracy(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    return float(np.mean([np.mean(yhat[y == c] == c) for c in (0, 1) if (y == c).any()]))


def main():
    data = os.path.join(ROOT, "data")
    sev = build_dataset(data, verbose=False)
    labels, _ = make_labels(sev, threshold=T, verbose=False)
    train, _, _ = canonical_split(sev.keys())
    y_tr = np.array([labels[k] for k in train])

    b4 = load_b4(data, verbose=False)
    keys = list(b4)
    y = np.array([int(b4[k]["cycle_life"] >= T) for k in keys])
    life = np.array([b4[k]["cycle_life"] for k in keys])

    # label cross-check against BatteryLife (their EOL index is ours - 1)
    bl = batterylife_labels(data)
    disagree = {k: (b4[k]["cycle_life"], bl[k]) for k in keys
                if k in bl and abs(b4[k]["cycle_life"] - 1 - bl[k]) > 5}

    # production model @ cutoff 100 + envelope
    f_sev = featurize(sev, cutoff=100)[DQ_FEATURES]
    f_b4 = dq_frame(b4, 100)
    X_tr = f_sev.loc[train].values
    env = feature_envelope(f_sev.loc[train])
    model = EarlyVerdictModel().fit(X_tr, y_tr)
    p = model.predict_proba(f_b4.values)[:, 1]
    _, lo, hi = cvap_predict(X_tr, y_tr, f_b4.values, seed=0)
    call = abstain_call(lo, hi)
    viol = {k: envelope_violations(f_b4.loc[k].to_dict(), env) for k in keys}
    ok = np.array([not viol[k] for k in keys])

    # evidence timelines for the allocation policy (same loop as the bundle)
    evidence = {k: [] for k in keys}
    for cutoff in CUTOFFS:
        fs = featurize(sev, cutoff=cutoff)[DQ_FEATURES]
        fb = dq_frame(b4, cutoff)
        Xa = fs.loc[train].values
        pc = EarlyVerdictModel().fit(Xa, y_tr).predict_proba(fb.values)[:, 1]
        _, a, b = cvap_predict(Xa, y_tr, fb.values, seed=0)
        c = abstain_call(a, b)
        for k, pv, av, bv, cv in zip(keys, pc, a, b, c):
            evidence[k].append({"cutoff": cutoff, "p": round(float(pv), 3),
                                "lo": round(float(av), 3), "hi": round(float(bv), 3),
                                "call": int(cv)})

    yk, pk, ck = y[ok], p[ok], call[ok]
    called = ck != -1
    pol_cells = [{"id": k, "label": int(yv), "cycle_life": float(lv), "evidence": evidence[k]}
                 for k, yv, lv, o in zip(keys, y, life, ok) if o]
    pol = simulate(pol_cells, T, rule="confirmed-call")
    first = simulate(pol_cells, T, rule="first-call")

    metrics = {
        "n": len(keys), "n_pass": int(y.sum()), "refused": int((~ok).sum()),
        "balanced_acc": balanced_accuracy(yk, (pk > 0.5).astype(int)),
        "ece": float(expected_calibration_error(yk, pk)),
        "called_frac": float(called.mean()),
        "acc_on_called": float(np.mean(ck[called] == yk[called])) if called.any() else None,
        "policy_wrong": len(pol.wrong),
    }
    checks = {
        "balanced_acc": metrics["balanced_acc"] >= BARS["balanced_acc"],
        "ece": metrics["ece"] <= BARS["ece"],
        "acc_on_called": metrics["acc_on_called"] is not None and metrics["acc_on_called"] >= BARS["acc_on_called"],
        "policy_wrong": metrics["policy_wrong"] <= BARS["policy_wrong"],
        "refused": metrics["refused"] <= BARS["refused"],
    }
    if all(checks.values()):
        decision = "BUILD"
    elif checks["acc_on_called"] and checks["policy_wrong"] and checks["refused"]:
        decision = "RESCOPE"
    else:
        decision = "KILL"

    # descriptive: callable curve, bias, per-protocol
    curve = []
    for i, cutoff in enumerate(CUTOFFS):
        c = np.array([evidence[k][i]["call"] for k in keys])[ok]
        m = c != -1
        curve.append({"cutoff": cutoff, "called_frac": round(float(m.mean()), 3),
                      "acc_on_called": round(float(np.mean(c[m] == yk[m])), 3) if m.any() else None})
    per_protocol = {}
    for k, pv, yv, cv, o in zip(keys, p, y, call, ok):
        pr = per_protocol.setdefault(b4[k]["charge_policy"], {"n": 0, "true_pass": 0, "mean_p": 0.0,
                                                              "called_wrong": 0, "lives": []})
        pr["n"] += 1
        pr["true_pass"] += int(yv)
        pr["mean_p"] += float(pv)
        pr["lives"].append(int(b4[k]["cycle_life"]))
        pr["called_wrong"] += int(o and cv != -1 and cv != yv)
    for pr in per_protocol.values():
        pr["mean_p"] = round(pr["mean_p"] / pr["n"], 3)

    out = {
        "threshold": T, "bars": BARS, "metrics": metrics, "checks": checks, "decision": decision,
        "label_disagreements_vs_batterylife": disagree,
        "mean_p_pass": float(p[ok].mean()), "true_pass_rate": float(y[ok].mean()),
        "severson_train_pass_rate": float(y_tr.mean()),
        "callable_curve": curve,
        "policy": {"confirmed": {**pol.summary(), "wrong_ids": [o.cell for o in pol.wrong]},
                   "first": {**first.summary(), "wrong_ids": [o.cell for o in first.wrong]}},
        "per_protocol": per_protocol,
        "cells": [{"id": k, "policy": b4[k]["charge_policy"], "cycle_life": int(b4[k]["cycle_life"]),
                   "label": int(yv), "p_pass": round(float(pv), 3), "p_lo": round(float(a), 3),
                   "p_hi": round(float(b), 3), "call": int(cv), "violations": viol[k],
                   "features": {f: round(float(f_b4.loc[k, f]), 4) for f in DQ_FEATURES},
                   "evidence": evidence[k]}
                  for k, yv, pv, a, b, cv in zip(keys, y, p, lo, hi, call)],
    }
    # diagnosis: does the DeltaQ signal still rank b4 cells, and how far is the
    # Severson DeltaQ -> life map off? (univariate Severson "variance model")
    from scipy.stats import spearmanr
    test_keys = [k for k in sev if k not in set(train)]
    lv = {"train": (f_sev.loc[train, "log_var_dq"].values, np.log10([sev[k]["cycle_life"] for k in train])),
          "severson_test": (f_sev.loc[test_keys, "log_var_dq"].values,
                            np.log10([sev[k]["cycle_life"] for k in test_keys])),
          "b4": (f_b4["log_var_dq"].values, np.log10(life))}
    w = np.polyfit(*lv["train"], 1)
    diagnosis = {}
    for name in ("severson_test", "b4"):
        x, ll = lv[name]
        resid = ll - np.polyval(w, x)
        diagnosis[name] = {"spearman_logvar_life": round(float(spearmanr(x, ll)[0]), 3),
                           "life_ratio_true_over_pred": round(float(10 ** resid.mean()), 3),
                           "mape": round(float(np.mean(np.abs(10 ** resid - 1))), 3)}
    out["diagnosis"] = diagnosis
    print("diagnosis:", diagnosis)

    os.makedirs(os.path.join(ROOT, "figures"), exist_ok=True)
    with open(os.path.join(ROOT, "figures", "out_of_sample.json"), "w") as fp:
        json.dump(out, fp, indent=1)

    print(json.dumps({k: out[k] for k in ("metrics", "checks", "decision", "mean_p_pass",
                                          "true_pass_rate", "label_disagreements_vs_batterylife")}, indent=1))
    print("callable curve:", curve)
    print("confirmed policy:", out["policy"]["confirmed"])
    print("first-call policy:", out["policy"]["first"])
    _figure(out, lv, w, sev, test_keys, f_sev, model)
    for pol_name, pr in sorted(per_protocol.items(), key=lambda kv: -np.mean(kv[1]["lives"])):
        print(f"  {pol_name:22s} mean life {np.mean(pr['lives']):6.0f}  pass {pr['true_pass']}/{pr['n']}"
              f"  mean P {pr['mean_p']:.2f}  wrong calls {pr['called_wrong']}")


def _figure(out, lv, w, sev, test_keys, f_sev, model):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    p_sev = model.predict_proba(f_sev.loc[test_keys].values)[:, 1]
    life_sev = [sev[k]["cycle_life"] for k in test_keys]
    ax.scatter(life_sev, p_sev, s=16, color="#9a9a9a", label="Severson test (in-sample batches)")
    b4c = [c for c in out["cells"] if not c["violations"]]
    ax.scatter([c["cycle_life"] for c in b4c], [c["p_pass"] for c in b4c], s=22, color="#b0653a",
               label="batch 4 (2019, untouched)")
    ax.axvline(T, color="#444", lw=0.8, ls="--")
    ax.axhline(0.5, color="#444", lw=0.8)
    ax.set_xlabel("true cycle life")
    ax.set_ylabel("P(pass) at cycle 100")
    m = out["metrics"]
    ax.set_title(f"Batch 4: confident and wrong below T={T}\nbalanced acc {m['balanced_acc']:.2f}, "
                 f"ECE {m['ece']:.2f}, gate {out['decision']}", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right")

    for name, col in (("severson_test", "#9a9a9a"), ("b4", "#b0653a")):
        x, ll = lv[name]
        ax2.scatter(x, 10 ** ll, s=16 if name != "b4" else 22, color=col)
    xs = np.linspace(min(lv["b4"][0].min(), lv["severson_test"][0].min()),
                     max(lv["train"][0].max(), lv["severson_test"][0].max()), 50)
    ax2.plot(xs, 10 ** np.polyval(w, xs), color="#444", lw=1, label="Severson fit (train)")
    ax2.set_yscale("log")
    ax2.set_xlabel("log10 var ΔQ(V), cycles 100−10")
    ax2.set_ylabel("true cycle life")
    d = out["diagnosis"]["b4"]
    ax2.set_title(f"Ranking survives (ρ = {d['spearman_logvar_life']:.2f}); the level shifts:\n"
                  f"batch 4 lives are {1 - d['life_ratio_true_over_pred']:.0%} shorter than predicted",
                  fontsize=10, loc="left")
    ax2.legend(fontsize=8, frameon=False)
    for a in (ax, ax2):
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "out_of_sample.png"), dpi=150)


if __name__ == "__main__":
    main()
