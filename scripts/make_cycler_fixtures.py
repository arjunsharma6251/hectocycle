"""Write tests/fixtures/cyclers/: the sample cell in each supported vendor layout.

The discharge points are the real ones from app/static/sample_cell.csv (an SNL
LFP cell, cycles 10 and 100). Charge and rest rows are synthesized around them
so each file has the structure a real export has: mixed step types, vendor
units and sign conventions, Maccor's per-step capacity restart, BioLogic's
decimal commas, Latin-1 preamble and zero-based cycle numbering. Every
fixture must featurize to exactly the sample cell's DeltaQ(V) features.

    .venv/bin/python scripts/make_cycler_fixtures.py
"""

import csv
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "tests", "fixtures", "cyclers")
PARITY = os.path.join(ROOT, "tests", "fixtures", "parity.json")
I_DIS, I_CHG = 1.1, 0.55  # amps


def load_sample():
    cyc = {}
    with open(os.path.join(ROOT, "app", "static", "sample_cell.csv")) as fp:
        for r in csv.DictReader(fp):
            cyc.setdefault(int(r["cycle"]), []).append((r["voltage_v"], r["discharge_capacity_ah"]))
    return cyc  # values kept as the exact source strings


def steps(cycle_pts):
    """[(kind, voltage_str, capacity_str)] for charge, rest, discharge of one cycle."""
    out = [("C", f"{v:.5f}", f"{q:.6f}") for v, q in zip(np.linspace(2.0, 3.6, 12), np.linspace(0, 1.05, 12))]
    out += [("R", "3.45000", "0.000000")] * 3
    out += [("D", v, q) for v, q in cycle_pts]
    return out


def arbin(cyc):
    rows = [["Data_Point", "Test_Time(s)", "Step_Index", "Cycle_Index", "Current(A)", "Voltage(V)",
             "Charge_Capacity(Ah)", "Discharge_Capacity(Ah)"]]
    n = 0
    for c in sorted(cyc):
        for kind, v, q in steps(cyc[c]):
            n += 1
            cur = {"C": I_CHG, "R": 0.0, "D": -I_DIS}[kind]
            rows.append([n, n * 10, {"C": 1, "R": 2, "D": 3}[kind], c, cur, v,
                         q if kind == "C" else "0", q if kind == "D" else "0"])
    return "\n".join(",".join(map(str, r)) for r in rows) + "\n"


def maccor(cyc):
    lines = ["Today's Date 09/28/2026", "Date of Test: 01/15/2026", "Filename: CELL_017.001",
             "Procedure: LFP_QUAL_1C.000", "Comment/Barcode: sample cell", ""]
    lines.append("\t".join(["Rec#", "Cyc#", "Step", "Test (Sec)", "Step (Sec)", "Amp-hr", "Watt-hr", "Amps",
                            "Volts", "State", "ES", "DPt Time"]))
    n = 0
    for c in sorted(cyc):
        pts = steps(cyc[c])
        dis = [p for p in pts if p[0] == "D"]
        split_at = len(dis) // 2
        # the discharge runs as two steps; Amp-hr restarts at the second one
        q_split = float(dis[split_at - 1][2])
        di = 0
        for kind, v, q in pts:
            n += 1
            if kind == "D":
                step = 5 if di < split_at else 6
                amp_hr = q if di < split_at else f"{float(q) - q_split:.9f}"
                di += 1
            else:
                step, amp_hr = {"C": 2, "R": 3}[kind], q
            amps = {"C": I_CHG, "R": 0.0, "D": I_DIS}[kind]
            lines.append("\t".join(map(str, [n, c, step, n * 10, 10, amp_hr, 0, amps, v, kind, 0,
                                             "01/15/2026 10:00:00"])))
    return "\n".join(lines) + "\n"


