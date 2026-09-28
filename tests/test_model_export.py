"""Parity: the exported-JSON scoring path must match the sklearn model.

The TRY IT tab scores cells in the browser from the JSON export. src/scoring.py
is the pure-Python reference of that scorer (same pseudocode as core.js: scale
-> dot -> isotonic interpolation; per-fold PAVA for the Venn-ABERS interval);
this checks it against EarlyVerdictModel / cvap_predict on real feature vectors.
Requires the built bundle + Severson data; skips otherwise.
"""

import json
import os

import numpy as np
import pytest

from src.scoring import fold_score, score_point, venn_abers

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROOT, "app", "static", "cockpit_data.json")
DATA = os.path.join(ROOT, "data", "processed_slim.pkl")

needs_data = pytest.mark.skipif(
    not (os.path.exists(BUNDLE) and os.path.exists(DATA)),
    reason="bundle or Severson data not present")


@needs_data
def test_export_matches_sklearn():
    import sys
    sys.path.insert(0, ROOT)
    from src.calibration import cvap_predict
    from src.data import build_dataset
    from src.features import featurize
    from src.labels import make_labels
    from src.model import EarlyVerdictModel
    from src.split import canonical_split
    from src.transfer import DQ_FEATURES

    m = json.load(open(BUNDLE))["qual"]["model"]
    bd = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    labels, _ = make_labels(bd, threshold=700, verbose=False)
    train, primary, secondary = canonical_split(bd.keys())
    feats = featurize(bd, cutoff=100)[DQ_FEATURES]
    X_tr = feats.loc[train].values
    y_tr = np.array([labels[k] for k in train])
    X_te = feats.loc[primary + secondary].values

    ref = EarlyVerdictModel().fit(X_tr, y_tr)
    p_ref = ref.predict_proba(X_te)[:, 1]
    p_json = np.array([score_point(m["point"], x) for x in X_te])
    assert np.max(np.abs(p_ref - p_json)) < 1e-6

    _, p0_ref, p1_ref = cvap_predict(X_tr, y_tr, X_te[:10], seed=0)
    for i in range(10):
        p0s, p1s = [], []
        for fold in m["cvap"]:
            p0, p1 = venn_abers(fold, fold_score(fold, X_te[i]))
            p0s.append(p0); p1s.append(p1)
        assert abs(np.mean(p0s) - p0_ref[i]) < 1e-6
        assert abs(np.mean(p1s) - p1_ref[i]) < 1e-6
