import numpy as np

from src.lots import life_from_capacity, lot_from_files
from src.policy import CUTOFFS


def test_life_rule_requires_a_sustained_crossing():
    cyc = [1, 2, 3, 4, 5, 6]
    assert life_from_capacity(cyc, [1.0, 1.0, 0.87, 0.95, 0.87, 0.86], 1.1) == 5  # dip at 3 is noise
    assert life_from_capacity(cyc, [1.0] * 6, 1.1) is None  # log ends above EOL: censored
    assert life_from_capacity(cyc, [0.5, 1.0, 1.0, 1.0, 1.0, 0.8], 1.1) == 6  # first cycle ignored


def _arbin_full_life(path, eol_cycle=130, n_cycles=140):
    """A synthetic Arbin export from cycle 1 past end of life."""
    rows = ["Data_Point,Cycle_Index,Current(A),Voltage(V),Discharge_Capacity(Ah)"]
    n = 0
    for c in range(1, n_cycles + 1):
        qmax = 1.07 - (1.07 - 0.875) * (c / eol_cycle) ** 2
        for v in np.linspace(2.0, 3.6, 6):  # charge rows
            n += 1
            rows.append(f"{n},{c},0.55,{v:.4f},0")
        for i, v in enumerate(np.linspace(3.5, 2.0, 60)):  # discharge rows, shape shifts with age
            n += 1
            frac = i / 59
            q = qmax * (frac + 0.02 * (c / 100) * np.sin(np.pi * frac))
            rows.append(f"{n},{c},-4.4,{v:.4f},{q:.6f}")
    path.write_text("\n".join(rows) + "\n")


def test_lot_from_vendor_files(tmp_path):
    p = tmp_path / "cell_07.csv"
    _arbin_full_life(p)
    lot = lot_from_files([str(p)])
    c = lot["cell_07"]
    assert 120 <= c["life"] <= 135
    assert abs(c["qd2"] - 1.07) < 0.01
    assert set(c["feats"]) == set(CUTOFFS)
    assert all(v is not None for v in c["feats"].values())