def neware(cyc):
    rows = [["Record ID", "Cycle ID", "Step ID", "Step Type", "Current(mA)", "Voltage(V)",
             "Capacitance_Chg(mAh)", "Capacitance_DChg(mAh)"]]
    n = 0
    for c in sorted(cyc):
        for kind, v, q in steps(cyc[c]):
            n += 1
            mah = f"{float(q) * 1000:.6f}"
            rows.append([n, c, {"C": 1, "R": 2, "D": 3}[kind], {"C": "CC Chg", "R": "Rest", "D": "CC DChg"}[kind],
                         {"C": I_CHG * 1000, "R": 0, "D": -I_DIS * 1000}[kind], v,
                         mah if kind == "C" else "0", mah if kind == "D" else "0"])
    return "\n".join(",".join(map(str, r)) for r in rows) + "\n"


def biologic(cyc):
    cols = ["mode", "ox/red", "error", "cycle number", "time/s", "Ewe/V", "<I>/mA", "Q discharge/mA.h",
            "Q charge/mA.h"]
    pre = ["EC-Lab ASCII FILE", "Nb header lines : 6", "", "Technique : Galvanostatic Cycling with Potential Limitation",
           "Cell: LFP 18650, 25 °C"]
    lines = []
    n = 0
    for c in sorted(cyc):
        for kind, v, q in steps(cyc[c]):
            n += 1
            mah = f"{float(q) * 1000:.6f}"
            row = [1, 1 if kind == "C" else 0, 0, f"{c - 1:.15E}", n * 10, v,
                   {"C": I_CHG * 1000, "R": 0, "D": -I_DIS * 1000}[kind],
                   mah if kind == "D" else "0", mah if kind == "C" else "0"]
            lines.append("\t".join(str(x).replace(".", ",") for x in row))
    return "\n".join(pre + ["\t".join(cols)] + lines) + "\n"


def parity_expectations():
    """What core.js must reproduce: features per fixture (src/ingest.py) and
    scores for a spread of feature vectors (src/scoring.py, the Python reference
    of the browser scorer, parity-tested against sklearn in tests/test_model_export.py)."""
    from src.ingest import featurize_file
    from src.scoring import fold_score, score_point, venn_abers

    files = ["../../../app/static/sample_cell.csv"] + sorted(os.listdir(OUT))
    feats = {f: featurize_file(os.path.normpath(os.path.join(OUT, f)))["feats"] for f in files}
    model = json.load(open(os.path.join(ROOT, "app", "static", "cockpit_data.json")))["qual"]["model"]
    base = feats["arbin.csv"]
    vectors = [base] + [{k: base[k] + d * (i + 1) for i, k in enumerate(base)}
                        for d in (-0.6, -0.3, -0.1, 0.1, 0.3, 0.6)]
    scores = []
    for v in vectors:
        x = [v[f] for f in model["features"]]
        ivs = [venn_abers(fold, fold_score(fold, x)) for fold in model["cvap"]]
        scores.append({"feats": v, "p": float(score_point(model["point"], x)),
                       "p0": float(np.mean([a for a, _ in ivs])), "p1": float(np.mean([b for _, b in ivs]))})
    return {"features": feats, "scores": scores}


def main():
    cyc = load_sample()
    os.makedirs(OUT, exist_ok=True)
    files = {"arbin.csv": arbin(cyc), "maccor.txt": maccor(cyc), "neware.csv": neware(cyc),
             "biologic.mpt": biologic(cyc)}
    for name, text in files.items():
        enc = "latin-1" if name.endswith(".mpt") else "utf-8"
        with open(os.path.join(OUT, name), "w", encoding=enc, newline="") as fp:
            fp.write(text)
        print("wrote", os.path.relpath(os.path.join(OUT, name), ROOT))
    with open(PARITY, "w") as fp:
        json.dump(parity_expectations(), fp, indent=1)
    print("wrote", os.path.relpath(PARITY, ROOT))


if __name__ == "__main__":
    main()
