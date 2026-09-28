# Batch Recalibration Study

*Can a few pilot cells per lot make early verdicts safe on a batch the model has never seen?*

**Question:** the out-of-sample study killed cross-batch verdicts. On batch 4, lives sat 18% below what the model predicted, every input looked normal, and the model called five failing cells PASS. The ΔQ(V) ranking survived, and the shift was nearly one constant offset (every protocol between −0.08 and −0.15 in log₁₀ life). So the question is whether measuring that offset on a few cells from each lot restores safe verdicts, and at what cost.

**The workflow under test: provisional pull.**
- Every cell in a lot starts together, except **k pilot cells**, which run to end of life (or to a cycle cap).
- At checkpoints up to cycle 100, the shipped classifier's confirmed-call rule pulls cells off the cycler *provisionally*. Their channels are freed at once.
- When the pilots have finished, an **audit** re-checks every pulled cell with a life interval calibrated on the lot's own pilots:
  - If the audit agrees with the pull, the verdict is final.
  - If it doesn't, the cell goes back on test. That's a **reversal**, charged as though it had never been pulled.
- The cost of the process is the pilots' cycler time plus the saving lost on reversals.

**The model** (`src/recal.py`):

log₁₀ life = x·β + α_batch + ε, with ε ~ N(0, σ_w²)

- The ΔQ(V) slope β is shared across batches, with one intercept per batch.
- It is fit on the Severson training split with separate b1 and b2 intercepts.
- For a new lot, α is estimated from its pilots. A pilot still alive at the cap is used as a censored observation (Tobit MLE).
- The prediction interval has variance σ_w²(1 + 1/k) plus the slope's uncertainty.
- Within a batch, σ_w ≈ 0.051 in log₁₀ at cycle 100, about ±12% in life. That is tighter than the pooled model, whose residual SD of 0.084 mixes in the between-batch offsets. Those offsets exist even among the training batches: b1 about +0.05, b2 about −0.05 relative to their mean.

## 0. Phase A: exploratory tuning on batches 1–4 (disclosed as adaptive)

`scripts/batch_recal_explore.py` treats each held-out batch (b1-test, b2-test, b3, b4) as a new lot, draws k random pilots 500 times, and runs provisional pull. **Batch 4 had already been seen** in the out-of-sample study, so **nothing in this section is confirmatory**; it chose the design.

Results at k = 4 (mean over draws; full sweep in `figures/batch_recal_explore*.json`):

| Lot | No audit (what ships today): wrong / saved | Audit @ 90%: wrong / saved / reversals | Audit @ 80% + pilot cap: wrong / saved / reversals / final-verdict day |
|---|---|---|---|
| b1-test (21) | 0 / 27% | 0 / 7% / 4.8 | 0 / 14% / 4.0 / day 37 |
| b2-test (22) | 0 / 37% | 0 / 32% / 0.9 | 0 / 32% / 0.8 / day 22 |
| b3 (40) | 0 / 74% | 0 / 48% / 11.5 | 0 / 61% / 6.6 / day 31 |
| **b4 (45)** | **4.54 / 61%** | **0.07** / 8% / 24.8 | **0.23** / 15% / 21.8 / day 28 |

**What Phase A found:**

1. **The audit does the safety job.** On batch 4, expected wrong final verdicts fall from 4.5 to about 0.2 with 4 pilots.
2. **The honest saving on a lot clustered near spec is small, however well the offset is known.** With the *true* offset (oracle), the 90% audit still reverses about 26 of batch 4's pulls. Within-batch scatter of ±12% means no honest interval clears T = 700 for a cell living roughly 550–850 cycles, and most of batch 4 lives there. The classifier's 61% "saving" on batch 4 was bought with its wrong calls.
3. **The batch-offset model beats shifting the pooled jackknife+ intervals.** It gave fewer reversals on b2 (0.8 vs 3.7) and b3 (6.6 vs 24), and narrower intervals. The shifted-interval variant was dropped.
4. **Audit confidence is the safety/saving dial.** On b4: 90% → 0.07 wrong, 8% saved; 80% → 0.21, 14%; 70% → 0.37, 19%; 50% → 0.74, 29%. **80% was chosen**: on a clean lot it keeps most of the saving (b3: 61% of a possible 74%).
5. **Uncapped pilots make the final verdict slow on long-lived lots.** On b1-test some pilots lived past 2,000 cycles, so verdicts took 61 days. **Capping pilots at 1.5 × T** and treating survivors as censored brought that to 37 days and slightly raised savings.
6. **The batch warning is a clue, not yet a detector.** Batch 4's median discharge capacity at cycle 2 (1.051 Ah) is below every training batch's (1.065–1.078). With four batches this is one data point. It is reported with every lot but gates nothing.

## 1. Pre-registration (committed before HUST or any new lot was scored)

**Frozen** (`scripts/batch_recal.py`; changing any of these requires a new pre-registration):

| Choice | Value |
|---|---|
| Stage-1 pulls | shipped classifier, confirmed-call rule, envelope guard (only at T = 700, the spec it was trained for) |
| Audit model | batch-offset life model, refit per checkpoint cutoff on the Severson training split |
| Pilots per lot | k = 4, drawn at random |
| Pilot cap | 1.5 × T; survivors censored |
| Audit confidence | 80% two-sided interval must clear T on the called side |
| Evaluation | 1,000 random pilot draws per lot, seed 2026 |

