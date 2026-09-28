"""Read cycler text exports into per-cycle discharge curves, then DeltaQ(V) features.

Supported (text exports; binary formats get a friendly "export as text" error):
- Arbin MITS Pro CSV: Cycle_Index, Current(A), Voltage(V), Discharge_Capacity(Ah)
  (matr.io's unitless variant too: cycle_index, current, voltage, discharge_capacity)
- Maccor text export: tab-separated after a preamble; Cyc#, Step, Amps, Volts,
  Amp-hr, State (C/D/R). Currents are magnitudes and Amp-hr restarts every step,
  so discharge rows come from State == D and capacity is accumulated across a
  cycle's discharge steps.
- Neware BTS CSV: Cycle ID / Cycle Index, Current(mA|A), Voltage(V),
  Capacitance_DChg(mAh) / DChg. Cap.(Ah)
- BioLogic EC-Lab .mpt: "Nb header lines : N" preamble; cycle number, Ewe/V or
  Ecell/V, I/mA or <I>/mA, Q discharge/mA.h; decimal commas accepted
- Hectocycle CSV: cycle, voltage_v, discharge_capacity_ah (discharge rows only)

Everything here is mirrored line for line in app/static/core.js so the TRY IT
tab scores files in the browser; tests/js/parity.mjs checks the two agree.
"""

import os
import re

import numpy as np

from .transfer import DQ_FEATURES, dq_features_from_cycles

BINARY_EXT = {".nda": "Neware", ".ndax": "Neware", ".mpr": "BioLogic", ".res": "Arbin", ".xlsx": "Excel",
              ".xls": "Excel"}
DEADBAND_A = 0.05
EARLY, LATE = (10, 3), (100, 5)  # (target cycle, tolerance)

CYCLE = {"cycleindex", "cycleid", "cycle", "cyclenumber", "cyclec", "cyc"}
VOLT = {"voltage", "volts", "ewe", "ecell", "voltagev"}
CURR = {"current", "amps", "i", "currenta"}
QDIS = {"dischargecapacity", "capacitancedchg", "dchgcap", "qdischarge", "dischargecapacityah",
        "dchgcapacity"}
QANY = {"amphr", "capacity"}
STATE = {"state", "md"}
STEP = {"step", "stepindex", "stepid", "ns"}
SCALE = {"v": 1.0, "mv": 1e-3, "a": 1.0, "ma": 1e-3, "ah": 1.0, "ahr": 1.0, "mah": 1e-3}


class IngestError(ValueError):
    """A file we can't read, with a message written for the person uploading it."""


def parse_header(h):
    """'Discharge_Capacity(Ah)' -> ('dischargecapacity', 'ah'); 'Q discharge/mA.h' -> ('qdischarge', 'mah')."""
    h = h.strip().lower()
    m = re.match(r"^(.*?)\s*[(/]\s*([^)]*)\)?\s*$", h)
    name, unit = (m.group(1), m.group(2)) if m else (h, "")
    return re.sub(r"[^a-z0-9]", "", name), re.sub(r"[^a-z]", "", unit)


def _num(s):
    s = s.strip()
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _split_table(lines):
    """Delimiter-sniffed (header fields, data rows) from the header line onward."""
    head = lines[0]
    delim = max(("\t", ",", ";"), key=head.count)
    return [f for f in head.split(delim)], [ln.split(delim) for ln in lines[1:]]


def _find(cols, names):
    for i, (n, _) in enumerate(cols):
        if n in names:
            return i
    return -1


def _refuse_binary(filename):
    ext = filename[filename.rfind("."):].lower() if "." in filename else ""
    if ext in BINARY_EXT:
        raise IngestError(f"{os.path.basename(filename)} is a binary {BINARY_EXT[ext]} file. Export it from the cycler "
                          "software as text (CSV, TXT or MPT) and try again.")


