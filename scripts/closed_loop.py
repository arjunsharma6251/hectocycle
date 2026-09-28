"""Score closed-loop protocol selection on batch 4 against the pre-registered gate
(docs/closed-loop-study.md §0). Writes figures/closed_loop.{json,png}.

    .venv/bin/python scripts/closed_loop.py
"""

import json
import os
import sys

import numpy as np
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.campaign import Replicate, at_budgets, first_budget_reaching, run_campaign  # noqa: E402
from src.data import build_dataset  # noqa: E402
from src.features import dq_frame  # noqa: E402
from src.life_model import JackknifePlusLife  # noqa: E402
from src.matr_b4 import load_b4  # noqa: E402
from src.split import canonical_split  # noqa: E402

N_CAMPAIGNS = 1000
CHANNELS = 8
MIN_PER_CYCLE = 43.8  # median measured on batch 4 (data/cycle_minutes_b4.json)
BARS = {"spearman": 0.70, "budget_ratio": 0.25, "p_top": 0.95}
STRATEGIES = {  # name: (early observation?, allocation)
    "run-to-failure grid": (False, "grid"),
    "early grid": (True, "grid"),
    "early + Thompson": (True, "ts"),
    "run-to-failure + Thompson": (False, "ts"),
}


def main():
    sev = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    train, _, _ = canonical_split(sev.keys())
    tr = {k: sev[k] for k in train}
    model = JackknifePlusLife().fit(dq_frame(tr, 100).values, [sev[k]["cycle_life"] for k in train])
    sigma = float(np.sqrt(np.mean(model.loo_resid_ ** 2)))

    b4 = load_b4(os.path.join(ROOT, "data"), verbose=False)
    keys = list(b4)
    pred, _, _ = model.predict(dq_frame(b4, 100).loc[keys].values)
    protocols = sorted({b4[k]["charge_policy"] for k in keys})
    arms, true_mean, pred_mean = [], [], []
    for p in protocols:
        ks = [i for i, k in enumerate(keys) if b4[keys[i]]["charge_policy"] == p]
        lives = np.array([b4[keys[i]]["cycle_life"] for i in ks])
        arms.append([Replicate(float(np.log10(b4[keys[i]]["cycle_life"])), float(np.log10(pred[i])),
                               float(b4[keys[i]]["cycle_life"])) for i in ks])
        true_mean.append(float(lives.mean()))
        pred_mean.append(float(np.mean(pred[ks])))
    true_mean, pred_mean = np.array(true_mean), np.array(pred_mean)
    best = true_mean.max()
    top = true_mean >= 0.95 * best
    rho = float(spearmanr(pred_mean, true_mean)[0])

    budget_max = float(sum(b4[k]["cycle_life"] for k in keys))
    budgets = np.unique(np.r_[np.geomspace(900, budget_max, 160), budget_max])
    curves = {}
    for name, (early, strat) in STRATEGIES.items():
        rng = np.random.default_rng(12345)
        recs = np.array([at_budgets(run_campaign(arms, early, strat, budget_max, rng, channels=CHANNELS,
                                                 sigma=sigma), budgets) for _ in range(N_CAMPAIGNS)])
        good = np.where(recs >= 0, top[np.clip(recs, 0, None)], False)
        regret = np.where(recs >= 0, (best - true_mean[np.clip(recs, 0, None)]) / best, np.nan)
        started = (recs >= 0).any(axis=0)
        mean_regret = [round(float(np.nanmean(regret[:, i])), 4) if started[i] else None
                       for i in range(len(budgets))]
        p_top = good.mean(axis=0)
        curves[name] = {"p_top": p_top.round(4).tolist(),
                        "mean_regret": mean_regret,
                        "b95": first_budget_reaching(budgets, p_top, BARS["p_top"])}
        print(f"{name:28s} B95 = {curves[name]['b95']}  final P(top) = {p_top[-1]:.3f}")

    b1 = curves["run-to-failure grid"]["b95"] or budget_max
    b3 = curves["early + Thompson"]["b95"]
    checks = {"spearman": rho >= BARS["spearman"],
              "budget": b3 is not None and b3 <= BARS["budget_ratio"] * b1}
    decision = ("BUILD" if all(checks.values()) else "RESCOPE" if checks["spearman"] else "KILL")
    days = lambda c: None if c is None else round(c * MIN_PER_CYCLE / 1440, 1)

    out = {"bars": BARS, "sigma_log10": sigma, "protocols": protocols,
           "true_mean": true_mean.round(1).tolist(), "pred_mean": pred_mean.round(1).tolist(),
           "top_cluster": top.tolist(), "spearman": rho, "budget_max": budget_max,
           "budgets": budgets.round(1).tolist(), "curves": curves, "b1": b1, "b3": b3,
           "ratio": None if b3 is None else b3 / b1, "channel_days": {"b1": days(b1), "b3": days(b3)},
           "min_per_cycle": MIN_PER_CYCLE, "checks": checks, "decision": decision,
           "n_campaigns": N_CAMPAIGNS, "channels": CHANNELS}
    with open(os.path.join(ROOT, "figures", "closed_loop.json"), "w") as fp:
        json.dump(out, fp, indent=1)

    for p, t, pm, tp in sorted(zip(protocols, true_mean, pred_mean, top), key=lambda r: -r[1]):
        print(f"  {p:22s} true {t:6.0f}  predicted {pm:6.0f}  {'top' if tp else ''}")
    print(f"sigma {sigma:.3f}  spearman {rho:.3f}  B1 {b1:.0f} ({days(b1)} ch-days)  "
          f"B3 {b3} ({days(b3)} ch-days)  ratio {out['ratio']}")
    print("checks", checks, "->", decision)
    _figure(out)


def _figure(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    col = {"run-to-failure grid": "#9a9a9a", "early grid": "#d9a58a",
           "early + Thompson": "#b0653a", "run-to-failure + Thompson": "#444444"}
    b = np.array(out["budgets"]) * out["min_per_cycle"] / 1440
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    for name, c in out["curves"].items():
        ax.plot(b, np.array(c["p_top"]) * 100, color=col[name], lw=1.8, label=name)
    ax.axhline(95, color="#444", lw=0.8, ls="--")
    ax.axhline(100 * 5 / 9, color="#9a9a9a", lw=0.8, ls=":")
    ax.text(b[-1], 100 * 5 / 9 + 1.5, "chance (5 of 9)", ha="right", fontsize=8, color="#666")
    ax.set_xscale("log")
    ax.set_xlabel("cycler budget (channel-days)")
    ax.set_ylabel("campaigns recommending a top-cluster protocol (%)")
    ax.set_title(f"Finding a good protocol, {out['n_campaigns']} replayed campaigns\n"
                 f"gate: {out['decision']}", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    tm, pm = np.array(out["true_mean"]), np.array(out["pred_mean"])
    ax2.scatter(pm, tm, color=["#b0653a" if t else "#9a9a9a" for t in out["top_cluster"]], s=40)
    lim = [min(tm.min(), pm.min()) * 0.95, max(tm.max(), pm.max()) * 1.05]
    ax2.plot(lim, lim, color="#444", lw=0.8)
    ax2.set_xlabel("mean predicted life at cycle 100 (5 replicates)")
    ax2.set_ylabel("true mean life")
    ax2.set_title(f"Ranking the 9 protocols: Spearman ρ = {out['spearman']:.2f}\n"
                  "orange = top cluster (within 5% of best)", fontsize=10, loc="left")
    for a in (ax, ax2):
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "figures", "closed_loop.png"), dpi=150)


if __name__ == "__main__":
    main()
