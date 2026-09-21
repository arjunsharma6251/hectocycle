---
target: app/static
total_score: 31
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "file:/Users/arjunsharma/Documents/hectocycle/app/static/index.html"
target_fingerprint: "sha256:649b53b83ad5ac115be8e93adf860886a4cdd77d75ab74bdebb250e2fd859968"
target_path: /Users/arjunsharma/Documents/hectocycle/app/static/index.html
timestamp: 2026-09-21T14-16-06Z
slug: app-static-index-html
---
Method: dual-agent (A: design review sub-agent · B: detector/browser sub-agent)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | No loading state while the 1.9 MB bundle resolves; under search, result count changes but queue cards do not |
| 2 | Match System / Real World | 4 | Domain language is fluent ("call", "come off the cycler", "channel"); TRY IT result prints raw feature names log_var_dq etc. |
| 3 | User Control and Freedom | 3 | Every row selection pushes a history entry; switching fleet silently wipes search and sort |
| 4 | Consistency and Standards | 2 | Cell counts disagree in four places (124 / 133 / 61 / 69 / 202); HELD rows show p = 1.00 under a "No verdict" banner; FAIL reuses PASS closing copy |
| 5 | Error Prevention | 3 | CSV parser guards columns, cycles, overlap; no file-size guard; search matches hidden fields with no hint |
| 6 | Recognition Rather Than Recall | 3 | Header tooltips hover-only; "P(pass ≥ T)" requires recalling T = 700; OOD badge / transfer split / out-of-envelope are three labels for overlapping ideas |
| 7 | Flexibility and Efficiency | 3 | Arrow keys, deep links, sort, search; no keyboard access to tabs or fleet switch; no export of the READY TO CALL list |
| 8 | Aesthetic and Minimalist Design | 3 | Disciplined copper and hairlines; 7–8 nowrap columns; the 46px tally persists unchanged on every tab |
| 9 | Error Recovery | 3 | TRY IT errors name the fix; bundle-load failure copy references scripts/build_bundle.py on a public site |
| 10 | Help and Documentation | 4 | Welcome sheet, ? re-open, idle manual, SCIENCE page, GATES notes; tooltips hover-only is the only deduction |
| **Total** | | **31/40** | **Good** |

## Design Specificity Verdict

**LLM assessment.** Authored, not skinned. The verdict bracket (tick = calibrated P(pass), band = Venn-ABERS interval, notch = decision line) is a genuine signature element used at three scales with one grammar, and it makes "honest abstention" visible without reading a number. Composition is decision-ordered: queue cards named for actions, a caption that says where to start, inspector banners that lead with consequence. GATES shows a pre-registered run that missed its bar with a red ✗. Where it slips: the shell is a standard admin layout (masthead + KPI tally + tabs + table + right inspector); GATES is two generic card-with-table tiles; SCIENCE and TRY IT share one editorial column pattern; every section header in the product is the same mono-uppercase eyebrow with a copper tick, so nothing signals "you are now in the high-stakes part." Two product-character opportunities are missed: hecto = 100 is the domain name and the entire premise yet appears only as a dashed line inside a 430px chart; and the biggest type on the page is a model scorecard (74% / 100% / 22) rather than the operational consequence (channels freed, cycler-days saved).

**Deterministic scan.** CLI detector on app/static: 7 warnings, 0 errors (tiny-text 10.5px, wide-tracking 0.06em, undersized-ui-text ×2 on the 10px segment captions, side-tab ×2 on .banner and .sci-callout, layout-transition on .search width). In-browser scan of the rendered SPA: 143 findings on FLEET, 153 with an inspector open, 16 visible on GATES, 32 on SCIENCE, 8 on TRY IT. Two CSS rules drive ~80% of the count: the 10.5px verdict-chip pill (×92 rows) and 9.5px column headers (×13). Light mode adds 23 low-contrast hits that do not exist in dark: #898781 on #f9f9f7 at 3.4:1 for the fleet caption, all sortable column headers, inspector labels and section heads; #f9f9f7 on copper at 4.2:1 for the numbered group badges. SCIENCE adds 14 line-length hits (~97 chars/line) and 25 em-dashes. False positives: the side-tab hits on a dismissible status banner and a blockquote-style callout; the wide-tracking hit is on a mono micro-label, which the rule itself exempts; the layout-transition is a 40px input grow on focus.

**Visual overlays.** Injection succeeded. Overlays are visible in the [Human] tab in Chrome (tab titled "[Human] Hectocycle critique", FLEET view with the b1c0 inspector open, light theme so the contrast hits show). The theme toggle was left on light; cycle it back if you prefer system. The static server has been stopped; the page stays rendered.

