---
name: Hectocycle
description: The cycler fleet as one control chart on plain cream paper, with colour that only ever means something.
colors:
  paper: "#f7f4ea"
  surface: "#fffdf7"
  ink: "#1a1a17"
  ink-2: "#45463f"
  muted: "#62635c"
  rule: "#d9d6cb"
  rule-soft: "#e9e6da"
  ink-wash: "rgba(26, 26, 23, 0.06)"
  red: "#d1202f"
  red-wash: "rgba(209, 32, 47, 0.09)"
  green: "#1e9e5a"
  green-text: "#157a44"
  green-wash: "rgba(30, 158, 90, 0.12)"
  slate: "#8d8f88"
  slate-wash: "rgba(141, 143, 136, 0.18)"
  chem-nca: "#2f6fd6"
  chem-nmc: "#a24a8a"
  chem-lfp: "#b8860b"
  chem-kokam: "#6b5fc9"
  age-1: "#c9c8bf"
  age-2: "#7b7c74"
typography:
  display:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  subtitle:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "normal"
  body:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  reading:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "normal"
  label:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "0.02em"
  measure:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "12.5px"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "normal"
    fontFeature: "tabular-nums"
  measure-large:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "26px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "normal"
    fontFeature: "tabular-nums"
  axis:
    fontFamily: "JetBrains Mono, ui-monospace, Menlo, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "normal"
rounded:
  mark: "2px"
  panel: "4px"
  field: "6px"
  sheet: "12px 12px 0 0"
  pill: "999px"
spacing:
  hair: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "22px"
  xl: "28px"
  gap: "32px"
  gutter: "48px"
  gutter-phone: "20px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: "11px 20px"
  button-primary-hover:
    backgroundColor: "{colors.ink-2}"
    textColor: "{colors.paper}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    padding: "6px 2px"
  button-quiet-hover:
    textColor: "{colors.ink}"
  button-tool:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    size: "34px"
  button-tool-hover:
    textColor: "{colors.ink}"
  segment:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.pill}"
    padding: "7px 16px"
  segment-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  tab:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.body}"
    padding: "12px 14px 16px"
  tab-active:
    textColor: "{colors.ink}"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "7px 12px"
    width: "190px"
  disposition-count:
    backgroundColor: "transparent"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.field}"
    padding: "6px 12px 6px 10px"
  disposition-count-pressed:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
  panel-inspector:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "22px 28px"
  consequence-pass:
    backgroundColor: "{colors.green-wash}"
    textColor: "{colors.green-text}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  consequence-fail:
    backgroundColor: "{colors.ink-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  consequence-keep-testing:
    backgroundColor: "{colors.slate-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  consequence-out-of-envelope:
    backgroundColor: "{colors.red-wash}"
    textColor: "{colors.red}"
    rounded: "{rounded.panel}"
    padding: "12px 14px"
  chart-tip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.field}"
    padding: "8px 11px"
---

# Design System: Hectocycle

## Overview

**Creative North Star: "The Control Chart"**

Hectocycle is one Shewhart control chart, and everything else on the page is the chart's paperwork. The fleet of held-out cells sits as interval bars on a shared 0 to 1 rail with the decision line drawn across it; a bar that clears the line is a call, a bar that straddles it wears a red pennant, and a cell the model refuses to score is a red-hatched column, the loudest mark on the page. The ground is plain cream chart paper in light and matte black in dark, with no grid, no texture and no pattern behind the data. Density is high but calm: one hairline rule separates the chart from the disposition line, one separates the log from its header, and the inspector is the only surface that lifts off the paper.

Colour is a signal, never decoration. There are exactly four meanings: green for a cleared pass or a positive result, red for an alarm and nothing else, neutral ink for text and every interaction state, and gray for waiting. Four chemistry hues are categorical and keep clear of all four meanings so no chemistry ever impersonates a status. Archivo carries every UI role at four weights; JetBrains Mono appears only where a measurement or a cell ID is being read. Numerals are tabular everywhere, so counts and hours never jitter as they change.

