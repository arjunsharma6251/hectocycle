import pytest

from src.policy import baseline_cycles, compare, saved_by_class, simulate


def _cell(cid, label, life, calls):
    cutoffs = (40, 50, 60, 80, 100)
    return {"id": cid, "label": label, "cycle_life": life,
            "evidence": [{"cutoff": c, "call": v} for c, v in zip(cutoffs, calls)]}


CELLS = [
    _cell("pass_early", 1, 1500, [1, 1, 1, 1, 1]),    # confident from cycle 40
    _cell("fail_late", 0, 400, [-1, -1, -1, 0, 0]),    # callable at 80
    _cell("flicker", 1, 900, [0, -1, 1, 1, 1]),        # wrong single look at 40
    _cell("never", 1, 720, [-1, -1, -1, -1, -1]),      # keep testing throughout
    _cell("fast_fail", 0, 30, [0, 0, 0, 0, 0]),        # dies before any checkpoint
]
T = 700


def test_baseline_is_min_of_life_and_threshold():
    assert baseline_cycles(1500, T) == 700
    assert baseline_cycles(400, T) == 400


def test_first_call_takes_the_earliest_clearing_checkpoint():
    r = simulate(CELLS, T, rule="first-call")
    by = {o.cell: o for o in r.outcomes}
    assert by["pass_early"].stop_cycle == 40 and by["pass_early"].correct
    assert by["fail_late"].stop_cycle == 80 and by["fail_late"].correct
    assert by["flicker"].stop_cycle == 40 and not by["flicker"].correct
    assert not by["never"].called_early and by["never"].stop_cycle == 700
    # a cell that answers itself before the checkpoint is never "called early"
    assert not by["fast_fail"].called_early and by["fast_fail"].stop_cycle == 30
    assert [o.cell for o in r.wrong] == ["flicker"]


def test_confirmed_call_needs_two_consecutive_agreeing_looks():
    r = simulate(CELLS, T, rule="confirmed-call")
    by = {o.cell: o for o in r.outcomes}
    assert by["pass_early"].stop_cycle == 50
    assert by["fail_late"].stop_cycle == 100
    assert by["flicker"].stop_cycle == 80 and by["flicker"].correct
    assert r.wrong == []


def test_savings_accounting():
    r = simulate(CELLS, T, rule="confirmed-call")
    base = 700 + 400 + 700 + 700 + 30
    pol = 50 + 100 + 80 + 700 + 30
    assert r.baseline_cycles == base and r.policy_cycles == pol
    assert r.saved_frac == pytest.approx(1 - pol / base)
    b, p = r.hours({o.cell: 60.0 for o in r.outcomes})
    assert (b, p) == (base, pol)
    saved = saved_by_class(r)
    assert saved[1] == (700 - 50) + (700 - 80) and saved[0] == 400 - 100


def test_single_look_and_compare_shapes():
    r = simulate(CELLS, T, single_cutoff=60)
    assert r.name == "single@60" and r.n_called == 2  # pass_early, flicker (fast_fail died first)
    names = [x.name for x in compare(CELLS, T)]
    assert names == ["single@40", "single@50", "single@60", "single@80", "single@100",
                     "first-call", "confirmed-call"]
