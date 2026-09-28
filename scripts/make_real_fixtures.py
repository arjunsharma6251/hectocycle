"""Thin real cycler exports into small committed fixtures (tests/fixtures/real/).

Sources are test files from TRI's beep (Apache-2.0, see tests/fixtures/real/NOTICE),
downloaded into data/real_exports/. Each fixture keeps the file's own preamble,
header and every structural row (cycle and step rows in nested Neware files)
but only every Nth data row and the first few cycles, so the parser is tested
on genuine vendor layout at a size CI can carry.

    .venv/bin/python scripts/make_real_fixtures.py
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "real_exports")
OUT = os.path.join(ROOT, "tests", "fixtures", "real")

BEEP = "https://github.com/TRI-AMDD/beep/tree/main/tests/test_files"
# (source, fixture name, encoding, header lines to keep verbatim, cycle column index or None, keep every Nth row, max cycle)
SPECS = [
    ("2017-12-04_4_65C-69per_6C_CH29.csv", "arbin_matr_fastcharge.csv", "utf-8", 1, 5, 10, 3),
    ("xTESLADIAG_000019_CH70.070", "maccor_diagnostic.070", "latin-1", 2, 1, 10, 2),
    ("test_loopsnewoutput_MB_CE1_short10k.txt", "biologic_btlab.mpt", "latin-1", 102, None, 60, 2),
]


def thin_table(lines, keep_head, cyc_col, every, max_cycle):
    out = lines[:keep_head]
    data = lines[keep_head:]
    delim = "\t" if "\t" in lines[keep_head - 1] else ","
    for i, ln in enumerate(data):
        if not ln.strip():
            continue
        if cyc_col is not None:
            f = ln.split(delim)
            try:
                if float(f[cyc_col]) > max_cycle:
                    break
            except (ValueError, IndexError):
                pass
        if i % every == 0:
            out.append(ln)
    return out


def thin_biologic(lines, keep_head, every, max_cycle):
    head = lines[:keep_head]
    cols = head[-1].split("\t")
    ci = next(i for i, c in enumerate(cols) if c.strip().lower() == "cycle number")
    out = list(head)
    for i, ln in enumerate(lines[keep_head:]):
        f = ln.split("\t")
        if len(f) > ci and float(f[ci].replace(",", ".")) > max_cycle:
            break
        if i % every == 0:
            out.append(ln)
    return out


def thin_neware_nested(lines, every, max_cycle):
    out = lines[:3]
    cyc, rec = 0, 0
    for ln in lines[3:]:
        first = ln.split(",")[0].strip().strip('"').strip()
        if first:
            cyc = int(float(first))
            if cyc > max_cycle:
                break
            out.append(ln)
        elif re.match(r'^,\s*"?\s*\d', ln) or re.match(r'^,"\t\d', ln):  # step row
            out.append(ln)
        else:
            rec += 1
            if rec % every == 0:
                out.append(ln)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    made = []
    for src, name, enc, head, cyc_col, every, max_cycle in SPECS:
        lines = open(os.path.join(SRC, src), encoding=enc, newline="").read().splitlines(keepends=True)
        if name.endswith(".mpt"):
            kept = thin_biologic(lines, head, every, max_cycle)
        else:
            kept = thin_table(lines, head, cyc_col, every, max_cycle)
        open(os.path.join(OUT, name), "w", encoding=enc, newline="").write("".join(kept))
        made.append((src, name))
    lines = open(os.path.join(SRC, "neware_test.csv"), encoding="latin-1", newline="").read().splitlines(keepends=True)
    open(os.path.join(OUT, "neware_nested.csv"), "w", encoding="latin-1", newline="").write(
        "".join(thin_neware_nested(lines, 10, 3)))
    made.append(("raw/neware_test.csv", "neware_nested.csv"))
    with open(os.path.join(OUT, "NOTICE"), "w") as fp:
        fp.write("Fixtures in this directory are thinned excerpts of test files from TRI's beep\n"
                 f"({BEEP}), Copyright Toyota Research Institute, licensed under the Apache License 2.0\n"
                 "(http://www.apache.org/licenses/LICENSE-2.0). Modification: data rows subsampled and\n"
                 "truncated to the first cycles by scripts/make_real_fixtures.py; headers kept verbatim.\n\n")
        for src, name in made:
            fp.write(f"{name}  <-  {src}\n")
    for _, name in made:
        print(f"{name:32s} {os.path.getsize(os.path.join(OUT, name)) / 1024:7.1f} KB")


if __name__ == "__main__":
    main()
