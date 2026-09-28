import os

import pytest

from src.ingest import IngestError, featurize_file, featurize_text, parse_header, read_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "cyclers")
SAMPLE = os.path.join(ROOT, "app", "static", "sample_cell.csv")


@pytest.mark.parametrize("name,vendor", [("arbin.csv", "Arbin"), ("maccor.txt", "Maccor"),
                                         ("neware.csv", "Neware"), ("biologic.mpt", "BioLogic")])
def test_every_vendor_matches_the_sample_cell(name, vendor):
    ref = featurize_file(SAMPLE)["feats"]
    r = featurize_file(os.path.join(FIX, name))
    assert r["vendor"] == vendor
    for k, v in ref.items():
        assert abs(r["feats"][k] - v) < 1e-9


def test_biologic_zero_based_cycles_resolve_within_tolerance():
    assert featurize_file(os.path.join(FIX, "biologic.mpt"))["cycles"] == [9, 99]


def test_maccor_capacity_accumulates_across_discharge_steps():
    _, cycles = read_text(open(os.path.join(FIX, "maccor.txt")).read(), "maccor.txt")
    q = cycles[100]["discharge_capacity_in_Ah"]
    assert all(b >= a - 1e-12 for a, b in zip(q, q[1:]))  # no restart at the step boundary


@pytest.mark.parametrize("raw,expected", [
    ("Discharge_Capacity(Ah)", ("dischargecapacity", "ah")),
    ("Q discharge/mA.h", ("qdischarge", "mah")),
    ("<I>/mA", ("i", "ma")),
    ("DChg. Cap.(Ah)", ("dchgcap", "ah")),
    ("Cyc#", ("cyc", "")),
    ("voltage_v", ("voltagev", "")),
])
def test_parse_header(raw, expected):
    assert parse_header(raw) == expected


def test_binary_files_get_an_export_hint():
    with pytest.raises(IngestError, match="Export it"):
        read_text("", "run.ndax")


def test_friendly_errors():
    with pytest.raises(IngestError, match="too short"):
        featurize_text("cycle,voltage_v,discharge_capacity_ah\n1,3.0,0.1\n")
    with pytest.raises(IngestError, match="Could not find"):
        featurize_text("a,b,c\n" + "1,2,3\n" * 30)
    rows = "".join(f"{c},{3.3 - i * 0.01:.3f},{i * 0.01:.3f}\n" for c in (50, 60) for i in range(30))
    with pytest.raises(IngestError, match="cycle ~10"):
        featurize_text("cycle,voltage_v,discharge_capacity_ah\n" + rows)


def test_cli_scores_fixtures_like_the_browser(capsys):
    import json
    import sys
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import score_files

    score_files.main(["--json", SAMPLE, os.path.join(FIX, "maccor.txt"), "x.nda"])
    out = json.loads(capsys.readouterr().out)
    ok = [r for r in out["results"] if "error" not in r]
    assert [r["verdict"] for r in ok] == ["pass", "pass"]
    assert abs(ok[0]["p0"] - 0.717) < 1e-3 and ok[0]["p0"] == ok[1]["p0"]
    assert "binary Neware" in out["results"][2]["error"]
