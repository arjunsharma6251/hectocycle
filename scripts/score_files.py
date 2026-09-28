"""Score cycler files from the command line, exactly as the TRY IT tab does.

Reads each file (Arbin / Maccor / Neware / BioLogic text exports, or the
three-column Hectocycle CSV), computes the DeltaQ(V) features and scores them
with the exported production model in app/static/cockpit_data.json.

    .venv/bin/python scripts/score_files.py cell_01.csv cell_02.mpt ...
    .venv/bin/python scripts/score_files.py --json runs/*.txt > verdicts.json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.ingest import IngestError, featurize_file  # noqa: E402
from src.scoring import score_features  # noqa: E402

BUNDLE = os.path.join(ROOT, "app", "static", "cockpit_data.json")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args(argv)

    qual = json.load(open(BUNDLE))["qual"]
    results = []
    for path in args.files:
        try:
            f = featurize_file(path)
            r = score_features(qual["model"], qual["envelope"], f["feats"])
            results.append({"file": path, "vendor": f["vendor"], "cycles": f["cycles"], **r, "feats": f["feats"]})
        except (IngestError, OSError) as e:
            results.append({"file": path, "error": str(e)})

    if args.json:
        json.dump({"threshold": qual["threshold"], "results": results}, sys.stdout, indent=1)
        print()
        return
    print(f"spec: cycle life >= {qual['threshold']}  (verdicts are calibrated for the Severson batches only;"
          " see docs/out-of-sample-study.md)")
    w = max(len(os.path.basename(r["file"])) for r in results)
    for r in results:
        name = os.path.basename(r["file"]).ljust(w)
        if "error" in r:
            print(f"{name}  error: {r['error']}")
            continue
        interval = f"P {r['p']:.3f}  [{r['p0']:.3f}, {r['p1']:.3f}]"
        why = f"  ({', '.join(r['violations'])} outside envelope)" if r["violations"] else ""
        print(f"{name}  {r['vendor']:<14} {r['cycles'][0]:>3}->{r['cycles'][1]:<4} {r['verdict']:<16} {interval}{why}")


if __name__ == "__main__":
    main()