Motion is a single arrival choreography (the decision line draws, the bars rise from it, the flags drop, the counters and rows follow) plus one selection signature (an ink pen circle draws around the chosen point, a hairline drops to the baseline, the inspector sharpens in). Tabs and the theme toggle use the View Transitions API, the theme as a circular reveal from the toggle. Every motion collapses to a static render under `prefers-reduced-motion`. Confirmed rejections: the KPI-tally dashboard, decorative gradients, background grids, eyebrows and section numbers, cards inside cards, and any number shown for a refused cell.

**Key Characteristics:**
- One chart is the page; tables, counters and the inspector serve it
- Cream paper (#f7f4ea) or matte black (#121212), never patterned, never hue-cast
- Four colour meanings (green cleared, red alarm, ink neutral, gray waiting) plus a categorical chemistry quartet
- Archivo for every UI role; JetBrains Mono for measurements and IDs only; tabular numerals throughout
- 1px hairline rules, 4px panel corners, 999px pills; depth by one soft lift on the inspector
- One arrival choreography, one selection signature, all reduced-motion aware

## Colors

A warm neutral paper carrying an ink voice, with green and red rationed to their meanings and a chemistry quartet kept categorical; dark mode swaps every token for a matte black counterpart with no hue cast.

### Primary
- **Charged Green** (`green`): the fill of a cleared pass bar and its point, the pass swatch, the in-envelope band and the accuracy line on the Gates tab. Its wash (`green-wash`) tints the pass consequence block and the saved-hours stripe of the budget bar.
- **Cleared Green Text** (`green-text`): the darker green used wherever green must carry type: the pass verdict word, the "ready to call" count, hours saved, the run-chart pass call, the pass check on Gates. Never use the fill green for text.

### Secondary
- **Signal Red** (`red`): alarm only. Straddle pennants, the refusal hatch pattern and held swatch, the diagnostics trust-bar limit line and its label, the envelope marker on a refused cell, the "held" count, the unstable diagnostics point, the shortfall annotation on a fade curve, the low-ρ figure, the Gates fail check, and error blocks. `red-wash` tints the out-of-envelope consequence block and the TRY IT error block.

### Tertiary (categorical chemistry quartet)
- **NCA Blue** (`chem-nca`), **NMC Plum** (`chem-nmc`), **LFP Goldenrod** (`chem-lfp`), **Kokam Violet** (`chem-kokam`): chemistry dots in the log, fade-curve strokes on diagnostics, the quantitative and featured bars on the mode-stability chart, and the LLI / LAM_pe / LAM_ne mode traces. Each is lifted and desaturated in dark mode. None of the four sits near green or red.
- **Age Ramp** (`age-1`, `age-2`, then `ink`): three strokes for early, mid and late cycle in ICA/DVA small multiples; a lightness ramp, not a hue.

### Neutral
- **Paper** (`paper`): the page ground and the table header ground; also the text colour on ink-filled controls (pressed segment, primary button, tooltip) and the ring around chart points.
- **Surface** (`surface`): the slightly brighter sheet for panels that sit on paper: the inspector, tool buttons, the fleet switch, search field, callouts, the welcome dialog.
- **Ink** (`ink`): body text, the decision line, the fail bar and fail verdict, selection ring and drop line, the selected-row underline, focus outline, hover borders, the budget-bar used fill, the tooltip ground, and the strong borders on the header, disposition line and inspector.
- **Ink 2** (`ink-2`): secondary prose (the premise, reading paragraphs, notes), table headers, tool-button glyphs, and the hover colour of the primary button.
- **Muted** (`muted`): waiting text: axis labels, source lines, inactive tabs and segments, placeholders, the "reference" count, the run-chart keep call.
- **Slate** (`slate`): the waiting mark: the keep-testing interval band, the hatched muted column, the reference swatch outline, dashed reference lines on line charts, the dropzone dash. `slate-wash` tints the keep-testing consequence block and the envelope rail.
- **Rule** (`rule`) and **Rule Soft** (`rule-soft`): the two hairline greys. `rule` for panel borders, the chart's 0 and 1 rails, group separators and header underlines; `rule-soft` for table row dividers and chart gridlines.
- **Ink Wash** (`ink-wash`): row hover and selection ground, the guided block ground, the search focus halo, the dropzone hover ground.

### Named Rules
**The Four Meanings Rule.** Green means cleared or positive, red means alarm, ink is the neutral voice, gray means waiting. A colour that appears without one of these four meanings is a defect. Chemistry hues are categorical and never carry a status.

**The Ink Interaction Rule.** Selection, focus, hover and the decision line are ink, never red and never green. Red is spent only on things that must be acted on: a straddled interval, a refusal, a limit, an error.

**The Plain Paper Rule.** The ground is one flat colour: cream in light, matte black in dark. No grid, no noise, no gradient, no hue cast behind the data.

## Typography

**Display Font:** Archivo (with Helvetica Neue, Arial, sans-serif), self-hosted variable, weights 400 to 700, Latin subset
**Body Font:** Archivo (same face; there is one UI voice)
**Label/Mono Font:** JetBrains Mono (with ui-monospace, Menlo, monospace), self-hosted variable, weights 400 to 600

**Character:** A plain grotesk doing every job at a small size, tightened slightly at the few large sizes, with a monospace reserved so strictly for measurements that a mono glyph reads as "this is a number you can trust". Numerals are tabular on the body element, so every count, hour and probability lines up and rolls in place.

### Hierarchy
- **Display** (600, 30px, line-height 1, -0.02em): the disposition counters (ready to call, keep testing, held, reference). Drops to 24px under 960px. The same 30px at 700 is the Read register's h2 on Science and Try it (26px on phones); the welcome dialog title is a 28px cousin (24px on phones).
- **Headline** (700, 20px, 1.1, -0.02em): the wordmark. Gate titles and Read h3 are 18–19px at 700 with -0.01em.
- **Title** (600, 18px, -0.01em, balanced wrap): the chart's one-sentence title. Data log title 15px at 600; inspector idle title 15px at 700; inspector section heads 13px at 700.
- **Body** (400, 14px, 1.5): the base. The premise runs 15px in `ink-2` at a 56ch measure; reading paragraphs run 15px at 1.7 in a 68ch column; table cells 13.5px; controls and secondary lines 13px; notes, sub-lines and legend text 12.5px.
- **Label** (600, 12px, 0.02em): chart group titles, table headers (600, 12px, `ink-2`), verdict words (600, 12.5px, 0.01em). Never uppercased; there are no eyebrows in this system.
- **Measure** (JetBrains Mono 500, 12.5–13px): cell IDs, probabilities, cycle-life deltas, chemistry codes, the result count, the budget label, key-value figures. Larger measures: inspector title 16px at 600, mode name 18px at 600, transfer result and reading stats 26px at 600.
- **Axis** (JetBrains Mono, 11px, `muted`): chart tick labels; axis titles and series labels are Archivo 11px.

### Named Rules
**The Mono Is A Measurement Rule.** JetBrains Mono appears only on a value that was measured, computed or identifies a cell. Prose, labels, buttons and headings never use it.

**The One Scale Step Rule.** The only large type on the Fleet surface is the four disposition numerals at 30px. Nothing else on that surface exceeds 20px; the chart title is 18px so the chart stays the largest thing.

## Layout

The page is a single column of full-width bands under a header strip, each band separated by one 1px rule, with a 48px gutter on both sides (20px under 960px). The header is a three-column grid (brand, tabs, tools) aligned to its bottom edge and closed by a 1px ink rule. The chart head places the fleet switch beside a balanced one-line title and a muted source line. The fleet chart is a full-width responsive SVG, 300px tall (200px under 960px), with a left axis gutter of 46px and top padding of 34px for group labels and pennants (50px when the plot is narrower than 620px). The disposition line beneath it is `auto 1fr`: count buttons on the left, the channel-time sentence and budget bar (max 640px) on the right, separated by a 1px ink rule above and a hairline below.

Below the fold the log and inspector share a `minmax(0, 1fr) 460px` grid with a 32px column gap (400px and 24px under 1180px). The inspector is sticky at 16px from the top with a viewport-bounded max height. Gates is an `auto-fit, minmax(440px, 1fr)` grid with a 56px column gap capped at 1320px. Science and Try it use a centred 68ch reading column with 48px vertical padding.

Spacing leans on multiples of 4 (4, 8, 12, 16, 22–24, 28, 32, 40, 48) but is not a strict baseline: tight controls use 6, 7, 10, 11 and 14px paddings and type sits at 11.5, 12.5 and 13.5px where a half step read better. Record and reuse those values rather than rounding them.

Under 960px the header collapses to brand and tools on one row with the tab strip scrolling horizontally beneath; the chart head stacks; disposition counts form a two-column grid at 24px numerals; optional log columns (`.col-opt`) hide; and the inspector leaves the flow to become a fixed bottom sheet (72vh max, 12px top corners, slides up on selection, hidden when idle). On the narrow chart the group labels shorten to their first word, per-bar pennants are withheld and one clustered pennant with the straddler count stands in for them, while the refused columns keep their full-size flags at every width.

## Elevation & Depth

Hectocycle is flat by default and conveys depth by tonal layering: paper for the page, surface for anything that sits on it, and 1px rules where one band ends. Two soft, diffuse shadows exist and each has one job. Nothing else casts a shadow; hovers are answered by border-colour and a 1px translate, not by lift.

### Shadow Vocabulary
- **Lift** (`box-shadow: 0 1px 2px rgba(26, 26, 23, 0.06), 0 8px 18px -10px rgba(26, 26, 23, 0.22)`; dark: `0 1px 2px rgba(0,0,0,0.5), 0 8px 18px -10px rgba(0,0,0,0.7)`): the inspector, the TRY IT result panel, the welcome dialog and the chart tooltip: surfaces that hold the selected object.
- **Sheet** (`box-shadow: 0 -8px 40px -12px rgba(26, 26, 23, 0.35)`; dark alpha 0.8): the phone bottom sheet only, cast upward.
- **Focus halo** (`box-shadow: 0 0 0 3px var(--ink-wash)`): the search field on focus, alongside an ink border. All other focus is a 2px ink outline offset 3px.

### Named Rules
**The One Lift Rule.** Only the surface that holds the selected cell (inspector, result panel, dialog, tooltip) lifts off the paper. Bands, tables, counts and charts stay flat and are separated by rules.

## Shapes

The form language is a drafting instrument: straight 1px rules, small square-ish corners on panels, and full pills on anything you press with a fingertip. Panels, consequence blocks, callouts and result frames take 4px corners; interactive fields and the floating tooltip take 6px; tiny marks (swatches, the budget bar, the envelope rail) take 2px; the phone sheet rounds only its top corners at 12px. Tool buttons, the fleet switch and its segments, the primary button and the inspector close are 999px pills. Chart marks are rounded rectangles (bar corners at half the bar width) with a point ringed in paper. Borders are 1px in `rule`, or 1px in `ink` when the edge is structural (the header's bottom, the disposition line, the inspector, the gate title underline, callouts). The only heavier strokes are chart instruments: the decision line at 1.25, the interval rail at 1.5, the selection ring at 1.75, the dropzone's 1.5px dash, and the selected-row underline at 1.5px. Refusal is a 45-degree hatch (6px tile, 1.1 stroke) in red; the "muted" diagnostics column uses the same hatch in slate.

## Components

### Buttons
- **Shape:** full pill (999px) for the primary; no shape at all for the quiet button.
- **Primary:** ink on paper text, 1px ink border, 11px 20px padding, 600 at 14px. Used once, in the welcome dialog.
- **Hover / Focus:** ground shifts to `ink-2` and the button rises 1px; active presses to scale 0.98. Focus is the global 2px ink outline.
- **Quiet:** bare `muted` text at 13.5px; hover turns ink and underlines with a 3px offset.
- **Tool (icon):** a 34px pill on surface with a 1px rule border and an `ink-2` 16px inline SVG glyph; hover darkens the border and glyph to ink and rises 1px.
- **Segment (fleet switch):** a pill group on surface with 3px inner padding; each segment 7px 16px at 500/13px in `muted`; the pressed segment is filled ink with paper text.
- **Disposition count:** a transparent 6px-radius button carrying a 10px swatch, a 30px numeral and a lowercase label; hover shows a rule border, pressed shows an ink border on surface. The numeral is tinted by meaning (green-text, red, muted, or ink).
- **Sort header:** the table header text itself, with a 9px chevron that appears only when that column is sorted.

### Chips
- **Verdict word:** inline 600 at 12.5px with a 9px square swatch before it: green fill and green-text for pass, ink for fail, slate square with `ink-2` text for keep testing, an outlined square with muted 500 text for reference, and no square for out-of-envelope, which is red text preceded by the pennant glyph.
- **Chemistry code:** JetBrains Mono 600 at 12.5px after a 9px circle in the chemistry hue.
- **Tooltip verdict tag:** 11px 600 on a 3px corner inside the ink tooltip; pass on green, fail on white, keep-testing on slate, out-of-envelope on red.
- **Legend swatches:** 10px squares at 2px radius; the held and muted swatches carry the hatch as a repeating gradient with a 1px border in their colour.

### Cards / Containers
- **Corner Style:** 4px.
- **Background:** surface for the inspector, callouts and result frames; paper for the page itself and the table header.
- **Shadow Strategy:** Lift on the inspector, result panel and welcome dialog only.
- **Border:** 1px ink.
- **Internal Padding:** 22px 28px for inspector sections (30px 28px when idle); 18px 20px for reading callouts; 16px 18px for the transfer result; 40px 44px for the welcome dialog.

### Inputs / Fields
- **Search:** 13px on surface with a 1px rule border, 6px corners, 7px 12px padding, 190px wide; placeholder in `muted`.
- **Focus:** border turns ink and a 3px ink-wash halo appears; the native cancel glyph is suppressed.
- **Dropzone:** a 1.5px slate dash on surface with 6px corners and 44px 24px padding; hover or drag turns the dash ink and the ground ink-wash, drag scales to 1.01.
- **Error:** a red-wash block with red 500 text at 13.5px and 4px corners.

### Navigation
- **Form tabs:** four bare text tabs at 500/14px in `muted` with 12px 14px 16px padding; the active tab is ink with a 2px ink underline that scales in from the left over 0.35s and sits 1px below the header rule so it closes the rule. Hover turns ink. Under 960px the strip scrolls horizontally with its scrollbar hidden. Tab switches run through a 0.35s root View Transition.
- **Skip link:** an ink pill with paper text that drops in at 12px from the top on focus.

### Fleet Control Chart (signature)
A full-width SVG on the paper with a 1px rule at 0 and 1, a 1px ink y-axis, and the decision line (ink, 1.25, labelled "decision line 0.5") or, on Diagnostics, the trust bar (red, 1px, 5 4 dash, labelled "trust bar ρ ≥ 0.8"). Cells are grouped by queue with 20px gaps and a 2 4 dashed rule separator; each group is titled in Archivo 600/12px with its count in mono. An interval bar is a rounded rect from the interval's low to high (width min(9, 55% of the slot)) with a point circle ringed in paper; green for pass, ink for fail, slate for keep testing. Straddlers carry an 11 by 13 red pennant above the bar; refused cells are red-hatched columns spanning the plot with the pennant above. Hovering dims every other bar to 45% opacity and shows an ink tooltip with the cell ID in mono and a verdict tag. Selection draws an ink ring (r 8.5, stroke 1.75, dash draw-on) around the point and a 2 3 dashed ink drop line from the point to the baseline. Filtered-out bars fade to 18%.

### Disposition Line and Budget Bar (signature)
A band closed by a 1px ink rule above and a hairline below. Left: the count buttons, whose numerals roll in with a 4px rise on change. Right: the channel-time sentence with bold figures and a 10px budget bar with a 1px ink border and 2px corners, striped in green-wash for the hours saved and filled ink for hours used (a scaleX transform, so it cannot overflow), labelled in mono 11.5px with the saved hours in green-text.

### Data Log (signature)
A full-width table with an ink rule above the 12px/600 header, hairline row dividers, 11px 8px cell padding and 13.5px text. Group rows are 700/13px titles with mono counts and a muted sub-line, opening on click with a rotating chevron. Each cell row shows its verdict chip, a 104 by 14px interval bar (rule rail at 1.5, ink notch at the decision line, a band in the verdict colour, a point) with the probability in mono, cycle life and its delta in mono (green-text when past spec), and the split. Rows hover and select onto ink-wash; the selected row gets a 1.5px ink underline under its ID that draws in from the left. A refused row shows the red pennant and "held" at a fixed 13px with the reason in `ink-2` and the feature name in mono; it never shrinks at any breakpoint.

### Inspector (signature)
A surface panel with 1px ink border, 4px corners and Lift, sticky beside the log. Header: the cell ID in mono 16px/600, a muted sub-line, and a 30px pill close. Then, in order: the consequence block (600/14px on a meaning-tinted wash: green for a freed channel, ink-wash for a fail, slate-wash for keep testing, red-wash for a refusal), an optional guided block (ink-wash ground under a 1px ink rule, rounded only at the bottom, with a bold lead and numbered steps), the run chart (the cell's own control chart across cutoffs with pass/keep/fail calls under each bar), key-value sections (muted keys, mono values, red flagged values), line charts with 1.75 strokes and 4 3 dashed reference lines, and for refused cells the envelope panel (an 8px slate-wash rail with a green in-range band, a 2px red marker for the out-of-range value, and mono bounds). Sections sharpen in with a 40ms stagger. Under 960px it becomes the bottom sheet.

### Welcome Dialog
A 600px surface panel with 1px ink border, 6px corners, Lift, a 28px/700 title, an `ink-2` lead, a list of verdict chips, and one primary pill beside two quiet buttons. Its backdrop blurs 10px.

## Do's and Don'ts

### Do:
- **Do** keep the page ground one flat colour: cream (#f7f4ea) in light, matte black (#121212) in dark, no grid, gradient or texture.
- **Do** spend red only on alarms: a straddle pennant, a refusal hatch, a limit line, an error or a shortfall against spec.
- **Do** use ink for every interaction state: selection ring, drop line, row underline, focus outline, hover border, pressed segment.
- **Do** set every measurement, probability, delta and cell ID in JetBrains Mono with tabular numerals, and everything else in Archivo.
- **Do** separate bands with 1px rules (`rule` for hairlines, `ink` for structural edges) and give panels 4px corners and pressable controls 999px pills.
- **Do** lift only the surface that holds the selected cell (inspector, result panel, dialog, tooltip) with the Lift shadow.
- **Do** run motion once as arrival (line draws, bars rise, flags drop, counters and rows follow) and once as selection; collapse all of it under `prefers-reduced-motion`.
- **Do** keep the refused mark at full size on every breakpoint and cluster straddler pennants into one flag with a count when the chart is narrow.

### Don't:
- **Don't** show a number for a refused cell; a refusal is a hatched column, a pennant and the out-of-range feature's name.
- **Don't** let a chemistry hue read as a status: the quartet stays clear of green and red and never fills a verdict.
- **Don't** use green as the interval fill for anything but a cleared pass, or use fill green for type (use `green-text`).
- **Don't** add eyebrows, kickers, section numbers, uppercase labels or cards inside cards.
- **Don't** add a second lift, a hard offset shadow, a glow or a hover shadow; hover is a border change and a 1px rise.
- **Don't** let a masthead tally or an accuracy scorecard become the largest type on a surface; the 30px disposition numerals are the one scale step.
- **Don't** introduce custom cursors, split-text reveals, parallax, magnetic buttons or marquees.