def read_text(text, filename=""):
    """(vendor, {cycle: {current_in_A, voltage_in_V, discharge_capacity_in_Ah}})."""
    _refuse_binary(filename)
    lines = [ln for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    vendor = None
    start = 0
    m = re.search(r"nb header lines\s*:\s*(\d+)", text[:4000], re.I)
    if m:
        vendor, start = "BioLogic", int(m.group(1)) - 1
    else:
        for i, ln in enumerate(lines[:60]):
            fields = [parse_header(f)[0] for f in re.split(r"\t", ln)]
            if "cyc" in fields or "cyclec" in fields:
                vendor, start = "Maccor", i
                break
    body = [ln for ln in lines[start:] if ln.strip()]
    if len(body) < 20:
        raise IngestError("That file looks too short. Expected discharge time-series rows for cycles 10 and 100.")
    header, rows = _split_table(body)
    cols = [parse_header(h) for h in header]
    ci, vi, ii = _find(cols, CYCLE), _find(cols, VOLT), _find(cols, CURR)
    qi, si, ti = _find(cols, QDIS), _find(cols, STATE), _find(cols, STEP)
    if qi == -1 and si != -1:
        qi = _find(cols, QANY)
    if ci == -1 or vi == -1 or qi == -1:
        raise IngestError("Could not find cycle, voltage and discharge-capacity columns. Supported: Arbin, "
                          "Maccor, Neware and BioLogic text exports, or cycle,voltage_v,discharge_capacity_ah.")
    if vendor is None:
        names = {n for n, _ in cols}
        vendor = ("Arbin" if "cycleindex" in names else "Neware" if names & {"cycleid", "capacitancedchg", "dchgcap"}
                  else "Hectocycle CSV" if ii == -1 else "CSV")
    vs, qs, is_ = SCALE.get(cols[vi][1], 1.0), SCALE.get(cols[qi][1], 1.0), SCALE.get(cols[ii][1], 1.0) if ii != -1 else 1.0

    cycles = {}
    offset, last_q, last_key = 0.0, 0.0, None
    for r in rows:
        if len(r) <= max(ci, vi, qi, ii, si, ti):
            continue
        c, v, q = _num(r[ci]), _num(r[vi]) * vs, _num(r[qi]) * qs
        if not (np.isfinite(c) and np.isfinite(v) and np.isfinite(q)):
            continue
        c = int(round(c))
        if si != -1:  # Maccor: state flags discharge; capacity restarts every step
            if not r[si].strip().upper().startswith("D"):
                continue
            key = (c, r[ti].strip() if ti != -1 else "")
            if last_key is None or key[0] != last_key[0]:
                offset = 0.0
            elif key != last_key:
                offset += last_q
            last_key, last_q = key, q
            q, cur = q + offset, -1.0
        elif ii != -1:
            cur = _num(r[ii]) * is_
            if not np.isfinite(cur):
                continue
        else:
            cur = -1.0  # discharge-only file
        d = cycles.setdefault(c, {"current_in_A": [], "voltage_in_V": [], "discharge_capacity_in_Ah": []})
        d["current_in_A"].append(cur)
        d["voltage_in_V"].append(v)
        d["discharge_capacity_in_Ah"].append(q)
    return vendor, cycles


def _nearest(cycles, target, tol):
    best = None
    for c in sorted(cycles):
        if abs(c - target) <= tol and (best is None or abs(c - target) < abs(best - target)):
            best = c
    return best


def _n_discharge(cyc):
    I = np.asarray(cyc["current_in_A"], float)
    Q = np.asarray(cyc["discharge_capacity_in_Ah"], float)
    return int(np.sum((I < -DEADBAND_A) & (Q >= 0)))


def featurize_text(text, filename=""):
    """{vendor, cycles: [early, late], n_points: [..], feats: {DQ_FEATURES}} or IngestError."""
    vendor, cycles = read_text(text, filename)
    dis = {c: d for c, d in cycles.items() if _n_discharge(d) > 0}
    ce, cl = _nearest(dis, *EARLY), _nearest(dis, *LATE)
    if ce is None or cl is None:
        found = sorted(dis)
        raise IngestError("Need discharge data at cycle ~10 and cycle ~100. Found cycles: "
                          + ", ".join(str(c) for c in found[:12]) + ("…" if len(found) > 12 else ""))
    for c in (ce, cl):
        n = _n_discharge(dis[c])
        if n < 20:
            raise IngestError(f"Cycle {c} has only {n} usable points. A full discharge branch is needed.")
    feats = dq_features_from_cycles(dis, cyc_late=cl, cyc_early=ce)
    if feats is None:
        raise IngestError("The two cycles' voltage ranges do not overlap. Check that the voltage column is in volts.")
    return {"vendor": vendor, "cycles": [ce, cl], "n_points": [_n_discharge(dis[ce]), _n_discharge(dis[cl])],
            "feats": {k: feats[k] for k in DQ_FEATURES}}


def featurize_file(path):
    _refuse_binary(path)
    with open(path, encoding="utf-8", errors="replace") as fp:
        text = fp.read()
    if "�" in text[:2000]:  # BioLogic exports are Latin-1
        with open(path, encoding="latin-1") as fp:
            text = fp.read()
    return featurize_text(text, path)
