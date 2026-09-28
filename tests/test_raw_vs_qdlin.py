"""Raw-curve features must reproduce the Qdlin features the model trained on.

Every real file (TRY IT, scripts/score_files.py, the batch-recalibration
runner) goes through dq_features_from_cycles; the model was trained on
Severson's Qdlin arrays. Needs the Severson .mat files; skips otherwise.
Full 124-cell check: scripts/raw_vs_qdlin.py.
"""

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT = os.path.join(ROOT, "data", "2017-05-12_batchdata_updated_struct_errorcorrect.mat")


@pytest.mark.skipif(not os.path.exists(MAT), reason="Severson batch files not present")
def test_raw_curve_features_match_qdlin():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from raw_vs_qdlin import raw_cycles
    from src.data import build_dataset
    from src.features import delta_q_features
    from src.transfer import DQ_FEATURES, dq_features_from_cycles

    sev = build_dataset(os.path.join(ROOT, "data"), verbose=False)
    keys = [k for k in sev if k.startswith("b1")][:12]
    raw = raw_cycles(MAT, "b1", set(keys))
    for f in DQ_FEATURES:
        d = [dq_features_from_cycles(raw[k])[f] - delta_q_features(sev[k])[f] for k in keys]
        assert np.median(np.abs(d)) < 0.01, f
