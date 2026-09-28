"""Score cells with the JSON-exported production model, in plain Python.

This is the reference implementation of the browser scorer (app/static/core.js
scoreCell): scale -> linear -> isotonic interpolation for the point
probability; per-fold PAVA for the cross Venn-ABERS interval. It is checked
against sklearn in tests/test_model_export.py and against core.js in
tests/js/parity.mjs, and scores cycler files in scripts/score_files.py.
"""

import numpy as np


def score_point(m, x):
    """Mirror of the JS point scorer: scale -> linear -> isotonic interp."""
    z = sum((xi - mu) / sc * w for xi, mu, sc, w in zip(x, m["mean"], m["scale"], m["coef"])) + m["intercept"]
    xs, ys = m["iso_x"], m["iso_y"]
    if z <= xs[0]:
        return ys[0]
    if z >= xs[-1]:
        return ys[-1]
    i = np.searchsorted(xs, z) - 1
    t = (z - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] != xs[i] else 0.0
    return ys[i] + t * (ys[i + 1] - ys[i])


def pava(xs, ys):
    """Isotonic regression via pool-adjacent-violators; ties on x averaged
    first (sklearn's behavior). Returns fitted value per input point."""
    order = np.argsort(xs, kind="stable")
    xs_s, ys_s = np.asarray(xs)[order], np.asarray(ys)[order]
    ux, inv = np.unique(xs_s, return_inverse=True)
    uy = np.array([ys_s[inv == i].mean() for i in range(len(ux))])
    uw = np.array([(inv == i).sum() for i in range(len(ux))], dtype=float)
    vals, wts, idx = [], [], []
    for y, w in zip(uy, uw):
        vals.append(y); wts.append(w); idx.append(1)
        while len(vals) > 1 and vals[-2] >= vals[-1]:
            v = (vals[-2] * wts[-2] + vals[-1] * wts[-1]) / (wts[-2] + wts[-1])
            wts[-2] += wts[-1]; idx[-2] += idx[-1]
            vals.pop(); wts.pop(); idx.pop()
            vals[-1] = v
    fitted_u = np.repeat(vals, idx)
    return fitted_u, ux


def venn_abers(fold, s):
    """Mirror of the JS interval scorer for one fold and one test score."""
    out = []
    for label in (0, 1):
        xs = fold["cal_scores"] + [s]
        ys = fold["cal_labels"] + [label]
        fitted, ux = pava(xs, ys)
        out.append(float(fitted[np.searchsorted(ux, s)]))
    return out  # [p0, p1]


def fold_score(fold, x):
    return sum((xi - mu) / sc * w for xi, mu, sc, w in zip(x, fold["mean"], fold["scale"], fold["coef"])) + fold["intercept"]


def score_features(model, envelope, feats):
    """{p, p0, p1, verdict, violations} for one feature dict (core.js scoreCell)."""
    x = [feats[f] for f in model["features"]]
    ivs = [venn_abers(fold, fold_score(fold, x)) for fold in model["cvap"]]
    p0, p1 = float(np.mean([a for a, _ in ivs])), float(np.mean([b for _, b in ivs]))
    violations = [f for f in model["features"] if not envelope[f][0] <= feats[f] <= envelope[f][1]]
    verdict = ("out-of-envelope" if violations else "pass" if p0 > 0.5 else "fail" if p1 < 0.5
               else "keep-testing")
    return {"p": float(score_point(model["point"], x)), "p0": p0, "p1": p1,
            "verdict": verdict, "violations": violations}
