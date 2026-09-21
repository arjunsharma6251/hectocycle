"""Cycler-allocation policy built on the abstain rule.

The early call is only worth something if it changes what the lab does. This
module turns the per-cutoff Venn-ABERS verdicts into a stopping policy and
scores it against the conventional qualification test:

- Baseline ("run to spec"): every cell stays on the cycler until the spec
  question is answered the slow way — a fail cell runs to its end of life,
  a pass cell runs to the threshold T and is then confirmed. Cost per cell is
  min(cycle_life, T) cycles. (Running everything to EOL is the other common
  practice; it is reported as a secondary baseline.)
- "first-call" policy: at each checkpoint cutoff (40, 50, 60, 80, 100
  cycles) the model is refit with data truncated there; the first checkpoint
  whose interval clears the decision line pulls the cell off the cycler with
  that verdict. Cells never called by the last checkpoint fall back to the
  baseline.
- "confirmed-call" policy: same, but a verdict must repeat at two consecutive
  checkpoints before the cell is pulled (at the second one). This is the
  guard against the multiple-look problem: five chances to clear the line
  means five chances for a noisy interval to clear it wrongly.

Everything here is pure arithmetic over per-cell evidence timelines, so it
runs on the precomputed bundle (app/static/cockpit_data.json) with no refit.
"""

from dataclasses import dataclass, field

import numpy as np

CUTOFFS = (40, 50, 60, 80, 100)


@dataclass
class CellOutcome:
    cell: str
    label: int
    cycle_life: float
    baseline_cycles: float
    stop_cycle: float
    called_early: bool
    verdict: int  # 1 pass / 0 fail / -1 never called (fell back to baseline)
    correct: bool


@dataclass
class PolicyResult:
    name: str
    outcomes: list = field(default_factory=list)

    @property
    def n(self):
        return len(self.outcomes)

    @property
    def n_called(self):
        return sum(o.called_early for o in self.outcomes)

    @property
    def wrong(self):
        return [o for o in self.outcomes if o.called_early and not o.correct]

    @property
    def baseline_cycles(self):
        return float(sum(o.baseline_cycles for o in self.outcomes))

    @property
    def policy_cycles(self):
        return float(sum(o.stop_cycle for o in self.outcomes))

    @property
    def saved_frac(self):
        return 1.0 - self.policy_cycles / self.baseline_cycles

    def hours(self, minutes_per_cycle):
        """(baseline_hours, policy_hours) given {cell: minutes per cycle}."""
        b = sum(o.baseline_cycles * minutes_per_cycle[o.cell] for o in self.outcomes) / 60.0
        p = sum(o.stop_cycle * minutes_per_cycle[o.cell] for o in self.outcomes) / 60.0
        return b, p

    def summary(self):
        return {
            "policy": self.name,
            "n": self.n,
            "called_early": self.n_called,
            "called_frac": round(self.n_called / self.n, 3),
            "wrong_calls": len(self.wrong),
            "baseline_cycles": self.baseline_cycles,
            "policy_cycles": self.policy_cycles,
            "saved_frac": round(self.saved_frac, 3),
        }


def baseline_cycles(cycle_life, threshold):
    """Conventional cost of the spec question: fail cells run to EOL, pass cells to T."""
    return float(min(cycle_life, threshold))


def _stop_first(evidence):
    """(cutoff, verdict) of the first checkpoint whose interval clears the line."""
    for e in evidence:
        if e["call"] != -1:
            return e["cutoff"], int(e["call"])
    return None, -1


def _stop_confirmed(evidence):
    """(cutoff, verdict) once the same verdict holds at two consecutive checkpoints."""
    prev = None
    for e in evidence:
        c = int(e["call"])
        if c != -1 and prev is not None and prev == c:
            return e["cutoff"], c
        prev = c
    return None, -1


def _stop_single(evidence, at):
    e = next((x for x in evidence if x["cutoff"] == at), None)
    if e is None or e["call"] == -1:
        return None, -1
    return e["cutoff"], int(e["call"])


RULES = {
    "first-call": _stop_first,
    "confirmed-call": _stop_confirmed,
}


def simulate(cells, threshold, rule="confirmed-call", single_cutoff=None):
    """Score a stopping rule over cells = [{id, label, cycle_life, evidence:[...]}].

    `evidence` entries are {cutoff, call} in ascending cutoff order (extra keys
    ignored). `single_cutoff` scores the one-look rule at that cutoff instead.
    """
    if single_cutoff is not None:
        stopper = lambda ev: _stop_single(ev, single_cutoff)
        name = f"single@{single_cutoff}"
    else:
        stopper = RULES[rule]
        name = rule
    res = PolicyResult(name=name)
    for c in cells:
        ev = sorted(c["evidence"], key=lambda e: e["cutoff"])
        base = baseline_cycles(c["cycle_life"], threshold)
        stop, verdict = stopper(ev)
        if stop is None or stop >= base:
            # never called, or the cell would have answered itself first
            res.outcomes.append(CellOutcome(c["id"], int(c["label"]), float(c["cycle_life"]),
                                            base, base, False, -1, True))
            continue
        res.outcomes.append(CellOutcome(c["id"], int(c["label"]), float(c["cycle_life"]),
                                        base, float(stop), True, verdict,
                                        verdict == int(c["label"])))
    return res


def compare(cells, threshold, cutoffs=CUTOFFS):
    """All policies side by side: each single-look cutoff plus the two sequential rules."""
    out = [simulate(cells, threshold, single_cutoff=c) for c in cutoffs]
    out += [simulate(cells, threshold, rule=r) for r in RULES]
    return out


def saved_by_class(result):
    """Cycles saved on true-pass vs true-fail cells (where the savings come from)."""
    saved = {0: 0.0, 1: 0.0}
    for o in result.outcomes:
        saved[o.label] += o.baseline_cycles - o.stop_cycle
    return saved
