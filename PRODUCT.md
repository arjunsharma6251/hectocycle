# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, in priority order (confirmed 2026-09-21):

1. **Reviewers of the work, first.** Hiring managers, researchers, and recruiters at battery or AI-for-science labs who arrive at hectocycle.com from a job application, a résumé, or the GitHub repo. They have a few minutes, often on a laptop between other tabs, and are judging scientific rigor, honesty, and taste. Their job: decide whether the author does outstanding work.
2. **Working cell engineers, kept real.** Cell qualification and test engineers running a life-test campaign on a cycler fleet, who would score their own cells and decide which channels to free. Every workflow must remain genuinely usable on real data for this audience, even though the first visit is designed for the reviewer.

Pilot tests (July 2026) showed first-time visitors could not tell what the app did at a glance; the arrival moment, the one-sentence tagline, and decision-ordered queues exist because of that finding.

## Product Purpose

Hectocycle answers one question for a battery cell on a life test: **will it pass, and is it honest to say so yet?** From the first 100 cycles it emits a calibrated pass/fail verdict with a distribution-free probability interval, or an explicit KEEP TESTING when the interval straddles the decision line. A second layer gives chemistry-aware degradation diagnostics (ICA/DVA curve tracking, and quantitative LLI/LAM mode attribution only where the data earns it). A third layer scores the verdict as a cycler-allocation policy: which channels can come off the cycler today, and what that saves.

Success for a reviewer: within one visit they understand the premise, see a worked example, and recognize that the method was validated gate-first with failures documented. Success for an engineer: a correct early call on their own CSV, and a defensible reason when the tool declines to call.

## Positioning

**Honest abstention.** A neighboring early-life-prediction tool predicts; Hectocycle tells you when *not* to believe the prediction. Every verdict carries a Venn-ABERS interval with distribution-free validity, a straddled interval is a KEEP TESTING rather than a guess, and inputs outside the training envelope are refused rather than scored. Every number shown in the interface survived a pre-registered, falsifiable gate; the validation studies record where the methods break and what it took to earn them back. Future work must protect this: the interface never shows a number the gate did not earn.

## Operating Context

- **Life testing as the scene.** Cells sit on cycler channels for weeks (about 49 minutes per cycle on the Severson protocol; a 700-cycle qualification is roughly three weeks). Channel time is the scarce resource; the allocation policy frees 60 of 83 test cells by cycle 100 with zero wrong verdicts, cutting cycler-hours 67%.
- **Data in play.** Severson/MATR (124 A123 LFP cells, fast-charge protocols; training + canonical test split), Sandia/SNL (61 NCA/NMC/LFP cells, 0.5C), Oxford BDD-1 (8 Kokam pouch cells with C/18.5 pseudo-OCV diagnostics). Half-cell OCP references vendored from PyBaMM parameter sets and SLIDE.
- **How it is used.** The live site runs entirely on a precomputed bundle (`app/static/cockpit_data.json`); nothing is fitted at request time. The TRY IT tab scores a user's CSV of cycles 10 and 100 in the browser with the exported production model; **nothing is uploaded anywhere**, and that privacy claim is stated in the product copy.
- **Rituals.** Fleet triage as an inbox: queue cards (READY TO CALL, KEEP TESTING, HELD — OUT OF ENVELOPE) are the filter; the inspector leads with the action ("this cell can come off the cycler"). Deep links per cell (`#qual/<id>`, `#diag/<id>`).
- **Where it lives.** https://hectocycle.com, GitHub Pages from `github.com/arjunsharma6251/hectocycle` (public, MIT), CI on every push. Local dev: FastAPI on port 8377 serving the same static files.

## Capabilities and Constraints

- Early call: ΔQ(V)-only logistic model, isotonic calibration on out-of-fold scores, cross Venn-ABERS intervals, abstain rule at 0.5, feature-envelope guard (10% margin). In-domain 0.905 accuracy / 0.043 ECE; cross-lab transfer 9/9 (the full feature set transferred 0/9 because a charge-time covariate sat ~50σ out of distribution).
- Per-cell verdict-evidence timeline: intervals refit at cutoffs 40, 50, 60, 80, 100.
- Allocation policy (`src/policy.py`): first-call vs confirmed-call stopping rules against a run-to-spec baseline; confirmed-call is the recommended rule.
- Diagnostics: ICA/DVA age evolution, fade-closure QC, mode attribution shown as a qualitative hint at 0.5C, quantitative LLI/LAM_pe with generic references at C/20, full three-way split only with chemistry-matched half-cell references (Oxford/Kokam, 8/8).
- Terminology in use: **verdict**, **call / callable**, **KEEP TESTING**, **out of envelope**, **queue**, **evidence**, **verdict bracket** (the interval rail), **gate**, **fleet**, **inspector**, cycler **channel**.
- Technical constraints: static hosting at runtime (no server on hectocycle.com), bundle currently ~1.9 MB JSON, no build step, browser-side scoring must stay parity-tested against the Python pipeline (tests at 1e-6).
- Known open question: a persistent accuracy dip at the cycle-60 cutoff, unexplained across all model variants; the product documents it rather than smoothing it over.
- Undecided: whether the allocation policy gets a surface in the cockpit (it currently lives in the study doc and README only).

## Brand Commitments

**None binding.** On 2026-09-21 the user explicitly released the current wordmark treatment, copper accent, divination voice, system-font stack, static no-build implementation, and motion system to future design work: "whatever makes it amazing." Durable facts that remain: the product is named Hectocycle (hecto- = SI prefix for one hundred; the domain is hectocycle.com), and product copy already makes the privacy claim that TRY IT uploads nothing.

## Evidence on Hand

- Validation studies with real numbers: `docs/early-call-study.md` (gate runs, callable curve, OOD transfer, allocation policy §6), `docs/degradation-modes-study.md`, `docs/mode-identifiability-study.md`.
- Figures: `figures/` (callable curve, reliability, stabilization, allocation policy, mode trajectories); screenshots in `docs/screenshots/`.
- Reproducible notebooks: `notebooks/early_call_study.ipynb`, `notebooks/degradation_modes_study.ipynb`; 29 tests in `tests/`, CI green.
- Real sample cell for TRY IT: `app/static/sample_cell.csv` (an SNL LFP transfer cell).
- **Absent, do not fabricate:** no external users, testimonials, lab adoptions, press, or customers. No Tesla, Periodic, or Dahn-lab involvement; the README's "Tesla-relevant chemistry portfolio" describes the dataset choice, not a relationship.

## Product Principles

1. **Never show a number the gate did not earn.** Abstention, envelope refusal, and muted diagnostics are features, and the interface must make them legible rather than hide them.
2. **Overview first, then zoom and filter, then details.** The missing altitude in pilot tests was between global stats and row detail; keep queue-level structure as the workflow.
3. **The first sentence explains the product.** Name plus category is not an explanation; the one guaranteed first-glance slot carries a full subject-verb sentence.
4. **Verdicts are actions.** A call means a channel comes free; design toward the decision and its consequence, not toward the chart.
5. **Reviewer-first, engineer-true.** Optimize the first visit for someone judging the work, but never at the cost of a workflow an engineer could not actually run on real data.
