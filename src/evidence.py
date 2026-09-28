"""Per-checkpoint verdicts from the shipped classifier for cells of any lot.

At each cutoff in src/policy.CUTOFFS the production model (DeltaQ(V)-only
EarlyVerdictModel + cross Venn-ABERS) is refit on the Severson training split
with features truncated there, exactly as scripts/build_bundle.py does, and
scores the lot's cells. The envelope guard uses the cutoff-100 training
features. Output feeds the confirmed-call rule in src/policy.py.
"""

import numpy as np

from .calibration import abstain_call, cvap_predict
from .features import dq_frame
from .model import EarlyVerdictModel
from .policy import CUTOFFS
from .transfer import DQ_FEATURES, envelope_violations, feature_envelope


def classifier_evidence(sev, train, labels, lot):
    """({cell: [{cutoff, p, lo, hi, call}]}, {cell: [violations]}) for a lot (src/lots.py)."""
    y_tr = np.array([labels[k] for k in train])
    tr = {k: sev[k] for k in train}
    env = feature_envelope(dq_frame(tr, 100))
    viol, evidence = {}, {k: [] for k in lot}
    for k, c in lot.items():
        f = c["feats"].get(100)
        viol[k] = ["missing cycle-100 data"] if f is None else envelope_violations(f, env)
    for cutoff in CUTOFFS:
        X_tr = dq_frame(tr, cutoff).values
        keys = [k for k in lot if lot[k]["feats"].get(cutoff) is not None]
        if not keys:
            continue
        X = np.array([[lot[k]["feats"][cutoff][f] for f in DQ_FEATURES] for k in keys])
        p = EarlyVerdictModel().fit(X_tr, y_tr).predict_proba(X)[:, 1]
        _, lo, hi = cvap_predict(X_tr, y_tr, X, seed=0)
        for k, pv, a, b, cv in zip(keys, p, lo, hi, abstain_call(lo, hi)):
            evidence[k].append({"cutoff": cutoff, "p": float(pv), "lo": float(a), "hi": float(b), "call": int(cv)})
    return evidence, viol
