"""Loader for MATR batch 4: the Attia et al. 2020 validation batch.

Same A123 APR18650M1A cell and .mat layout as the three Severson batches
(src/data.py), cycled a year later under nine closed-loop-optimized
four-step fast-charge protocols (5 replicates each), run to 80% capacity.
Used as untouched out-of-sample data in docs/out-of-sample-study.md.

Raw file (~2.6 GB) from data.matr.io:
  https://data.matr.io/1/api/v1/file/5dcef152110002c7215b2c90/download
Save into data/ as 2019-01-24_batchdata_updated_struct_errorcorrect.mat.
"""

import json
import os
import pickle

from .data import compute_cycle_life, load_batch

B4_FILE = "2019-01-24_batchdata_updated_struct_errorcorrect.mat"


def load_b4(data_dir, cache=True, verbose=True):
    """{b4c<i>: cell_dict} with Qdlin for cycles <= 105 and computed cycle_life."""
    cache_path = os.path.join(data_dir, "b4_slim.pkl")
    if cache and os.path.exists(cache_path):
        with open(cache_path, "rb") as fp:
            return pickle.load(fp)
    if verbose:
        print(f"parsing {B4_FILE} ...")
    cells = load_batch(os.path.join(data_dir, B4_FILE), "b4")
    for cell in cells.values():
        cell["cycle_life"] = compute_cycle_life(cell)
    if cache:
        with open(cache_path, "wb") as fp:
            pickle.dump(cells, fp)
    return cells


def batterylife_labels(data_dir):
    """{b4c<i>: life} from BatteryLife's MATR_labels.json, if downloaded."""
    path = os.path.join(data_dir, "matr", "life_labels", "Life labels", "MATR_labels.json")
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path))
    return {k.replace("MATR_", "").replace(".pkl", ""): float(v)
            for k, v in raw.items() if k.startswith("MATR_b4")}
