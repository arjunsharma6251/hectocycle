import pytest

from src.protocols import charge_minutes_0_80, parse_protocol


def test_clo_four_steps():
    p = parse_protocol("4.8C-5.2C-5.2C-4.160C")
    assert p["family"] == "clo"
    assert p["rates"] == [4.8, 5.2, 5.2, 4.16]
    # Attia's policies are designed to charge 0-80% in 10 minutes
    assert charge_minutes_0_80(p) == pytest.approx(10.0, abs=0.05)
    assert parse_protocol("4.8-5.2-5.2-4.16")["rates"] == [4.8, 5.2, 5.2, 4.16]


def test_severson_two_step():
    p = parse_protocol("5.4C(40%)-3.6C")
    assert (p["c1"], p["q1"], p["c2"], p["newstructure"]) == (5.4, 40.0, 3.6, False)
    assert p["steps"] == [(5.4, 0.0, 40.0), (3.6, 40.0, 80.0)]


def test_severson_variants():
    assert parse_protocol("5.3C(54%)-4C-newstructure")["newstructure"] is True
    assert parse_protocol("4C(31%)-5")["c2"] == 5.0  # truncated source string


def test_rejects_garbage():
    with pytest.raises(ValueError):
        parse_protocol("CCCV 1C")