**Gate for a fresh lot (Phase C).** The lot must be the same cell (A123 APR18650M1A), 4C discharge at ~30 °C, not previously published, with at least 5 cells on each side of T = 700 (otherwise the lot is declared *uninformative* at T):

| Check | Pass bar |
|---|---|
| Wrong final verdicts, mean over pilot draws | ≤ 0.5 |
| Draws with at most 1 wrong final verdict | ≥ 95% |
| Coverage of the 80% pilot-calibrated interval @ 100 (non-pilot, non-refused cells) | ≥ 0.70 |
| Refused by the envelope guard | ≤ one third of the lot |
| Net cycler-cycles saved vs run-to-spec, pilots and reversals included | > 0 |

**Decision rule:**
- All pass: **BUILD**. Provisional pull becomes the cockpit's recommended workflow for new lots.
- Wrong-verdict, coverage and refusal checks pass, saving doesn't: **RESCOPE**. The audit is safe but pays nothing on that lot; ship the batch warning only.
- Wrong-verdict or coverage fails: **KILL**.

**Rehearsal gate: HUST (not a product decision).** HUST is 77 cells of the same A123 cell from BatteryLife ([Zenodo 19688272](https://zenodo.org/records/19688272), `HUST.zip`). Every cell charges on one fast-charge protocol, and each has a *different multi-stage discharge*.
- **What was seen before this section was written:**
  - BatteryLife's summary of the HUST life labels (77 cells, 1,164–2,768 cycles, median about 1,900)
  - the zip's member names
  No cell file has been opened, featurized or scored.
- **Why no verdicts at 700:** every HUST cell lives past 700, so verdicts there are meaningless. The classifier is trained for 700 only, so the rehearsal runs **life-model only** at a rehearsal spec **T_H = 1,800**, chosen from the summary median, with the pilot cap at 2,700.
- **What it checks:** the pipeline end to end on untouched data in the BatteryLife format, the refusal rate, and whether the pilot-calibrated interval still covers.
- **Checks:** coverage ≥ 0.70 and refusals ≤ one third; the lot must be informative at T_H.
- **Expectation, stated in advance:** HUST's varied discharge protocols change the discharge curves the ΔQ(V) features are computed from. A *loud* shift (many refusals) would not be a surprise, and would say the rehearsal cannot speak to the offset model.

**Label cross-check:** cycle life is recomputed from each cell's capacity (first sustained drop below 80% of nominal). Disagreements of more than 5 cycles with BatteryLife's labels are reported.

## 2. HUST rehearsal: **uninformative**

Run once by `scripts/batch_recal.py --source batterylife --T 1800` (output in `figures/batch_recal_hust-rehearsal.json`).

| Check | Result | Bar | |
|---|---|---|---|
| Refused by the envelope guard | **74 of 77 (96%)** | ≤ one third | ❌ |
| Cells with a measured life (log reaches 80% of nominal) | **0 of 77** | at least 5 on each side of T_H | uninformative |
| Coverage of the pilot-calibrated interval | not computable: no pilots | ≥ 0.70 | n/a |

The rehearsal says nothing about the offset model. Two independent reasons, the first stated in advance:

1. **Loud shift, as expected.** HUST discharges each cell on a different multi-stage protocol (for example 5C to 60% state of charge, then a lower rate). When the current steps down, the voltage jumps, and Q(V) is no longer a single smooth curve. The ΔQ(V) statistics land far outside training: |min ΔQ| is about 0.65 Ah on the first cell against about 0.01 Ah in training. The envelope guard refuses them, which is its job.
2. **No measured lives, not anticipated.** Every HUST log ends above 80% of nominal (the first cell bottoms out at 0.894 Ah against the 0.88 Ah line). BatteryLife *extrapolates* labels for cells that end between 80% and 82.5%. Under the pre-registered rule these are censored, so there are no pilots to calibrate on. Using BatteryLife's extrapolated labels instead would be a deviation from the pre-registration, and it would not rescue the rehearsal given reason 1.

**What it changes:** it turns two assumptions in the Phase C data requirements into hard requirements:
- **constant-current discharge** at the Severson rate (4C to 2.0 V)
- **logs that run past 80% of nominal capacity**

*Note:* the raw-curve featurizer was later clipped to Severson's 2.0–3.5 V window (see the out-of-sample study, deviation note). The rehearsal was run before that change and was not rerun; reason 2 (no measured lives) makes it uninformative either way.

The pipeline itself ran end to end on untouched BatteryLife data: loading, featurizing at every checkpoint, the envelope guard, and a clean "uninformative" verdict instead of a crash or a number.

## 3. Status

Phase C, a fresh lot, is the only remaining test that can decide this study. The data it needs:
- the same cell (A123 APR18650M1A)
- at least 20 cells from one unpublished lot
- 4C constant-current discharge to 2.0 V at about 30 °C
- fast-charge protocols giving lives near 700
- each cell logged from cycle 1 to below 80% of nominal
- text exports from any supported cycler

One command then runs the frozen gate:

```bash
.venv/bin/python scripts/batch_recal.py --source files --paths lot/*.csv --name <lot> --minutes-per-cycle <measured>
```