## Overall Impression

The product knows what it is and says so in its own words. The bracket, the queue names, the ✗ on a failed gate: those are decisions most dashboards never make. What undermines it is a handful of places where the interface contradicts its own thesis. The cells the product refuses to score still print a score. The guided first example lands a newcomer on "1.000 / KEEP TESTING / fail" with no sentence connecting them. The product cannot agree with itself about how many cells it has. And the whole type scale sits below the accessibility floor in light mode. The single biggest opportunity: make refusal the loudest state in the table, not the quietest, and put channel time where the accuracy tally is now.

## What's Working

1. **The verdict bracket at three scales.** One grammar in the table (116px), the evidence strip (210px) and the inspector (380px), decoded in the idle manual. It converts the positioning into something you can see.
2. **Verdicts written as actions.** "Call it — this cell can come off the cycler." "Reject early and reallocate the channel." "Leave on test — recheck at the next checkup." Queue names are decisions. This honours principle 4 better than most operational UIs.
3. **Failure is shown, not hidden.** The pre-registered run's missed ECE bar, the mode-sanity gate FAIL at 37%, the 0/9 → 9/9 story on SCIENCE. For the reviewer persona this is the credibility engine, and the detector confirms no invented users, logos, or claims.

## Priority Issues

**[P0] OUT OF ENVELOPE cells still print a probability and a bracket**
- Why it matters: principle 1 says the interface never shows a number the gate did not earn. The three HELD rows show "1.00" with a green band, and the inspector lists "Calibrated P(pass ≥ T) 1.000" directly under the "No verdict" banner. The bracket's aria-label reads the number to screen readers too. A reviewer who reads "refuses rather than scores" and then sees 1.00 concludes the abstention is cosmetic.
- Fix: for verdict === "out-of-envelope", render an empty rail with a dashed "refused" glyph, print "—" for p, and replace the inspector kv rows with the violating feature, its value, and the envelope bounds (TRY IT already does this with r.violations). If the withheld score must exist for engineers, put it behind a disclosure labelled "what the model would have said (not earned)".
- Suggested command: /impeccable harden

**[P1] The worked example is the right cell with the wrong narration and the wrong scroll**
- Why it matters: "See a worked example" selects b1c6 (p = 1.000, interval [0.367, 1.000], KEEP TESTING, truth = fail at 636) and scrolls the table to centre, pushing the queue cards off-screen. This is the best possible demonstration of abstention (the point estimate was wrong, the interval refused to commit, the cell died 64 cycles short) but nothing says so. The July pilot problem, "cannot tell what this does", is now concentrated in the guided path.
- Fix: keep b1c6, add a one-line guided callout at the top of the inspector ("The point estimate said pass. The interval said not yet. It died at 636. This is the abstention doing its job."), scroll with block:"nearest" after scrolling the pane to top, and number the first three inspector sections as a walk-through that dismisses on next selection.
- Suggested command: /impeccable onboard

