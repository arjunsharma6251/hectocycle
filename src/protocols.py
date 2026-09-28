"""Parse MATR fast-charge protocol strings into numbers.

Two families share the same A123 cell:
- Severson 2019 two-step policies, "C1(Q1%)-C2": charge at C1 up to Q1% state
  of charge, then at C2 up to 80%. Batch 3 appends "-newstructure" (a changed
  rest/CV structure, kept as a flag). One source string is truncated
  ("4C(31%)-5"), read as C2 = 5C.
- Attia 2020 closed-loop policies, "CC1-CC2-CC3-CC4": four constant-current
  steps, each covering 20% of state of charge (0-80% in 10 minutes). The raw
  .mat files drop the "C" units ("4.8-5.2-5.2-4.16").
"""

import re

_SEVERSON = re.compile(r"^([\d.]+)C\(([\d.]+)%\)-([\d.]+)C?(-newstructure)?$")
_CLO = re.compile(r"^([\d.]+)C?-([\d.]+)C?-([\d.]+)C?-([\d.]+)C?$")


def parse_protocol(s):
    """{family, steps[(C-rate, SOC-from, SOC-to)], ...} or raise ValueError."""
    s = s.strip()
    m = _CLO.match(s)
    if m:
        rates = [float(x) for x in m.groups()]
        return {"family": "clo", "rates": rates,
                "steps": [(r, 20 * i, 20 * (i + 1)) for i, r in enumerate(rates)]}
    m = _SEVERSON.match(s)
    if m:
        c1, q1, c2, new = m.groups()
        c1, q1, c2 = float(c1), float(q1), float(c2)
        return {"family": "severson", "c1": c1, "q1": q1, "c2": c2,
                "newstructure": bool(new),
                "steps": [(c1, 0.0, q1), (c2, q1, 80.0)]}
    raise ValueError(f"unrecognised protocol string: {s!r}")


def charge_minutes_0_80(p):
    """Nominal time (min) to charge 0-80% SOC from the parsed step list."""
    return sum(60.0 * (hi - lo) / 100.0 / c for c, lo, hi in p["steps"])
