"""Score the abstain rule as a cycler-allocation policy (docs/early-call-study.md, section 6).

Reads the precomputed evidence timelines from app/static/cockpit_data.json
(no refit), simulates the stopping rules in src/policy.py against the
run-to-spec baseline, converts cycles to cycler-hours with each cell's own
measured cycle duration from the raw Severson batch files (cached in
data/cycle_minutes.json; falls back to a flat 50 min/cycle if the raw files
are absent), prints the markdown table used in the study doc, and draws
figures/allocation_policy.png.
"""

import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data import BATCH_FILES  # noqa: E402
from src.policy import CUTOFFS, compare, saved_by_class, simulate  # noqa: E402

BUNDLE = os.path.join(ROOT, "app", "static", "cockpit_data.json")
CACHE = os.path.join(ROOT, "data", "cycle_minutes.json")
FIG = os.path.join(ROOT, "figures", "allocation_policy.png")
FALLBACK_MIN_PER_CYCLE = 50.0


def cycle_minutes(data_dir=os.path.join(ROOT, "data")):
    """{cell_key: median minutes per cycle} from the raw .mat per-cycle clocks."""
    if os.path.exists(CACHE):
        return json.load(open(CACHE))
    try:
        import h5py
    except ImportError:
        return {}
    out = {}
    for prefix, fname in BATCH_FILES.items():
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            continue
        with h5py.File(path, "r") as f:
            batch = f["batch"]
            for i in range(batch["cycles"].shape[0]):
                grp = f[batch["cycles"][i, 0]]
                refs = grp["t"]
                durs = []
                for j in range(1, refs.shape[0]):  # cycle 0 is a placeholder
                    t = f[refs[j, 0]][()]
                    if t.size:
                        durs.append(float(np.max(t)))
                if durs:
                    out[f"{prefix}c{i}"] = float(np.median(durs))
    if out:
        json.dump(out, open(CACHE, "w"), indent=0)
    return out


def main():
    d = json.load(open(BUNDLE))
    T = d["qual"]["threshold"]
    cells = [c for c in d["qual"]["cells"] if "evidence" in c]
    mins = cycle_minutes()
    measured = all(c["id"] in mins for c in cells)
    rate = {c["id"]: mins.get(c["id"], FALLBACK_MIN_PER_CYCLE) for c in cells}
    if measured:
        r = np.array(list(rate.values()))
        print(f"cycle duration (measured, n={len(r)}): median {np.median(r):.1f} min, "
              f"range {r.min():.1f}-{r.max():.1f} min")
    else:
        print(f"cycle duration: flat {FALLBACK_MIN_PER_CYCLE} min/cycle (raw files absent)")

    results = compare(cells, T)
    print(f"\nn={len(cells)} test cells, T={T}, baseline = run to spec (fail -> EOL, pass -> T)\n")
    print("| Policy | Cells pulled early | Wrong verdicts | Cycler-hours (baseline -> policy) | Saved |")
    print("|---|---|---|---|---|")
    for res in results:
        b, p = res.hours(rate)
        print(f"| {res.name} | {res.n_called}/{res.n} ({res.n_called / res.n:.0%}) | "
              f"{len(res.wrong)} | {b:,.0f} -> {p:,.0f} | **{res.saved_frac:.0%}** |")
    for res in results:
        if res.wrong:
            print(f"\n{res.name} wrong calls: " + ", ".join(
                f"{o.cell} (life {o.cycle_life:.0f}, true {'pass' if o.label else 'fail'}, "
                f"called {'pass' if o.verdict else 'fail'} at cycle {o.stop_cycle:.0f})" for o in res.wrong))
    conf = next(r for r in results if r.name == "confirmed-call")
    sv = saved_by_class(conf)
    b, p = conf.hours(rate)
    print(f"\nconfirmed-call: cycles saved on true-pass cells {sv[1]:,.0f}, on true-fail cells {sv[0]:,.0f}; "
          f"cycler-hours {b:,.0f} -> {p:,.0f} ({(b - p) / 24:,.0f} cycler-days freed)")
    stops = [o.stop_cycle for o in conf.outcomes if o.called_early]
    print("confirmed-call stop cycles:", {int(c): stops.count(c) for c in sorted(set(stops))})

    # ---- figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    first = next(r for r in results if r.name == "first-call")
    order = sorted(conf.outcomes, key=lambda o: o.cycle_life)
    ys = np.arange(len(order))
    col = {1: "#2a78d6", 0: "#c0392b"}
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 7), gridspec_kw={"width_ratios": [3, 2]})
    for y, o in zip(ys, order):
        ax.plot([0, o.baseline_cycles], [y, y], color="#d0d0d0", lw=2.2, solid_capstyle="butt")
        ax.plot([0, o.stop_cycle], [y, y], color=col[o.label], lw=2.2, solid_capstyle="butt")
    ax.axvline(T, color="#444", lw=0.8, ls="--")
    ax.text(T + 8, len(order) - 1.5, f"spec T={T}", fontsize=8, va="top")
    ax.set_yticks([])
    ax.set_xlabel("cycles on the cycler")
    ax.set_title("Confirmed-call policy: colored = cycler time actually used, grey = run-to-spec baseline\n"
                 f"{conf.n_called}/{conf.n} cells pulled early, 0 wrong verdicts, {conf.saved_frac:.0%} of cycler-cycles saved",
                 fontsize=10, loc="left")
    ax.plot([], [], color=col[1], lw=3, label="true pass")
    ax.plot([], [], color=col[0], lw=3, label="true fail")
    ax.plot([], [], color="#d0d0d0", lw=3, label="baseline (fail→EOL, pass→T)")
    ax.legend(loc="lower right", fontsize=8, frameon=False)
    ax.set_ylabel("83 test cells, sorted by cycle life →")

    names = [r.name for r in results]
    saved = [r.saved_frac * 100 for r in results]
    wrong = [len(r.wrong) for r in results]
    x = np.arange(len(results))
    bars = ax2.bar(x, saved, color=["#b0653a" if w == 0 else "#d9a58a" for w in wrong])
    for xi, s, w in zip(x, saved, wrong):
        ax2.text(xi, s + 1, f"{s:.0f}%", ha="center", fontsize=8)
        if w:
            ax2.text(xi, s / 2, f"{w} wrong", ha="center", color="#5a2f14", fontsize=8, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax2.set_ylabel("cycler-cycles saved vs run-to-spec (%)")
    ax2.set_ylim(0, 100)
    ax2.set_title("Savings by stopping rule\n(dark = zero wrong verdicts)", fontsize=10, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
        ax2.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG, dpi=150)
    print("figure ->", os.path.relpath(FIG, ROOT))


if __name__ == "__main__":
    main()