**[P1] Cell counts disagree in four places**
- Why it matters: segment caption "Severson LFP · 124" vs result count "92 of 133 cells" with nothing filtered; "SNL · 61" vs "69 cells" (Oxford's 8 unlisted); welcome says "202 cells"; under search the count changes while queue cards still say 67/22/3/41. A reviewer judging rigor notices n first; an engineer thinks a filter is stuck.
- Fix: one vocabulary. Segment captions list all sources ("Severson 124 + SNL 9"; "SNL 61 + Oxford 8"), result count renders only when search or a queue is active, queue cards recompute from the searched set.
- Suggested command: /impeccable clarify

**[P1] The type scale sits below the accessibility floor, and light mode fails contrast**
- Why it matters: both assessments converged here independently. 9.5px column headers and tally labels, 10.5px verdict chips on every row, 10px inspector section heads and evidence rows; in light mode the muted grey (#898781 on #f9f9f7) is 3.4:1 on the caption, every column header, and every inspector label, and the copper group badges are 4.2:1. Dark mode passes contrast, which means half your reviewers see a compliant product and half do not. Header tooltips are hover-only, rows have no accessible name, tabs have no arrow-key navigation, and the welcome dialog has no focus trap or aria-labelledby.
- Fix: raise the floor to 11px for functional text and 12px for chips and headers, re-tune the light-mode muted token to ≥ 4.5:1 (about #6b6963 on #f9f9f7), add aria-sort and focusable headers, role="button" on rows, aria-controls on tabs, and a focus trap on the welcome dialog.
- Suggested command: /impeccable typeset, then /impeccable audit

**[P2] GATES small multiples use truncated axes and print 100.1% accuracy**
- Why it matters: the auto-padded y-domain runs 65–75 on "cells callable" and 98.0–100.1 on "accuracy on called". The documented cycle-60 dip is visually exaggerated and unannotated. These are the two most scrutinised charts for a hiring manager; an axis above 100% reads as carelessness on a page whose whole point is rigor. The same auto-domain clips the T = 700 reference line off every FAIL cell's capacity chart, which is exactly where the shortfall matters.
- Fix: ylim [0, 100] with accuracy clamped at 100, a labelled reference at cycle 60 ("dip — unexplained, documented"), n called under the chart; extend capacity-chart x-domain to max(cycle_life, T) and draw the shortfall.
- Suggested command: /impeccable harden

## Persona Red Flags

**Alex (impatient power user)**: clicking a queue card leaves a stale inspector for a row no longer visible; the search box is 150px at the far right with no "/" shortcut; first click on a column sorts descending, third click clears, neither discoverable; every row selection pushes history so Back becomes a tour; no export of READY TO CALL; theme toggle changes only a glyph.

**Jordan (confused first-timer)**: "1.000" beside "KEEP TESTING" beside "Ground truth: fail" with no connecting sentence; "P(pass ≥ T)" where T is defined only in a tooltip; "Venn-ABERS interval" with no in-place gloss once a row is open; OOD badge, transfer split and out-of-envelope verdict as three labels for one idea; "92 of 133 cells" with nothing filtered; in DIAGNOSTICS the idle manual teaches verdicts the table does not contain.

**Sam (screen reader, keyboard only)**: rows are tr tabindex=0 with no role or accessible name, Enter opens but Space does not; th has hover-only tooltips, no aria-sort, not focusable; #inspector is aria-live="polite" with its whole innerHTML rewritten per selection, so every arrow press announces the full record; welcome dialog has no aria-labelledby, no focus trap, no focus return; tabs have no aria-controls or arrow navigation; sparklines are aria-hidden with no text fallback; refused cells announce "P(pass) 1". Reduced motion is respected thoroughly in both CSS and JS.

**The Reviewer (AI-for-science hiring manager, 3 minutes)**: minute one lands on the 1.000/keep-testing/fail contradiction and HELD rows printing 1.00 under a sentence about refusing to guess; minute two on GATES earns trust from the ✗ rows and then loses some to a 100.1% axis and an uncaptioned cliff; "OOD 9/9 (full set 0/9)", the most important result on the site, is a 10px cell; "100% accuracy on calls" is the largest number on the page with no n beside it; counts that disagree are what a reviewer of rigor notices first. Positive: no invented users, sources cited with years, failures documented.

## Minor Observations

- FAIL verdicts reuse the PASS closing paragraph ("The interval clears the decision line…"); write fail-specific copy naming what ΔQ(V) saw.
- The 46px tally and the idle "How to read a verdict" manual are qualification-only but persist on DIAGNOSTICS, GATES, SCIENCE and TRY IT; swap per fleet, hide on non-fleet tabs.
- masthead-rev duplicates the segment captions and welcome copy; the 14px sans tagline under a 27px letterspaced mono wordmark reads as two products.
- Copper is simultaneously identity, selection state, and the ICA age-ramp data encoding; the three tints are hard to separate in dark mode.
- TRY IT result brackets bake theme colours at render; after a theme toggle the result card is stale.
- SCIENCE body runs ~97 characters per line and carries 25 em-dashes; tighten measure to ~70 and vary punctuation.
- Bundle-load failure copy ("run scripts/build_bundle.py first") is developer-facing on a public URL.
- Phone width (from source): the inspector stacks below a 100+ row table so a tap updates content off-screen; the sticky tab strip wraps to 2–3 rows; the 7-column nowrap table forces horizontal scroll. Browser resize to 390px did not take effect during the review, so this is unverified visually.
- Result count and search live in #filters but the slot is visibility:hidden on other tabs, leaving a blank in the sticky bar.

## Questions to Consider

1. If the thesis is "we tell you when not to believe the number", what would the HELD row look like if refusal were the loudest state in the table rather than the quietest?
2. The biggest type on the page is a model scorecard. What if the masthead counted channels freed and cycler-days saved today, and accuracy lived in GATES where it is earned?
3. READY TO CALL holds PASS and FAIL together because both free a channel, but one ships a design and the other kills it. Is the queue organised around the cycler's decision or the engineer's?
4. Hecto = 100. What would the interface be if "100" were its visual spine: a rail every chart shares, a position every bracket sits on?
