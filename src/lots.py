"""A lot of cells in one shape, from any source the batch-recalibration study reads.

A lot is {cell_id: {"life": cycles, "feats": {cutoff: {DQ_FEATURES}}, "qd2": Ah}}:
cycle life to 80% of nominal, DeltaQ(V) features from data up to each
checkpoint cutoff, and discharge capacity at cycle 2 (the batch-warning
signal). Loaders:

- lot_from_matr(bat_dict): MATR .mat batches (src/data.py, src/matr_b4.py),
  whose Qdlin arrays go through the training featurizer unchanged.
- lot_from_batterylife(paths): BatteryLife pickles (per-cycle time series).
- lot_from_files(paths): cycler text exports (src/ingest.py), one file per
  cell covering cycle 1 to end of life, which is what a lab would send.
"""

import os
import pickle

import numpy as np

from .features import delta_q_features
from .ingest import read_text
from .policy import CUTOFFS
from .transfer import dq_features_from_cycles

EOL_FRACTION = 0.80


def life_from_capacity(cycles, qd, nominal_ah, fraction=EOL_FRACTION):
    """First cycle (after the first) below fraction x nominal and still below
    at the next logged cycle; None if the log ends first (censored)."""
    thr = fraction * nominal_ah
    cycles, qd = np.asarray(cycles), np.asarray(qd, float)
    for i in range(1, len(qd)):
        if qd[i] < thr and (i == len(qd) - 1 or qd[i + 1] < thr):
            return float(cycles[i])
    return None


def lot_from_matr(bat_dict):
    lot = {}
    for k, c in bat_dict.items():
        feats = {cut: delta_q_features(c, cyc_late=cut) for cut in CUTOFFS}
        qd = np.asarray(c["summary"]["QD"], float)
        lot[k] = {"life": float(c["cycle_life"]), "feats": feats, "qd2": float(qd[1]) if len(qd) > 1 else None}
    return lot


def _from_cycle_map(cmap, nominal_ah):
    """(life, feats, qd2) from {cycle: {current_in_A, voltage_in_V, discharge_capacity_in_Ah}}."""
    nums = sorted(cmap)
    qmax = [float(np.max(cmap[n]["discharge_capacity_in_Ah"])) if len(cmap[n]["discharge_capacity_in_Ah"]) else 0.0
            for n in nums]
    life = life_from_capacity(nums, qmax, nominal_ah)
    feats = {cut: dq_features_from_cycles(cmap, cyc_late=cut, cyc_early=10) for cut in CUTOFFS}
    qd2 = qmax[nums.index(2)] if 2 in nums else None
    return life, feats, qd2


def lot_from_batterylife(paths, nominal_ah=None):
    lot = {}
    for p in paths:
        d = pickle.load(open(p, "rb"))
        cmap = {c["cycle_number"]: c for c in d["cycle_data"]}
        nom = nominal_ah or float(d.get("nominal_capacity_in_Ah") or 1.1)
        life, feats, qd2 = _from_cycle_map(cmap, nom)
        lot[d.get("cell_id") or p] = {"life": life, "feats": feats, "qd2": qd2}
    return lot


def lot_from_files(paths, nominal_ah=1.1):
    lot = {}
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as fp:
            text = fp.read()
        if "\ufffd" in text[:2000]:  # BioLogic exports are Latin-1
            text = open(p, encoding="latin-1").read()
        _, cycles = read_text(text, p)
        if cycles and min(cycles) == 0:  # BioLogic numbers cycles from 0
            cycles = {n + 1: d for n, d in cycles.items()}
        cmap = {n: {"current_in_A": d["current_in_A"], "voltage_in_V": d["voltage_in_V"],
                    "discharge_capacity_in_Ah": d["discharge_capacity_in_Ah"]} for n, d in cycles.items()}
        life, feats, qd2 = _from_cycle_map(cmap, nominal_ah)
        lot[os.path.splitext(os.path.basename(p))[0]] = {"life": life, "feats": feats, "qd2": qd2}
    return lot
