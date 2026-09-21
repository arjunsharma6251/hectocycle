---
version: 1
slug: "app-static-index-html"
primary_target: "app/static/index.html"
related_targets: []
---

# Surface brief: the cockpit (app/static/index.html)

Scope: the whole single-page cockpit. FLEET is the primary surface (mode: Operate, reviewer-first per PRODUCT.md); GATES, SCIENCE (Read) and TRY IT inherit the world.

Audience and job: a reviewer with three minutes judging rigor and taste; a cell engineer triaging a cycler fleet. Primary task: understand the premise in one viewport, find a callable cell, read its verdict and its consequence (a channel comes free), and see what the tool refuses to call.

Proof: 133 qualification cells (Severson 124 = 41 train + 83 held-out test, plus 9 Sandia transfer), 69 diagnostics cells (Sandia 61 + Oxford 8), the callable curve, the allocation policy (60 of 83 channels freed, 0 wrong verdicts, 1,144 channel-days), the OOD 0/9 to 9/9 result. No users, testimonials or relationships exist; none are invented.

Untouched: product truth, verdict logic, in-browser scoring parity, deep links, the docs. Anti-goals: the KPI-tally-over-table dashboard; a number shown for a refused cell; a HOLD state that reads quieter than a pass.

## Direction contract

THESIS: The fleet is one control chart. Every held-out cell is an interval bar on a shared 0 to 1 rail with the 0.5 center line; a bar that clears the line is a call, a bar that crosses it is flagged, and a refused cell is the loudest mark on the chart. It refuses the masthead-tally, tab strip, table, side-card arrangement and the accuracy scorecard as the largest type on the page.

OWN-WORLD (palette user-pinned 2026-09-21: "cream/off-white and green, red only for alarming things"): Plain chart paper (user removed the rule grid on 2026-09-21: "visually noisy, simplicity matters"): cream ground (#f7f4ea) with no background pattern in light and matte black (#121212, no hue cast; user-pinned 2026-09-21) in dark, neutral near-black ink (#1a1a17) for text, the decision line, selection, focus and hover, charged-cell green (#1e9e5a) reserved for cleared passes and positive results only, ink for a cleared fail, gray-green slate for the interval band of an uncalled cell, and one signal red (#d1202f) that means alarm and nothing else: straddle pennants, refusal hatch, the diagnostics trust-bar limit, errors and shortfalls against spec. Chemistry trio blue / plum / goldenrod so no chemistry impersonates a status color. Archivo at four weights for every UI role, JetBrains Mono only for measurements and cell IDs, tabular numerals everywhere, a strict 4px baseline. No eyebrows, no section numbers, no cards inside cards, 1px rules only. Dark mode is the same chart on navy paper.

STORY: The visitor reads the one-sentence premise, sees the whole fleet as a chart with a center line, notices the red flags and understands within seconds that this tool marks what it cannot call. They click a bar or a row, the chart circles the point in red pen, and the inspector shows that cell's own run chart across cutoffs with the consequence stated first: channel freed, keep testing, or refused with the out-of-range feature named. The disposition line beneath the chart tells them what the policy did to cycler time.

FIRST VIEWPORT: At 1440 by 900: a 64px header strip with the wordmark, the premise sentence, and the four form tabs at the right. Beneath it the fleet chart at full width, 300px tall: 92 vertical interval bars ordered by queue then point estimate, the 0.5 center line labelled, straddlers flagged with red pennants, the three refused cells as red-hatched columns with flags at the top. Under the chart a disposition line in fixed-width numerals (ready to call, keep testing, held, reference) and the channel-time sentence with a cycler-hours budget bar. Below the fold: the data log table on the left, the inspector (the selected cell's run chart) on the right. The primary action is selecting a bar or row.

FORM: Control chart (Shewhart SPC), position 1 on the ordered list; chosen as Impeccable's pick over the assigned Receiving Inspection (position 6); seed key 337180d2. Raises carried from declined challengers: counters in fixed digit positions that cross-fade (nixie); hierarchy by scale on a strict baseline, no eyebrows (specimen); right-aligned running numbers and a budget bar that cannot overflow (j-card); the refusal never shrinks at any breakpoint (info-noise); text readable through every transition (storm).

MOTION (user-pinned 2026-09-21: "add animations and true design polish", Awwwards-level finish): one arrival choreography, once per fleet render and never on tab switches: the center line draws left to right, the interval bars rise out of the center line in a 4ms stagger on an exponential ease-out, the flags drop onto the straddlers and refusals, then the disposition counters cross-fade in and the log rows cascade. Signature interaction: selecting a cell draws a red pen circle around its point (stroke draw-on), drops a hairline from the point to the chart baseline, underlines the selected row in red pen, and brings the inspector sections in with a blur-to-sharp stagger. Hover on the chart dims neighbouring bars and the tooltip follows the cursor on a lerp. Tab and theme changes use the View Transitions API (theme as a circular reveal from the toggle) with a plain swap fallback. Counters change by cross-fade with a 4px vertical roll, never showing a wrong intermediate number. Browser surfaces are themed: selection, caret, focus ring, scrollbar, tabular numerals. Every motion collapses to a static render under prefers-reduced-motion. Excluded on purpose: custom cursors, split-text reveals, parallax, magnetic buttons, marquees.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
