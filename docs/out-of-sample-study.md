# Out-of-Sample Validation Study

*Does the early call hold on cells it has never seen, from a batch run a year later?*

**Question:** the early-call study ([early-call-study.md](early-call-study.md) §2) ended at "RESCOPE → BUILD, pending revalidation of calibration on untouched data". Every number so far comes from the three Severson batches, and the only cross-lab check (SNL LFP, §5 there) is single-class. This study is the pending revalidation.

**Data:** MATR batch 4 ("b4"): Attia et al. 2020 (*Nature* 578, 397) validation batch, via the BatteryLife processed mirror ([Zenodo 19688272](https://zenodo.org/records/19688272), `MATR.zip`). 45 A123 APR18650M1A cells (same cell model as Severson), 9 closed-loop-optimized fast-charge protocols × 5 replicates, same 4C discharge, 30 °C, run to 80% of nominal capacity. The cells sat on the shelf longer before testing than batches 1–3, and Attia's own early predictor over-estimated their lives. That makes this a real distribution shift, not a resample.

## 0. Pre-registration (committed before any b4 feature was computed)

**What was seen before this section was written:** the BatteryLife life-label distribution for b4 (45 cells, 442–1081 cycles, 14 below T = 700). This is needed to confirm the test is two-sided. No b4 voltage curve, feature, or prediction had been computed.

**Model under test:** the production model exactly as shipped in the cockpit. That means ΔQ(V)-only `EarlyVerdictModel` (point probability) + cross Venn-ABERS interval, trained on the 41 Severson training cells, T = 700, cutoff cycle 100, envelope guard with 10% margin. No refit, no recalibration, no feature change after this commit.

**Featurizer pre-condition (not the gate):** b4 comes as raw per-cycle curves, while the model was trained on Severson's pre-interpolated `Qdlin`. The raw-curve featurizer must first reproduce the `Qdlin` features on the Severson cells in the same mirror (b1–b3): median |Δ| < 0.05 on each of the three log-features and Spearman ρ > 0.98. If it fails, the featurizer is fixed (on b1–b3 only) before b4 is scored.

**Labels:** cycle life = first cycle after cycle 1 where discharge capacity < 0.88 Ah and stays below at the next cycle (the `src/data.py` rule), cross-checked against BatteryLife's labels; any disagreement > 5 cycles is reported.

**Gate (b4, n = 45, refused cells excluded from the metrics but counted):**

| Metric | Pass bar |
|---|---|
| Balanced accuracy of the point call @ 100 | ≥ 0.85 (same bar as the original gate) |
| ECE of the point probability @ 100 (10 bins) | ≤ 0.10 (same bar) |
| Accuracy on cells the interval calls @ 100 | ≥ 0.90 |
| Confirmed-call allocation policy (`src/policy.py`) wrong verdicts | ≤ 1 |
| Cells refused by the envelope guard | ≤ 15 (one third) |

**Decision rule:**
- All five pass: **BUILD**. b4 joins the cockpit as a validated fleet.
- Calibration (ECE) fails but called-accuracy and the policy pass: **RESCOPE**. The interval and abstain product stands, and the point probability is labelled in-domain only.
- Called-accuracy or the policy fails: **KILL** for cross-batch use. The early call is shown only for Severson-like batches, and the failure is published here.

**Descriptive, not gated:**
- Direction of bias (predicted vs true life).
- Callable curve across cutoffs 40–100.
- Allocation-policy savings on b4.
- Per-protocol error.
