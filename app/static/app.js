/* Hectocycle — the fleet as a control chart. Vanilla JS + hand-rolled SVG. */

"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const XLINK = "http://www.w3.org/1999/xlink";
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const state = {
  data: null, tab: "fleet", fleet: "qual", queue: null, selected: null, search: "",
  sortKey: null, sortDir: 1, showRef: false, guided: false, arrived: { qual: false, diag: false },
};

/* ---------- tiny helpers ---------- */

function el(tag, attrs = {}, parent = null) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "href") { node.setAttribute("href", v); node.setAttributeNS(XLINK, "xlink:href", v); }
    else node.setAttribute(k, v);
  }
  if (parent) parent.appendChild(node);
  return node;
}

function html(tag, cls = "", parent = null, text = null) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  if (parent) parent.appendChild(node);
  return node;
}

function icon(name, w = 12, h = 12) {
  const svg = el("svg", { width: w, height: h, "aria-hidden": "true" });
  el("use", { href: `#${name}` }, svg);
  return svg;
}

const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? "–" : (+v).toFixed(d));
const fmtInt = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-US"));
const shortId = (id) => id.replace("SNL_18650_", "");
const T = () => state.data.qual.threshold;

const FEATURE_LABEL = {
  log_var_dq: "ΔQ(V) variance, log₁₀",
  log_min_dq: "ΔQ(V) minimum, log₁₀|min|",
  log_mean_dq: "ΔQ(V) mean, log₁₀|mean|",
};

const VERDICT_TEXT = {
  pass: "Pass", fail: "Fail", "keep-testing": "Keep testing", "out-of-envelope": "Refused", train: "Reference",
};

function announce(text) { document.getElementById("sr-status").textContent = text; }

/* drop logging glitches (zero-capacity first cycles, dropout spikes) */
function cleanFade(fade) {
  const med = [...fade.qd].sort((a, b) => a - b)[Math.floor(fade.qd.length / 2)];
  const keep = fade.qd.map((q) => q > 0.5 * med);
  return { cycle: fade.cycle.filter((_, i) => keep[i]), qd: fade.qd.filter((_, i) => keep[i]) };
}

/* ---------- theme: light by default (chart paper under lab light); dark on request ---------- */

function setTheme(theme) {
  if (theme === "dark") document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  localStorage.setItem("hectocycle-theme", theme);
  const btn = document.getElementById("theme-toggle");
  const next = theme === "dark" ? "light" : "dark";
  btn.innerHTML = "";
  btn.appendChild(icon(theme === "dark" ? "i-sun" : "i-moon", 16, 16));
  btn.setAttribute("aria-label", `Switch to ${next} theme`);
  btn.title = `Switch to ${next} theme`;
}

document.getElementById("theme-toggle").addEventListener("click", (ev) => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  const root = document.documentElement;
  if (document.startViewTransition && !REDUCED) {
    const r = ev.currentTarget.getBoundingClientRect();
    root.style.setProperty("--tx", `${r.left + r.width / 2}px`);
    root.style.setProperty("--ty", `${r.top + r.height / 2}px`);
    root.classList.add("theming");
    const vt = document.startViewTransition(() => setTheme(next));
    vt.finished.finally(() => root.classList.remove("theming"));
  } else setTheme(next);
});
setTheme(localStorage.getItem("hectocycle-theme") === "dark" ? "dark" : "light");

/* ---------- tabs ---------- */

const TABS = ["fleet", "gates", "science", "try"];

function showTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach((t) => {
    const on = t.dataset.tab === name;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on);
    t.tabIndex = on ? 0 : -1;
  });
  for (const n of TABS) document.getElementById(`pane-${n}`).classList.toggle("hidden", n !== name);
  if (name === "gates") renderGates();
  if (name === "science") renderScience();
  if (name === "try") renderTry();
  updateHash();
}

function setTab(name) {
  if (state.tab === name) return;
  if (document.startViewTransition && !REDUCED) document.startViewTransition(() => showTab(name));
  else showTab(name);
}

document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setTab(t.dataset.tab)));
document.querySelector(".form-tabs").addEventListener("keydown", (e) => {
  if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
  e.preventDefault();
  const i = TABS.indexOf(state.tab);
  const j = e.key === "ArrowRight" ? (i + 1) % TABS.length : e.key === "ArrowLeft" ? (i + TABS.length - 1) % TABS.length
    : e.key === "Home" ? 0 : TABS.length - 1;
  setTab(TABS[j]);
  document.querySelector(`.tab[data-tab="${TABS[j]}"]`).focus();
});
document.getElementById("home-link").addEventListener("click", (e) => { e.preventDefault(); setTab("fleet"); deselect(); window.scrollTo({ top: 0 }); });

function updateHash() {
  let h = state.tab === "fleet" ? (state.selected ? `${state.fleet}/${state.selected}` : (state.fleet === "diag" ? "diag" : "")) : state.tab;
  history.replaceState(null, "", h ? `#${h}` : location.pathname + location.search);
}

/* ---------- the arrival moment ---------- */

function verdictMark(verdict, text = VERDICT_TEXT[verdict]) {
  const s = html("span", `verdict ${verdict}`);
  if (verdict === "out-of-envelope") s.appendChild(icon("i-flag", 11, 13));
  s.append(text);
  return s;
}

function showWelcome() {
  const dlg = document.getElementById("welcome");
  const list = document.getElementById("welcome-outcomes");
  list.innerHTML = "";
  for (const [v, txt] of [
    ["pass", "call it now; the cell comes off the test channel"],
    ["keep-testing", "the honest answer when 100 cycles cannot separate it from the spec"],
    ["out-of-envelope", "data the model was not trained for; it refuses to guess"],
  ]) {
    const li = html("li", "", list);
    li.appendChild(verdictMark(v));
    html("span", "", li, txt);
  }
  dlg.showModal();
}

document.getElementById("welcome").addEventListener("close", (e) => {
  localStorage.setItem("hectocycle-welcomed", "1");
  const v = e.target.returnValue;
  if (v !== "demo") document.getElementById("help-btn").focus();
  if (v === "demo" && state.data) {
    setTab("fleet");
    const demo = state.data.qual.cells.find((c) => c.id === "b1c6") || state.data.qual.cells.find((c) => c.verdict === "keep-testing");
    state.guided = true;
    select(demo.id, { scroll: true });
  } else if (v === "try") setTab("try");
});
document.getElementById("help-btn").addEventListener("click", showWelcome);

/* ---------- queues: one source of truth for chart groups, counts, and log groups ---------- */

const QUEUES = {
  qual: [
    { key: "call", title: "Ready to call", tone: "good", swatch: "pass",
      sub: "interval clear of the decision line; these come off the cycler today",
      match: (c) => c.verdict === "pass" || c.verdict === "fail" },
    { key: "keep", title: "Keep testing", tone: "plain", swatch: "keep",
      sub: "interval straddles the line; leave on test",
      match: (c) => c.verdict === "keep-testing" },
    { key: "held", title: "Held", tone: "flag", swatch: "held",
      sub: "outside the training envelope; refused, not scored",
      match: (c) => c.verdict === "out-of-envelope" },
    { key: "ref", title: "Reference", tone: "quiet", swatch: "ref",
      sub: "training cells; they built the model and get no verdict",
      match: (c) => c.verdict === "train", collapsible: true, chart: false },
  ],
  diag: [
    { key: "quant", title: "Quantitative modes", tone: "plain", swatch: "quant",
      sub: "C/18.5 diagnostics and matched references earn the full LLI / LAM split",
      match: (c) => !!c.modes },
    { key: "featured", title: "Featured curves", tone: "plain", swatch: "featured",
      sub: "NCA and NMC at 0.5C: staged curves, a qualitative hint only",
      match: (c) => !c.modes && (c.chemistry === "NCA" || c.chemistry === "NMC") },
    { key: "muted", title: "Muted", tone: "quiet", swatch: "muted",
      sub: "LFP: the flat plateau limits what a curve can say",
      match: (c) => !c.modes && c.chemistry === "LFP" },
  ],
};

function fleetCells() { return (state.fleet === "qual" ? state.data.qual : state.data.diag).cells; }

function searchedCells() {
  const cells = fleetCells();
  if (!state.search) return cells;
  const q = state.search.toLowerCase();
  const hay = state.fleet === "qual"
    ? (c) => `${c.id} ${c.policy} ${c.split} ${c.verdict} ${VERDICT_TEXT[c.verdict]}`
    : (c) => `${c.id} ${c.chemistry} ${c.modes ? "quantitative" : c.mode_hint.dominant || ""}`;
  return cells.filter((c) => hay(c).toLowerCase().includes(q));
}

/* ordered chart items: [{cell, group, y, lo, hi, kind}] */
function chartItems() {
  const items = [];
  if (state.fleet === "qual") {
    const cells = state.data.qual.cells;
    const pass = cells.filter((c) => c.verdict === "pass").sort((a, b) => b.p_pass - a.p_pass || b.p_lo - a.p_lo);
    const fail = cells.filter((c) => c.verdict === "fail").sort((a, b) => a.p_pass - b.p_pass || a.p_hi - b.p_hi);
    const keep = cells.filter((c) => c.verdict === "keep-testing").sort((a, b) => b.p_pass - a.p_pass);
    const held = cells.filter((c) => c.verdict === "out-of-envelope");
    for (const c of [...pass, ...fail]) items.push({ cell: c, group: "call", y: c.p_pass, lo: c.p_lo, hi: c.p_hi, kind: c.verdict });
    for (const c of keep) items.push({ cell: c, group: "keep", y: c.p_pass, lo: c.p_lo, hi: c.p_hi, kind: "keep-testing" });
    for (const c of held) items.push({ cell: c, group: "held", kind: "held" });
  } else {
    const cells = state.data.diag.cells;
    const quant = cells.filter((c) => c.modes).sort((a, b) => b.modes.rho_LLI - a.modes.rho_LLI);
    const feat = cells.filter((c) => !c.modes && c.chemistry !== "LFP").sort((a, b) => (b.mode_hint.rho ?? -1) - (a.mode_hint.rho ?? -1));
    const muted = cells.filter((c) => !c.modes && c.chemistry === "LFP");
    for (const c of quant) items.push({ cell: c, group: "quant", y: c.modes.rho_LLI, kind: "quant" });
    for (const c of feat) items.push({ cell: c, group: "featured", y: c.mode_hint.rho, kind: "featured" });
    for (const c of muted) items.push({ cell: c, group: "muted", kind: "muted" });
  }
  return items;
}

/* ---------- the fleet chart ---------- */

const tipState = { x: 0, y: 0, tx: 0, ty: 0, raf: 0 };

function renderFleetChart() {
  const box = document.getElementById("fleet-chart");
  const cs = getComputedStyle(box);
  const W = Math.max(320, box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight));
  const H = window.innerWidth < 960 ? 200 : 300;
  const narrow = W < 620;
  const pad = { l: 46, r: 14, t: narrow ? 50 : 34, b: 26 };
  const items = chartItems();
  const groups = QUEUES[state.fleet].filter((g) => g.chart !== false);
  const first = !state.arrived[state.fleet];
  state.arrived[state.fleet] = true;

  box.innerHTML = "";
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img" }, box);
  const defs = el("defs", {}, svg);
  for (const [id, cls] of [["hatch-red", "var(--red)"], ["hatch-slate", "var(--slate)"]]) {
    const p = el("pattern", { id, width: 6, height: 6, patternUnits: "userSpaceOnUse" }, defs);
    el("path", { d: "M0 6 L6 0 M-1 1 L1 -1 M5 7 L7 5", stroke: cls, "stroke-width": 1.1, "stroke-linecap": "round", fill: "none" }, p);
  }

  const plotH = H - pad.t - pad.b, plotW = W - pad.l - pad.r;
  const Y = (p) => pad.t + (1 - p) * plotH;
  const isQual = state.fleet === "qual";
  const lineP = isQual ? 0.5 : 0.8;
  const midY = Y(lineP);

  // group spans; on narrow viewports the labels shorten and the flags shrink
  const gap = narrow ? 10 : 20;
  const flagW = narrow ? 8 : 11, flagH = narrow ? 9.5 : 13;
  const counts = groups.map((g) => items.filter((i) => i.group === g.key).length);
  const n = items.length;
  const usable = plotW - gap * (groups.length - 1);
  const slot = usable / Math.max(n, 1);
  const barW = Math.max(2, Math.min(9, slot * 0.55));
  let x = pad.l;
  const gx = {};
  groups.forEach((g, gi) => { gx[g.key] = x; x += counts[gi] * slot + gap; });

  // frame: y rules at 0 and 1, y labels
  for (const p of [0, 1]) el("line", { class: "fc-rule", x1: pad.l, x2: W - pad.r, y1: Y(p), y2: Y(p) }, svg);
  el("line", { class: "fc-yaxis", x1: pad.l, x2: pad.l, y1: pad.t, y2: H - pad.b }, svg);
  const yl = (p, txt) => { const t = el("text", { class: "fc-axis", x: pad.l - 8, y: Y(p) + 4, "text-anchor": "end" }, svg); t.textContent = txt; };
  yl(1, isQual ? "1.0" : "1.0"); yl(0, "0"); yl(lineP, isQual ? "0.5" : "0.8");
  const yt = el("text", { class: "axis-title", x: pad.l - 8, y: pad.t - 12, "text-anchor": "end" }, svg);
  yt.textContent = isQual ? "P(pass)" : "ρ";

  // group labels + separators
  groups.forEach((g, gi) => {
    const t = el("text", { class: "fc-group", x: gx[g.key], y: 14 }, svg);
    t.textContent = narrow ? g.title.split(" ")[0] : g.title;
    if (!narrow) { const c = el("tspan", { class: "fc-group-n", dx: 6 }, t); c.textContent = counts[gi]; }
    if (narrow && gi > 0) { t.setAttribute("x", gx[g.key] + counts[gi] * slot / 2); t.setAttribute("text-anchor", "middle"); }
    if (narrow && g.key === "keep" && counts[gi]) {
      // one clustered pennant with its count stands in for 22 overlapping flags
      const fx = gx[g.key] + counts[gi] * slot / 2;
      el("use", { href: "#i-flag", class: "fc-flag", x: fx - 16, y: 22, width: 11, height: 13 }, svg);
      const n = el("text", { class: "fc-group-n", x: fx - 2, y: 33 }, svg);
      n.textContent = String(counts[gi]);
      n.setAttribute("style", "font-size:11px");
    }
    if (gi > 0) {
      const sx = gx[g.key] - gap / 2;
      el("line", { class: "fc-sep", x1: sx, x2: sx, y1: pad.t - 6, y2: H - pad.b }, svg);
    }
  });

  // the center / limit line, drawn first
  const line = el("line", { class: isQual ? "fc-center" : "fc-limit", x1: pad.l, x2: W - pad.r, y1: midY, y2: midY }, svg);
  line.style.setProperty("--len", plotW);
  const ll = el("text", { class: isQual ? "fc-center-label" : "fc-limit-label", x: isQual ? pad.l + 12 : W - pad.r, y: isQual ? midY + 15 : midY - 6, "text-anchor": isQual ? "start" : "end" }, svg);
  ll.textContent = isQual ? "decision line 0.5" : "trust bar ρ ≥ 0.8";

  // bars
  const activeIds = new Set(searchedCells().filter((c) => !state.queue || QUEUES[state.fleet].find((q) => q.key === state.queue).match(c)).map((c) => c.id));
  const gCount = {};
  items.forEach((it, i) => {
    const gi = groups.findIndex((g) => g.key === it.group);
    gCount[it.group] = (gCount[it.group] || 0);
    const cx = gx[it.group] + gCount[it.group] * slot + slot / 2;
    gCount[it.group]++;
    const chem = it.cell.chemistry || "";
    const g = el("g", { class: `fc-bar ${it.kind} ${chem}`, "data-id": it.cell.id }, svg);
    g.style.setProperty("--i", i);
    g.style.setProperty("--mid", `${midY}px`);
    if (!activeIds.has(it.cell.id)) g.style.opacity = 0.18;
    if (it.cell.id === state.selected) g.classList.add("selected");

    if (it.kind === "held" || it.kind === "muted") {
      el("rect", { class: `fc-hatch${it.kind === "muted" ? " muted" : ""}`, x: cx - slot * 0.42, y: pad.t, width: slot * 0.84, height: plotH, rx: 1 }, g);
      if (it.kind === "held") el("use", { href: "#i-flag", class: "fc-flag", x: cx - 5.5, y: pad.t - 18, width: 11, height: 13 }, g);
    } else if (isQual) {
      const y1 = Y(it.hi), y2 = Y(it.lo);
      el("rect", { x: cx - barW / 2, y: y1, width: barW, height: Math.max(y2 - y1, 1.5), rx: barW / 2 }, g);
      el("circle", { cx, cy: Y(it.y), r: Math.max(2, barW * 0.32), stroke: "var(--paper)", "stroke-width": 1.2 }, g);
      if (it.kind === "keep-testing" && !narrow) el("use", { href: "#i-flag", class: "fc-flag", x: cx - flagW / 2, y: y1 - flagH - 5, width: flagW, height: flagH }, g);
    } else {
      const unstable = it.y < 0.8;
      if (unstable) g.classList.add("unstable");
      el("rect", { x: cx - 0.75, y: Y(it.y), width: 1.5, height: Y(0) - Y(it.y) }, g);
      el("circle", { cx, cy: Y(it.y), r: 3.2, stroke: "var(--paper)", "stroke-width": 1.2 }, g);
      if (unstable) el("use", { href: "#i-flag", class: "fc-flag", x: cx - flagW / 2, y: Y(it.y) - flagH - 9, width: flagW, height: flagH }, g);
    }
    const hit = el("rect", { class: "fc-hit", x: cx - slot / 2, y: pad.t - 20, width: slot, height: plotH + 20 }, g);
    hit.addEventListener("mouseenter", () => showTip(box, it, cx, it.kind === "held" || it.kind === "muted" ? pad.t : Y(it.y), g));
    hit.addEventListener("mouseleave", () => hideTip(box, g));
    hit.addEventListener("click", () => select(it.cell.id, { scroll: true }));
  });

  // selection: the red pen circle and the drop line
  const sel = items.find((it) => it.cell.id === state.selected);
  if (sel) {
    const gi = items.indexOf(sel);
    const cxSel = gx[sel.group] + (items.filter((it, k) => it.group === sel.group && k < gi).length) * slot + slot / 2;
    const cy = sel.kind === "held" || sel.kind === "muted" ? pad.t + 10 : Y(sel.y);
    const sg = el("g", { class: "fc-select" }, svg);
    el("line", { class: "fc-select-drop", x1: cxSel, x2: cxSel, y1: cy + 8, y2: H - pad.b }, sg);
    el("circle", { class: "fc-select-ring", cx: cxSel, cy, r: 8.5 }, sg);
  }

  svg.setAttribute("aria-label", isQual
    ? `Control chart of ${n} held-out and transfer cells: ${counts[0]} ready to call, ${counts[1]} keep testing, ${counts[2]} held.`
    : `Mode-stability chart of ${n} diagnostics cells: ${counts[0]} quantitative, ${counts[1]} featured, ${counts[2]} muted.`);

  if (!first || REDUCED) svg.querySelectorAll(".fc-center, .fc-limit, .fc-bar rect, .fc-bar circle, .fc-flag, .fc-group, .fc-sep").forEach((e) => { e.style.animation = "none"; });

  const tip = html("div", "chart-tip", box);
  tip.setAttribute("role", "status");
}

function showTip(box, it, cx, cy, g) {
  const tip = box.querySelector(".chart-tip");
  const c = it.cell;
  box.classList.add("hovering");
  g.classList.add("hover");
  if (state.fleet === "qual") {
    const v = c.verdict;
    tip.innerHTML = `<span class="tip-id">${shortId(c.id)}</span><span class="tip-verdict ${v}">${VERDICT_TEXT[v]}</span><br>`
      + (v === "out-of-envelope" ? `refused: ${c.violations.join(", ")} out of range` : `P(pass) <b>${fmt(c.p_pass)}</b> · interval [${fmt(c.p_lo)}, ${fmt(c.p_hi)}]`)
      + `<br>true life ${c.cycle_life ?? "≥ 2337 (censored)"} · ${c.label ? "pass" : "fail"} at T = ${T()}`;
  } else {
    tip.innerHTML = `<span class="tip-id">${shortId(c.id)}</span> ${c.chemistry}<br>`
      + (c.modes ? `LLI ${(c.modes.LLI.at(-1) * 100).toFixed(0)}% · ρ = ${c.modes.rho_LLI} quantitative`
        : c.chemistry === "LFP" ? "muted: no mode attribution offered"
          : `${c.mode_hint.dominant} · ρ = ${c.mode_hint.rho}${c.mode_hint.rho < 0.8 ? " (below trust bar)" : ""}`);
  }
  const cs = getComputedStyle(box);
  tipState.tx = parseFloat(cs.paddingLeft) + cx;
  tipState.ty = parseFloat(cs.paddingTop) + cy;
  if (!tip.classList.contains("show")) { tipState.x = tipState.tx; tipState.y = tipState.ty; }
  tip.classList.add("show");
  const step = () => {
    tipState.x += (tipState.tx - tipState.x) * (REDUCED ? 1 : 0.28);
    tipState.y += (tipState.ty - tipState.y) * (REDUCED ? 1 : 0.28);
    tip.style.left = `${tipState.x}px`; tip.style.top = `${tipState.y}px`;
    if (Math.abs(tipState.tx - tipState.x) > 0.3 || Math.abs(tipState.ty - tipState.y) > 0.3) tipState.raf = requestAnimationFrame(step);
  };
  cancelAnimationFrame(tipState.raf);
  tipState.raf = requestAnimationFrame(step);
}

function hideTip(box, g) {
  box.classList.remove("hovering");
  g.classList.remove("hover");
  box.querySelector(".chart-tip")?.classList.remove("show");
}

let resizeTimer = 0;
new ResizeObserver(() => {
  if (!state.data) return;
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderFleetChart, 120);
}).observe(document.getElementById("fleet-chart"));

/* ---------- chart head + disposition line ---------- */

function renderChartHead() {
  const title = document.getElementById("chart-title");
  const src = document.getElementById("chart-source");
  if (state.fleet === "qual") {
    title.textContent = "Every held-out cell at cycle 100: its calibrated P(pass) and Venn-ABERS interval against the decision line.";
    src.innerHTML = `<b>133 cells</b>: Severson 124 (41 train, 83 held-out) + Sandia transfer 9 · spec T = ${T()} cycles · verdicts use cycles ≤ 100 only · true cycle life shown so you can score the model yourself`;
  } else {
    title.textContent = "What is degrading inside each cell, and how much the data lets Hectocycle say about it.";
    src.innerHTML = `<b>69 cells</b>: Sandia 61 (NCA 22, NMC 21, LFP 18) + Oxford Kokam 8 · ρ = trajectory stability of the dominant mode; 0.8 is the trust bar`;
  }
}

function renderDisposition(first = false) {
  const box = document.getElementById("disposition");
  const prev = {};
  box.querySelectorAll(".disp").forEach((b) => { prev[b.dataset.key] = b.querySelector(".n").textContent; });
  box.innerHTML = "";
  if (first) { box.classList.add("arrive"); setTimeout(() => box.classList.remove("arrive"), 2200); }
  const counts = html("div", "disp-counts", box);
  const cells = searchedCells();
  QUEUES[state.fleet].forEach((q, i) => {
    const n = cells.filter(q.match).length;
    const b = html("button", `disp ${q.tone}`, counts);
    b.dataset.key = q.key;
    b.style.setProperty("--i", i);
    b.setAttribute("aria-pressed", state.queue === q.key);
    b.title = state.queue === q.key ? "Show every queue" : `Show only: ${q.title}`;
    html("span", `swatch ${q.swatch}`, b);
    const num = html("span", "n", b, String(n));
    if (prev[q.key] != null && prev[q.key] !== String(n)) num.classList.add("rolling");
    const lbl = html("span", "lbl", b, q.title.toLowerCase());
    if (q.key === "call") {
      const p = cells.filter((c) => c.verdict === "pass").length, f = cells.filter((c) => c.verdict === "fail").length;
      lbl.textContent = `ready to call (${p} pass · ${f} fail)`;
    }
    b.addEventListener("click", () => {
      state.queue = state.queue === q.key ? null : q.key;
      if (state.queue === "ref") state.showRef = true;
      renderDisposition(); renderLog(); renderFleetChart();
    });
  });

  const ct = html("div", "channel-time", box);
  ct.style.setProperty("--i", QUEUES[state.fleet].length);
  if (state.fleet === "qual") {
    const p = state.data.qual.policy;
    const line = html("p", "ct-line", ct);
    line.innerHTML = `Cycler time on the ${p.n} held-out cells, if a cell comes off the moment its verdict repeats at two consecutive checkpoints: `
      + `<b>${p.pulled_early} channels freed</b> by cycle 100 with <b>${p.wrong_verdicts} wrong verdicts</b>, `
      + `<b>${fmtInt(p.channel_days_freed)} channel-days</b> saved against running every cell to spec (${Math.round(p.saved_frac * 100)}% of cycler-hours, cycle time measured per cell).`;
    const budget = html("div", "budget", ct);
    const bar = html("div", "budget-bar", budget);
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `${fmtInt(p.policy_hours)} cycler-hours used of ${fmtInt(p.baseline_hours)} run-to-spec`);
    const used = html("div", "budget-used", bar);
    used.style.setProperty("--used", first && !REDUCED ? 1 : p.policy_hours / p.baseline_hours);
    if (first && !REDUCED) requestAnimationFrame(() => requestAnimationFrame(() => used.style.setProperty("--used", p.policy_hours / p.baseline_hours)));
    const lbl = html("span", "budget-lbl", budget);
    lbl.innerHTML = `${fmtInt(p.policy_hours)} h used of ${fmtInt(p.baseline_hours)} h · <b>${fmtInt(p.baseline_hours - p.policy_hours)} h saved</b>`;
  } else {
    const line = html("p", "ct-line", ct);
    line.innerHTML = `Mode attribution is shown only at the tier the data earns: a <b>quantitative</b> LLI / LAM split with C/18.5 diagnostics and matched half-cell references, a <b>hint</b> with its stability score from 0.5C curves, and <b>nothing</b> for LFP, whose flat plateau leaves too little to read.`;
  }
}

/* ---------- the data log ---------- */

const SORTS = {
  qual: { id: (c) => c.id, verdict: (c) => c.verdict, p_pass: (c) => c.p_pass, cycle_life: (c) => c.cycle_life ?? 1e9,
          delta: (c) => (c.cycle_life ?? 1e9) - 700, split: (c) => c.split, policy: (c) => c.policy },
  diag: { id: (c) => c.id, chemistry: (c) => c.chemistry, rho: (c) => c.modes ? c.modes.rho_LLI : (c.mode_hint.rho ?? -1),
          fade_frac: (c) => c.fade_frac, temperature_C: (c) => c.temperature_C,
          discharge_rate_C: (c) => c.discharge_rate_C ?? 0, v_dispersion: (c) => c.v_dispersion },
};

function sortCells(cells) {
  const acc = SORTS[state.fleet][state.sortKey];
  if (!acc) return cells;
  return [...cells].sort((a, b) => { const va = acc(a), vb = acc(b); return (va < vb ? -1 : va > vb ? 1 : 0) * state.sortDir; });
}

function headerRow(thead, cols) {
  const tr = html("tr", "", thead);
  for (const col of cols) {
    const th = html("th", col.cls || "", tr);
    th.scope = "col";
    if (col.sort) {
      th.setAttribute("aria-sort", state.sortKey === col.sort ? (state.sortDir > 0 ? "ascending" : "descending") : "none");
      const b = html("button", "sort", th);
      b.type = "button";
      const lbl = html("span", "", b, col.label);
      if (col.tip) { lbl.innerHTML = `<abbr title="${col.tip}">${col.label}</abbr>`; }
      const svg = el("svg", { viewBox: "0 0 10 10", "aria-hidden": "true" }, b);
      el("path", { d: "M5 1.5 L9 7.5 H1 Z", fill: "currentColor" }, svg);
      b.addEventListener("click", () => {
        if (state.sortKey === col.sort) { if (state.sortDir === 1) state.sortDir = -1; else { state.sortKey = null; state.sortDir = 1; } }
        else { state.sortKey = col.sort; state.sortDir = 1; }
        renderLog();
      });
    } else if (col.tip) th.innerHTML = `<abbr title="${col.tip}">${col.label}</abbr>`;
    else th.textContent = col.label;
  }
}

function intervalBar(c) {
  const wrap = html("span", "ibar");
  const w = 104, h = 14, x0 = 2, x1 = w - 2, mid = h / 2;
  const X = (p) => x0 + p * (x1 - x0);
  const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img",
    "aria-label": `P(pass) ${fmt(c.p_pass)}, interval ${fmt(c.p_lo)} to ${fmt(c.p_hi)}` }, wrap);
  el("line", { class: "ib-rail", x1: x0, x2: x1, y1: mid, y2: mid }, svg);
  el("line", { class: "ib-notch", x1: X(0.5), x2: X(0.5), y1: 2, y2: h - 2 }, svg);
  if (c.p_lo != null) el("rect", { class: `ib-band ${c.verdict}`, x: X(c.p_lo), y: mid - 2.5, width: Math.max(X(c.p_hi) - X(c.p_lo), 2), height: 5, rx: 2.5 }, svg);
  el("circle", { class: `ib-point ${c.verdict}`, cx: X(c.p_pass), cy: mid, r: 3, stroke: "var(--surface)", "stroke-width": 1 }, svg);
  html("span", "p", wrap, fmt(c.p_pass));
  return wrap;
}

function refusedBlock(c) {
  const s = html("span", "refused");
  s.appendChild(icon("i-flag", 11, 13));
  s.append("Refused ");
  const why = html("span", "why", s);
  why.innerHTML = `· ${c.violations.map((f) => `<code>${f}</code>`).join(", ")} outside the training range`;
  return s;
}

function lifeCell(c) {
  if (c.cycle_life == null) return { life: "≥ 2337", delta: "censored", cls: "dim", title: "The Sandia log ends before end of life; the cell is still above 80% capacity." };
  const d = c.cycle_life - T();
  return { life: String(c.cycle_life), delta: `${d >= 0 ? "+" : "−"}${Math.abs(d)}`, cls: d >= 0 ? "long" : "short", title: `${Math.abs(d)} cycles ${d >= 0 ? "past" : "short of"} the ${T()}-cycle spec` };
}

const SPLIT_LABEL = { primary: "primary", secondary: "secondary", transfer: "transfer", train: "train" };

function renderLog() {
  const table = document.getElementById("fleet-table");
  table.innerHTML = "";
  const thead = html("thead", "", table);
  const tbody = html("tbody", "", table);
  let rowIdx = 0;
  const isQual = state.fleet === "qual";
  const ncol = isQual ? 7 : 7;

  const cols = isQual ? [
    { label: "Cell", sort: "id" },
    { label: "Disposition", sort: "verdict" },
    { label: "Early call", sort: "p_pass", tip: "From cycles ≤ 100 only: the point is the calibrated P(pass), the band its Venn-ABERS interval, the notch the 0.5 decision line" },
    { label: "Cycle life", sort: "cycle_life", cls: "num", tip: "Ground truth: cycles until capacity fell to 80% (0.88 Ah)" },
    { label: "vs spec", sort: "delta", cls: "num", tip: `Cycles past or short of the T = ${T()} qualification spec` },
    { label: "Split", sort: "split", cls: "col-opt", tip: "primary and secondary are held-out test sets; transfer cells are the same A123 cell cycled at Sandia; train cells built the model" },
    { label: "Charge policy", sort: "policy", cls: "col-opt", tip: "fast-charge protocol, e.g. 4.8C(80%)-4.8C = 4.8C to 80% SOC, then 4.8C" },
  ] : [
    { label: "Cell", sort: "id" },
    { label: "Chemistry", sort: "chemistry" },
    { label: "Dominant mode", sort: "rho", tip: "ρ = Spearman stability of the mode trajectory against cycle number; 0.8 is the trust bar. Quantitative = earned by C/18.5 diagnostics and matched references" },
    { label: "Fade", sort: "fade_frac", cls: "num", tip: "capacity lost over the recorded test" },
    { label: "Temp", sort: "temperature_C", cls: "num" },
    { label: "Rate", sort: "discharge_rate_C", cls: "col-opt", tip: "aging discharge rate; C/18.5 marks diagnostics-grade slow cycles" },
    { label: "V-disp.", sort: "v_dispersion", cls: "num col-opt", tip: "voltage window holding the central 80% of charge; ~0.5–0.6 V for NCA/NMC, ~0.15 V for LFP" },
  ];
  headerRow(thead, cols);

  let groups = QUEUES[state.fleet];
  if (state.queue) groups = groups.filter((g) => g.key === state.queue);
  const cells = sortCells(searchedCells());
  let shown = 0;

  for (const g of groups) {
    const members = cells.filter(g.match);
    if (!members.length) continue;
    const tr = html("tr", `group-row${g.collapsible ? " collapsible" : ""}${g.collapsible && state.showRef ? " open" : ""}`, tbody);
    const td = html("td", "", tr);
    td.colSpan = ncol;
    if (g.collapsible) html("span", "chev", td);
    html("span", "g-title", td, g.title);
    html("span", "g-n", td, String(members.length));
    html("span", "g-sub", td, g.sub);
    if (g.collapsible) {
      td.setAttribute("role", "button");
      td.tabIndex = 0;
      td.setAttribute("aria-expanded", state.showRef);
      const toggle = () => { state.showRef = !state.showRef; renderLog(); };
      tr.addEventListener("click", toggle);
      td.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
      if (!state.showRef) continue;
    }
    for (const c of members) {
      shown++;
      const row = html("tr", "", tbody);
      row.style.setProperty("--i", Math.min(rowIdx++, 30));
      row.tabIndex = 0;
      row.dataset.id = c.id;
      row.setAttribute("aria-selected", c.id === state.selected);
      if (isQual) {
        html("td", "cell-id", row, shortId(c.id));
        html("td", "", row).appendChild(verdictMark(c.verdict));
        const ec = html("td", "", row);
        if (c.verdict === "out-of-envelope") { ec.appendChild(refusedBlock(c)); ec.style.whiteSpace = "normal"; }
        else if (c.verdict === "train") html("span", "dim", ec, "–");
        else ec.appendChild(intervalBar(c));
        const L = lifeCell(c);
        html("td", "cell-id num", row, L.life).title = L.title;
        const dt = html("td", "num", row);
        html("span", `delta ${L.cls}`, dt, L.delta).title = L.title;
        html("td", "cond col-opt", row, SPLIT_LABEL[c.split] || c.split);
        html("td", "cond col-opt", row, c.policy);
      } else {
        html("td", "cell-id", row, shortId(c.id));
        const ch = html("td", "", row);
        html("span", `chem ${c.chemistry}`, ch, c.chemistry);
        const m = html("td", "", row);
        if (c.modes) {
          html("span", "cell-id", m, `LLI ${(c.modes.LLI.at(-1) * 100).toFixed(0)}%`);
          html("span", "rho", m, `ρ = ${c.modes.rho_LLI} · quantitative`);
        } else if (c.chemistry === "LFP") {
          html("span", "dim", m, "muted · not offered");
        } else {
          html("span", "cell-id", m, c.mode_hint.dominant);
          html("span", `rho${c.mode_hint.rho < 0.8 ? " low" : ""}`, m, `ρ = ${c.mode_hint.rho}${c.mode_hint.rho < 0.8 ? " · below trust bar" : ""}`);
        }
        html("td", "cell-id num", row, `${(c.fade_frac * 100).toFixed(1)}%`);
        html("td", "cond num", row, `${c.temperature_C} °C`);
        html("td", "cond col-opt", row, c.diag_rate ?? `${c.discharge_rate_C}C`);
        html("td", "cell-id num col-opt", row, `${c.v_dispersion.toFixed(2)} V`);
      }
      row.addEventListener("click", () => select(c.id));
      row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(c.id); } });
    }
  }

  if (!shown && !tbody.querySelector(".group-row")) {
    const tr = html("tr", "empty-row", tbody);
    const td = html("td", "", tr);
    td.colSpan = ncol;
    td.textContent = state.search ? `No cells match “${state.search}”. Try a cell id, a verdict, or a charge policy.` : "Nothing in this queue.";
  }

  const total = fleetCells().length;
  const counter = document.getElementById("result-count");
  counter.textContent = (state.search || state.queue) ? `${shown} of ${total} cells` : "";
  document.getElementById("log-title").textContent = isQual ? "Data log · qualification" : "Data log · diagnostics";
}

/* ---------- selection ---------- */

function deselect() {
  state.selected = null;
  state.guided = false;
  document.querySelectorAll(".fleet tbody tr[data-id]").forEach((tr) => tr.setAttribute("aria-selected", "false"));
  document.querySelector("#fleet-chart .fc-select")?.remove();
  document.querySelectorAll("#fleet-chart .fc-bar.selected").forEach((g) => g.classList.remove("selected"));
  renderIdleInspector();
  updateHash();
}

function select(id, { scroll = false } = {}) {
  const wasGuided = state.guided && state.selected == null;
  if (state.selected && state.selected !== id) state.guided = false;
  if (wasGuided) state.guided = true;
  state.selected = id;
  document.querySelectorAll(".fleet tbody tr[data-id]").forEach((tr) => tr.setAttribute("aria-selected", tr.dataset.id === id));
  renderFleetChart();
  const insp = document.getElementById("inspector");
  insp.innerHTML = "";
  insp.scrollTop = 0;
  insp.classList.remove("idle");
  insp.classList.add("open");
  const cell = fleetCells().find((c) => c.id === id);
  if (state.fleet === "qual") renderQualInspector(insp, cell);
  else renderDiagInspector(insp, cell);
  announce(`${shortId(id)} selected: ${state.fleet === "qual" ? VERDICT_TEXT[cell.verdict] : cell.chemistry}.`);
  updateHash();
  if (state.guided) { insp.tabIndex = -1; insp.focus({ preventScroll: true }); }
  if (scroll) {
    const row = document.querySelector(`.fleet tbody tr[data-id="${CSS.escape(id)}"]`);
    row?.scrollIntoView({ block: "nearest", behavior: REDUCED ? "auto" : "smooth" });
  }
}

document.addEventListener("keydown", (e) => {
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (e.key === "/" && state.tab === "fleet") { e.preventDefault(); document.getElementById("search").focus(); return; }
  if (e.key === "Escape") { if (state.selected) deselect(); return; }
  if (state.tab !== "fleet" || (e.key !== "ArrowDown" && e.key !== "ArrowUp")) return;
  const rows = [...document.querySelectorAll(".fleet tbody tr[data-id]")];
  if (!rows.length) return;
  e.preventDefault();
  const idx = rows.findIndex((r) => r.dataset.id === state.selected);
  const next = rows[Math.min(Math.max(idx + (e.key === "ArrowDown" ? 1 : -1), 0), rows.length - 1)];
  select(next.dataset.id, { scroll: true });
  next.focus({ preventScroll: true });
});

/* ---------- inspector ---------- */

function section(parent, title, sub = "") {
  const s = html("div", "insp-section", parent);
  const h = html("h3", "", s, title);
  if (sub) html("span", "sub", h, sub);
  return s;
}

function kvList(parent, entries) {
  const dl = html("dl", "kv", parent);
  for (const [k, v, cls] of entries) {
    html("dt", "", dl, k);
    html("dd", cls || "", dl, v);
  }
  return dl;
}

function inspectorHead(insp, title, sub) {
  const head = html("div", "insp-head", insp);
  const t = html("div", "", head);
  html("div", "insp-title", t, title).id = "insp-title";
  html("div", "insp-sub", t, sub);
  const close = html("button", "insp-close", head);
  close.type = "button";
  close.setAttribute("aria-label", "Close record (Esc)");
  close.appendChild(icon("i-close", 12, 12));
  close.addEventListener("click", deselect);
}

function renderIdleInspector() {
  const insp = document.getElementById("inspector");
  insp.innerHTML = "";
  insp.classList.add("idle");
  insp.classList.remove("open");
  const box = html("div", "insp-idle", insp);
  if (state.fleet === "qual") {
    html("h3", "", box, "How to read the chart").id = "insp-title";
    html("p", "", box, "Each bar is one held-out cell at cycle 100. The point is its calibrated probability of passing the 700-cycle spec; the bar is the Venn-ABERS interval, the range the model is allowed to claim. The horizontal line is the decision.");
    const leg = html("div", "legend", box);
    for (const [v, txt] of [
      ["pass", "bar clears the line above: call it, free the channel"],
      ["fail", "bar clears the line below: reject early, reallocate"],
      ["keep-testing", "bar crosses the line: flagged, keep cycling"],
      ["out-of-envelope", "hatched: input outside the training range, no number offered"],
    ]) {
      const row = html("div", "", leg);
      row.appendChild(verdictMark(v));
      html("span", "", row, txt);
    }
    html("p", "hint", box).innerHTML = "Click a bar or a row to open its record · <kbd>↑</kbd><kbd>↓</kbd> move · <kbd>/</kbd> filter · <kbd>Esc</kbd> closes";
  } else {
    html("h3", "", box, "How to read the chart").id = "insp-title";
    html("p", "", box, "Each point is one cell's dominant degradation mode and how stable that attribution is across its life (ρ). Points under the 0.8 trust bar are flagged: the fit moved as the cell aged, so the mode is a hint, not a number.");
    const leg = html("div", "legend", box);
    for (const [cls, txt] of [["quant", "Oxford cells: full LLI / LAM split, earned by slow diagnostics and matched references"], ["featured", "NCA and NMC: a qualitative hint with its stability score"], ["muted", "LFP: hatched, no attribution offered"]]) {
      const row = html("div", "", leg);
      const sw = html("span", `swatch ${cls}`, row); sw.style.width = "12px"; sw.style.height = "12px";
      html("span", "", row, txt);
    }
    html("p", "hint", box).innerHTML = "Click a point or a row to open its record · <kbd>↑</kbd><kbd>↓</kbd> move · <kbd>Esc</kbd> closes";
  }
}

/* the cell's own control chart: verdict evidence across cutoffs */
function inspectorWidth() {
  const insp = document.getElementById("inspector");
  return Math.max(300, (insp.clientWidth || 460) - 56);
}

function runChart(evidence) {
  const wrap = html("div", "run-chart");
  const w = inspectorWidth(), h = 160, pad = { l: 34, r: 12, t: 16, b: 34 };
  const svg = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": "Verdict evidence at cutoffs 40 to 100 cycles" }, wrap);
  const plotW = w - pad.l - pad.r, plotH = h - pad.t - pad.b;
  const Y = (p) => pad.t + (1 - p) * plotH;
  const X = (i) => pad.l + (i + 0.5) * (plotW / evidence.length);
  for (const p of [0, 1]) el("line", { class: "fc-rule", x1: pad.l, x2: w - pad.r, y1: Y(p), y2: Y(p) }, svg);
  el("line", { class: "fc-center", x1: pad.l, x2: w - pad.r, y1: Y(0.5), y2: Y(0.5), style: "animation:none" }, svg);
  for (const [p, t] of [[1, "1.0"], [0.5, "0.5"], [0, "0"]]) { const tx = el("text", { class: "fc-axis", x: pad.l - 6, y: Y(p) + 4, "text-anchor": "end" }, svg); tx.textContent = t; }
  evidence.forEach((e, i) => {
    const kind = { 1: "pass", 0: "fail", "-1": "keep-testing" }[String(e.call)];
    const g = el("g", { class: `fc-bar ${kind}` }, svg);
    g.style.setProperty("--i", i);
    el("rect", { x: X(i) - 4, y: Y(e.hi), width: 8, height: Math.max(Y(e.lo) - Y(e.hi), 1.5), rx: 4 }, g);
    el("circle", { cx: X(i), cy: Y(e.p), r: 3.2, stroke: "var(--surface)", "stroke-width": 1.2, style: "animation:none" }, g);
    if (kind === "keep-testing") el("use", { href: "#i-flag", class: "fc-flag", x: X(i) - 5, y: Y(e.hi) - 17, width: 11, height: 13, style: "animation:none;opacity:1;transform:none" }, g);
    const cyc = el("text", { class: "fc-axis", x: X(i), y: h - 18, "text-anchor": "middle" }, svg);
    cyc.textContent = `cyc ${e.cutoff}`;
    const call = el("text", { class: `rc-call ${kind === "keep-testing" ? "keep" : kind}`, x: X(i), y: h - 4, "text-anchor": "middle" }, svg);
    call.textContent = kind === "keep-testing" ? (w < 380 ? "keep" : "keep testing") : kind;
  });
  return wrap;
}

function envelopePanel(parent, c) {
  const env = state.data.qual.envelope;
  const box = html("div", "env", parent);
  for (const f of state.data.qual.model.features) {
    const out = c.violations.includes(f);
    const row = html("div", `env-row${out ? " out" : ""}`, box);
    const name = html("div", "env-name", row);
    const nm = html("span", "", name);
    nm.innerHTML = `${FEATURE_LABEL[f]} <code>${f}</code>`;
    html("span", "env-state", name, out ? "outside the training range" : "inside");
    const bar = html("div", "env-bar", row);
    html("div", "env-in", bar);
    html("span", "env-lbl lo", bar, fmt(env[f][0], 2));
    html("span", "env-lbl hi", bar, fmt(env[f][1], 2));
    if (out) { const m = html("div", "env-mark", bar); m.style.left = "92%"; }
  }
  html("p", "note", parent, "The teal span is the range the training cells covered. A feature outside it means the model would be extrapolating, so no verdict is offered. Feature values for transfer cells are not carried in the demo bundle; the TRY IT tab shows them for your own file.");
  const det = html("details", "withheld", parent);
  html("summary", "", det, "What the model would have said (not earned)");
  kvList(det, [["Point estimate P(pass)", fmt(c.p_pass, 3)], ["Venn-ABERS interval", `[${fmt(c.p_lo, 3)}, ${fmt(c.p_hi, 3)}]`]]);
}

function renderQualInspector(insp, c) {
  inspectorHead(insp, shortId(c.id), c.split === "transfer"
    ? `Sandia · transfer cell, same A123 model · ${c.policy}`
    : `Severson · ${c.split === "train" ? "training split" : `held-out (${c.split})`} · charge ${c.policy}`);

  const cons = html("div", `consequence ${c.verdict}`, insp);
  cons.textContent = {
    pass: "Call it: this cell can come off the cycler. The interval clears the decision line.",
    fail: "Call it: reject early and reallocate the channel. The interval clears the line on the fail side.",
    "keep-testing": "Keep testing: the interval straddles the decision line, so 100 cycles cannot separate this cell from the spec.",
    "out-of-envelope": `Refused: ${c.violations?.join(" and ")} fall outside the training envelope. No verdict is offered; check the protocol match.`,
    train: "Reference cell: it trained the model, so it gets no verdict.",
  }[c.verdict];

  if (state.guided && c.id === "b1c6") {
    const g = html("div", "guided", insp);
    g.innerHTML = `<b>Watch the abstention work.</b> At cycle 100 the point estimate says pass (${fmt(c.p_pass)}). The interval [${fmt(c.p_lo)}, ${fmt(c.p_hi)}] straddles the line, so the verdict is <em>keep testing</em>. The cell died at ${c.cycle_life} cycles, ${T() - c.cycle_life} short of spec. A point estimate would have shipped it; the interval refused.
      <ol class="steps"><li>The run chart below shows the model even calling fail at cycle 40.</li><li>The capacity chart shows the spec line this cell never reached.</li><li>Pick any bar in the chart above to open another record.</li></ol>`;
  }

  if (c.evidence?.length) {
    const s = section(insp, "Run chart across cutoffs", "the model refit with data truncated at each cycle");
    s.appendChild(runChart(c.evidence));
    html("p", "note", s, "Each bar refits the model on data up to that cycle. The earliest cutoff where the bar clears the line is when the cell became callable; the allocation policy waits for two consecutive agreeing checkpoints before freeing the channel.");
  }

  if (c.verdict === "out-of-envelope") {
    const s = section(insp, "Training envelope");
    envelopePanel(s, c);
  }

  const s2 = section(insp, "Record");
  const L = lifeCell(c);
  kvList(s2, [
    ...(c.verdict !== "out-of-envelope" && c.verdict !== "train" ? [
      [`Calibrated P(pass ≥ ${T()} cycles)`, fmt(c.p_pass, 3)],
      ["Venn-ABERS interval", `[${fmt(c.p_lo, 3)}, ${fmt(c.p_hi, 3)}]`],
    ] : []),
    ["True cycle life", c.cycle_life != null ? `${c.cycle_life} cycles` : "≥ 2337, censored"],
    ["Against spec", L.delta === "censored" ? "still above 80% when the log ends" : `${L.delta} cycles`, L.cls === "short" ? "flag" : ""],
    ["Ground truth", c.label ? "pass" : "fail"],
  ]);

  const s3 = section(insp, "Capacity fade");
  const fade = cleanFade(c.fade);
  const xmax = Math.max(fade.cycle.at(-1), T() * 1.08);
  const annotations = [];
  if (c.cycle_life != null && c.cycle_life < T()) annotations.push({ x: c.cycle_life, y: 0.88, text: `died at ${c.cycle_life} · ${T() - c.cycle_life} short`, color: "var(--red)", anchor: "start", dy: -8 });
  s3.appendChild(lineChart({
    series: [{ x: fade.cycle, y: fade.qd, color: "var(--ink)", label: "" }],
    xlabel: "cycle", ylabel: "Qd (Ah)", xlim: [fade.cycle[0], xmax],
    refX: [{ v: 100, label: "cycle 100", color: "var(--slate)" }, { v: T(), label: `spec T = ${T()}`, color: "var(--red)" }],
    refY: [{ v: 0.88, label: "EOL 0.88 Ah", color: "var(--slate)" }],
    annotations,
  }));

  const s4 = section(insp, "Reading this record");
  const cc = state.data.qual.callable_curve.find((r) => r.cutoff === 100);
  html("p", "note ink", s4, c.split === "transfer"
    ? "Cross-lab transfer cell: the same A123 cell model, cycled at Sandia under a gentler protocol. The production ΔQ(V)-only features transfer (9 of 9 correct); the discarded protocol features called every one of these long-lived cells a fail."
    : c.verdict === "keep-testing"
      ? "The interval straddles the decision line: the early signal cannot separate this cell from the spec threshold yet. Keep cycling; this is the honest answer, not a model failure."
      : c.verdict === "train" ? "Training-split cell: it taught the model; it gets no verdict."
      : c.verdict === "fail"
        ? `The ΔQ(V) curve between cycles 10 and 100 already bulges the way short-lived cells do, so the interval sits entirely below the line. On the combined test set this rule called ${Math.round(cc.called_frac * 100)}% of cells at cycle 100 with ${Math.round(cc.acc_on_called * 100)}% accuracy.`
        : `The ΔQ(V) curve between cycles 10 and 100 is nearly flat, the signature of a long-lived cell, so the interval clears the line. On the combined test set this rule called ${Math.round(cc.called_frac * 100)}% of cells at cycle 100 with ${Math.round(cc.acc_on_called * 100)}% accuracy.`);
}

function renderDiagInspector(insp, c) {
  inspectorHead(insp, shortId(c.id), c.diag_rate
    ? `${c.chemistry} · ${c.temperature_C} °C · ${c.diag_rate} diagnostics · ${c.nominal_Ah} Ah · Oxford BDD-1`
    : `${c.chemistry} · ${c.temperature_C} °C · ${c.discharge_rate_C}C discharge · ${c.nominal_Ah} Ah · Sandia`);

  const tier = c.modes ? "quant" : c.chemistry === "LFP" ? "muted" : "hint";
  const cons = html("div", `consequence ${tier}`, insp);
  cons.textContent = tier === "quant"
    ? `Quantitative: LLI ${(c.modes.LLI.at(-1) * 100).toFixed(0)}% of capacity at end of test, trajectory stability ρ = ${c.modes.rho_LLI}. Earned by C/18.5 diagnostics and chemistry-matched references.`
    : tier === "muted"
      ? `Muted: LFP's flat 3.3 V plateau compresses the curve features into a ${c.v_dispersion.toFixed(2)} V band (NCA/NMC: 0.5 to 0.6 V). No mode attribution is offered for this chemistry.`
      : `Hint only: ${c.mode_hint.dominant} looks dominant with stability ρ = ${c.mode_hint.rho}${c.mode_hint.rho < 0.8 ? ", below the 0.8 trust bar" : ""}. Quantitative percentages did not pass the stability gate at 0.5C and are not shown.`;

  const s1 = section(insp, "Capacity fade");
  const fade = cleanFade(c.fade);
  s1.appendChild(lineChart({
    series: [{ x: fade.cycle, y: fade.qd, color: `var(--chem-${c.chemistry.toLowerCase()})`, label: "" }],
    xlabel: "cycle", ylabel: "Qd (Ah)",
  }));

  if (c.modes) {
    const sq = section(insp, "Degradation modes", "quantitative");
    const leg = html("div", "legend", sq);
    leg.innerHTML = `<span><span class="sw" style="background:var(--chem-nca)"></span>LLI (ρ = ${c.modes.rho_LLI})</span>
      <span><span class="sw" style="background:var(--chem-nmc)"></span>LAM_pe (ρ = ${c.modes.rho_LAM_pe})</span>
      <span><span class="sw" style="background:var(--chem-lfp)"></span>LAM_ne</span>
      <span><span class="sw" style="background:var(--slate)"></span>measured fade</span>`;
    sq.appendChild(lineChart({
      series: [
        { x: c.modes.cycle, y: c.modes.LLI.map((v) => v * 100), color: "var(--chem-nca)", label: "LLI" },
        { x: c.modes.cycle, y: c.modes.LAM_pe.map((v) => v * 100), color: "var(--chem-nmc)", label: "LAM_pe" },
        ...(c.modes.LAM_ne ? [{ x: c.modes.cycle, y: c.modes.LAM_ne.map((v) => v * 100), color: "var(--chem-lfp)", label: "LAM_ne" }] : []),
        { x: fade.cycle, y: fade.qd.map((v) => 100 * (1 - v / fade.qd[0])), color: "var(--slate)", label: "fade" },
      ],
      xlabel: "cycle", ylabel: "% of BOL", yfmt: (v) => fmt(v, 0),
    }));
    html("p", "note", sq, "The full three-way split is shown because this cell has diagnostics-grade C/18.5 pseudo-OCV data and chemistry-matched half-cell references. With generic references the anode term absorbs reference error; the pre-registered stability check went from 1 of 8 to 8 of 8 cells on matching. LAM_ne near zero is the physically expected answer: these cells age by lithium loss, not anode loss.");
  }

  const ages = ["fresh", "mid", "aged"];
  const ageColors = ["var(--age-1)", "var(--age-2)", "var(--age-3)"];
  const si = section(insp, "Incremental capacity", "dQ/dV");
  const legI = html("div", "legend", si);
  c.ica.forEach((d, i) => { legI.innerHTML += `<span><span class="sw" style="background:${ageColors[i]}"></span>${ages[i]} (cyc ${d.cycle})</span>`; });
  si.appendChild(lineChart({
    series: c.ica.map((d, i) => ({ x: d.v, y: d.dqdv, color: ageColors[i], label: `cyc ${d.cycle}` })),
    xlabel: "V", ylabel: "dQ/dV (Ah/V)", xfmt: (v) => fmt(v, 2), yfmt: (v) => fmt(v, 1),
  }));

  const sd = section(insp, "Differential voltage", "dV/dQ");
  const dvAll = c.dva.flatMap((d) => d.dvdq).filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  const p95 = dvAll[Math.floor(dvAll.length * 0.95)];
  sd.appendChild(lineChart({
    series: c.dva.map((d, i) => ({ x: d.q, y: d.dvdq, color: ageColors[i], label: `cyc ${d.cycle}` })),
    xlabel: "Q (Ah)", ylabel: "dV/dQ (V/Ah)", xfmt: (v) => fmt(v, 1), yfmt: (v) => fmt(v, 2), ylim: [0, p95 * 1.6],
  }));

  if (tier === "hint") {
    const sm = section(insp, "Dominant mode", "qualitative hint");
    const ml = html("div", "mode-line", sm);
    html("span", "mode-name", ml, c.mode_hint.dominant);
    html("span", "mode-rho", ml, `stability ρ = ${c.mode_hint.rho}`);
    if (c.mode_hint.rho < 0.8) html("span", "mode-warn", ml, "below the 0.8 trust bar");
    kvList(sm, [["Fit closure (median capacity error)", `${(c.mode_hint.closure_med * 100).toFixed(1)}% of nominal`]]);
  }
}

/* ---------- line chart with crosshair hover ---------- */

let _clipSeq = 0;

function lineChart({ series, w = inspectorWidth(), h = 190, xlabel = "", ylabel = "", refX = [], refY = [], xlim = null,
                     ylim = null, yfmt = (v) => fmt(v, 2), xfmt = (v) => String(Math.round(v)), annotations = [], xticks = null }) {
  const pad = { l: 46, r: 14, t: 22, b: 30 };
  const wrap = html("div", "chart");
  const svg = el("svg", { viewBox: `0 0 ${w} ${h}` }, wrap);
  const xs = series.flatMap((s) => s.x), ys = series.flatMap((s) => s.y);
  let xmin = Math.min(...xs), xmax = Math.max(...xs);
  if (xlim) [xmin, xmax] = xlim;
  let ymin, ymax;
  if (ylim) [ymin, ymax] = ylim;
  else {
    ymin = Math.min(...ys, ...refY.map((r) => r.v)); ymax = Math.max(...ys, ...refY.map((r) => r.v));
    const ypad = (ymax - ymin || 1) * 0.06; ymin -= ypad; ymax += ypad;
  }
  const X = (x) => pad.l + (x - xmin) / (xmax - xmin || 1) * (w - pad.l - pad.r);
  const Y = (y) => h - pad.b - (y - ymin) / (ymax - ymin || 1) * (h - pad.t - pad.b);

  for (let i = 0; i <= 3; i++) {
    const yv = ymin + (i / 3) * (ymax - ymin);
    el("line", { x1: pad.l, y1: Y(yv), x2: w - pad.r, y2: Y(yv), stroke: "var(--rule-soft)", "stroke-width": 1 }, svg);
    const t = el("text", { x: pad.l - 6, y: Y(yv) + 3, "text-anchor": "end", class: "axis-label" }, svg);
    t.textContent = yfmt(yv);
  }
  el("line", { x1: pad.l, y1: h - pad.b, x2: w - pad.r, y2: h - pad.b, stroke: "var(--rule)", "stroke-width": 1 }, svg);
  const ticks = xticks || [0, 1, 2, 3, 4].map((i) => xmin + (i / 4) * (xmax - xmin));
  for (const xv of ticks) {
    const t = el("text", { x: X(xv), y: h - pad.b + 14, "text-anchor": "middle", class: "axis-label" }, svg);
    t.textContent = xfmt(xv);
  }
  if (xlabel) { const t = el("text", { x: w - pad.r, y: h - 3, "text-anchor": "end", class: "axis-title" }, svg); t.textContent = xlabel; }
  if (ylabel) { const t = el("text", { x: pad.l - 6, y: 11, "text-anchor": "end", class: "axis-title" }, svg); t.textContent = ylabel; }

  for (const r of refX) {
    if (r.v < xmin || r.v > xmax) continue;
    el("line", { x1: X(r.v), y1: pad.t, x2: X(r.v), y2: h - pad.b, stroke: r.color || "var(--slate)", "stroke-width": 1, "stroke-dasharray": "4 3" }, svg);
    const t = el("text", { x: X(r.v) + 4, y: pad.t + 10, class: "ref-label", fill: r.color || "var(--slate)" }, svg);
    t.textContent = r.label;
  }
  for (const r of refY) {
    el("line", { x1: pad.l, y1: Y(r.v), x2: w - pad.r, y2: Y(r.v), stroke: r.color || "var(--slate)", "stroke-width": 1, "stroke-dasharray": "4 3" }, svg);
    const t = el("text", { x: w - pad.r - 4, y: Y(r.v) - 4, "text-anchor": "end", class: "ref-label", fill: r.color || "var(--slate)" }, svg);
    t.textContent = r.label;
  }

  const clipId = `clip${++_clipSeq}`;
  const clip = el("clipPath", { id: clipId }, el("defs", {}, svg));
  el("rect", { x: pad.l, y: pad.t, width: w - pad.l - pad.r, height: h - pad.t - pad.b }, clip);
  const paths = [];
  for (const s of series) {
    const d = s.x.map((x, i) => `${i ? "L" : "M"}${X(x).toFixed(1)},${Y(s.y[i]).toFixed(1)}`).join("");
    paths.push(el("path", { d, fill: "none", stroke: s.color, "stroke-width": 1.75, "stroke-linejoin": "round", "stroke-linecap": "round", "clip-path": `url(#${clipId})` }, svg));
  }
  if (!REDUCED) {
    requestAnimationFrame(() => paths.forEach((p, i) => {
      let len; try { len = p.getTotalLength(); } catch { return; }
      p.style.strokeDasharray = `${len}`; p.style.strokeDashoffset = `${len}`;
      p.getBoundingClientRect();
      p.style.transition = `stroke-dashoffset 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${i * 0.1}s`;
      p.style.strokeDashoffset = "0";
      p.addEventListener("transitionend", () => { p.style.strokeDasharray = "none"; }, { once: true });
    }));
  }
  const placed = [];
  for (const s of series.filter((s) => s.label)) {
    let ly = Math.min(Math.max(Y(s.y[s.y.length - 1]), pad.t + 10), h - pad.b - 4);
    while (placed.some((p) => Math.abs(p - ly) < 11)) ly -= 11;
    placed.push(ly);
    const t = el("text", { x: w - pad.r - 2, y: ly - 5, "text-anchor": "end", class: "series-label", fill: s.color }, svg);
    t.textContent = s.label;
  }
  for (const a of annotations) {
    const t = el("text", { x: Math.min(X(a.x) + 6, w - pad.r - 4), y: Y(a.y) + (a.dy || -6), class: "ref-label", fill: a.color || "var(--ink)", "text-anchor": a.anchor || "start" }, svg);
    if (X(a.x) > w * 0.6) { t.setAttribute("text-anchor", "end"); t.setAttribute("x", X(a.x) - 6); }
    t.textContent = a.text;
  }

  const tip = html("div", "chart-tip", wrap);
  const hover = el("rect", { x: pad.l, y: pad.t, width: w - pad.l - pad.r, height: h - pad.t - pad.b, fill: "transparent" }, svg);
  const cross = el("line", { x1: 0, y1: pad.t, x2: 0, y2: h - pad.b, stroke: "var(--ink)", "stroke-width": 1, opacity: 0 }, svg);
  hover.addEventListener("mousemove", (ev) => {
    const box = svg.getBoundingClientRect();
    const px = (ev.clientX - box.left) * (w / box.width);
    const xv = xmin + (px - pad.l) / (w - pad.l - pad.r) * (xmax - xmin);
    cross.setAttribute("x1", px); cross.setAttribute("x2", px); cross.setAttribute("opacity", 0.3);
    const lines = series.map((s) => {
      let best = 0;
      for (let i = 1; i < s.x.length; i++) if (Math.abs(s.x[i] - xv) < Math.abs(s.x[best] - xv)) best = i;
      return `${s.label || ylabel || "y"} ${yfmt(s.y[best])}`;
    });
    tip.innerHTML = `<b>${xfmt(xv)}</b> ${xlabel}<br>` + lines.join("<br>");
    tip.classList.add("show");
    tip.style.left = `${Math.min(Math.max((px / w) * 100, 16), 84)}%`;
    tip.style.top = `${(pad.t / h) * 100 + 14}%`;
  });
  hover.addEventListener("mouseleave", () => { tip.classList.remove("show"); cross.setAttribute("opacity", 0); });
  return wrap;
}

/* ---------- gates ---------- */

function check(ok, text) {
  const s = html("span", `check ${ok ? "pass" : "fail"}`);
  s.appendChild(icon(ok ? "i-check" : "i-cross", 13, 13));
  s.append(text);
  return s;
}

function renderGates() {
  const pane = document.getElementById("pane-gates");
  if (pane.dataset.rendered) return;
  pane.dataset.rendered = "1";
  const grid = html("div", "gates", pane);
  const q = state.data.qual, dg = state.data.diag;

  const g1 = html("section", "gate", grid);
  const h1 = html("h2", "", g1, "Early qualification call");
  html("span", "ships", h1, "ships as decision support: calibrated probability, Venn-ABERS interval, an explicit keep-testing verdict, and a refusal outside the training envelope");
  const t1 = html("table", "", g1);
  t1.innerHTML = `<thead><tr><th>run</th><th class="num">balanced acc</th><th class="num">ECE</th><th>verdict</th></tr></thead>`;
  const tb = html("tbody", "", t1);
  const rows = [
    ["pre-registered (the official gate)", q.gate.prereg.acc, q.gate.prereg.ece, false, "missed the calibration bar (ECE > 0.10)"],
    ["hardened (selected on the training split)", q.gate.hardened.acc, q.gate.hardened.ece, true, "meets both bars"],
    ["production, ΔQ(V) features only (shipped here)", q.gate.production.acc, q.gate.production.ece, true, "meets both bars; transfers across labs"],
  ];
  for (const [name, acc, ece, ok, txt] of rows) {
    const tr = html("tr", "", tb);
    html("td", name.includes("shipped") ? "big" : "", tr, name);
    html("td", "num", tr, fmt(acc, 3));
    html("td", "num", tr, fmt(ece, 3));
    html("td", "", tr).appendChild(check(ok, txt));
  }
  const tr = html("div", "transfer-result", g1);
  html("b", "tr-num bad", tr, "0 / 9"); html("span", "tr-lbl", tr, "cross-lab transfer with the full feature set: a charge-time covariate 50σ out of range called every healthy Sandia cell a fail");
  html("b", "tr-num good", tr, "9 / 9"); html("span", "tr-lbl", tr, "with the ΔQ(V)-only features shipped here, which cancel protocol effects; the envelope guard exists because of this result");
  html("p", "gate-note", g1).innerHTML = `The first model was rejected as written: accuracy 0.924 but ECE 0.105 against a 0.10 bar. The hardened run selected isotonic calibration by nested cross-validation on the training split only. <b>n = 83 held-out cells</b> (43 primary, 40 secondary); batch 3 has only 2 true fails, so the fail class is thin there.`;
  const sm = html("div", "small-multiples", g1);
  const cc = q.callable_curve;
  const c1 = html("div", "", sm); html("h3", "", c1, "Cells callable at each cutoff, %");
  c1.appendChild(lineChart({ series: [{ x: cc.map((r) => r.cutoff), y: cc.map((r) => r.called_frac * 100), color: "var(--ink)", label: "" }],
    w: 300, h: 170, xlabel: "cutoff cycle", ylim: [0, 100], yfmt: (v) => fmt(v, 0), xticks: cc.map((r) => r.cutoff),
    refX: [{ v: 60, label: "cycle-60 dip, unexplained", color: "var(--red)" }] }));
  const c2 = html("div", "", sm); html("h3", "", c2, "Accuracy on the cells called, %");
  c2.appendChild(lineChart({ series: [{ x: cc.map((r) => r.cutoff), y: cc.map((r) => Math.min(100, r.acc_on_called * 100)), color: "var(--green)", label: "" }],
    w: 300, h: 170, xlabel: "cutoff cycle", ylim: [0, 100], yfmt: (v) => fmt(v, 0), xticks: cc.map((r) => r.cutoff) }));
  const ct = html("table", "callable-table", g1);
  ct.innerHTML = `<thead><tr><th>cutoff</th>${cc.map((r) => `<th class="num">${r.cutoff}</th>`).join("")}</tr></thead>
    <tbody><tr><td>called, of 83</td>${cc.map((r) => `<td class="num">${Math.round(r.called_frac * 83)}</td>`).join("")}</tr>
    <tr><td>accuracy on called</td>${cc.map((r) => `<td class="num">${Math.round(r.acc_on_called * 100)}%</td>`).join("")}</tr></tbody>`;
  html("p", "gate-note", g1).innerHTML = `The dip at cutoff 60 survives every model variant tried and has no explanation yet. It is documented rather than smoothed over; with n = 83 a single cutoff moves by a few cells.`;

  const g2 = html("section", "gate", grid);
  const h2 = html("h2", "", g2, "Degradation-mode engine");
  html("span", "ships", h2, "ships as curve tracking with fade-closure QC; quantitative modes only where the data earns them");
  const t2 = html("table", "", g2);
  t2.innerHTML = `<thead><tr><th>check</th><th class="num">result</th><th></th></tr></thead>`;
  const tb2 = html("tbody", "", t2);
  for (const [name, val, ok] of [
    ["fade closure ≤ 3% of nominal", `${Math.round(dg.gate.fade_closure.frac_ok * 100)}% of NCA + NMC`, dg.gate.fade_closure.pass],
    ["mode sanity ρ ≥ 0.8 on ≥ 70%", `${Math.round(dg.gate.mode_sanity.frac_ok * 100)}%`, dg.gate.mode_sanity.pass],
    ["chemistry contrast ≥ 3×", `${dg.gate.chemistry_contrast.ratio}×`, dg.gate.chemistry_contrast.pass],
    ["condition systematics", `${dg.gate.condition_systematics.n_confirmed} of 3 Preger trends`, dg.gate.condition_systematics.pass],
  ]) {
    const r = html("tr", "", tb2);
    html("td", "", r, name); html("td", "num", r, val); html("td", "", r).appendChild(check(ok, ok ? "pass" : "fail"));
  }
  html("p", "gate-note", g2).innerHTML = `NCA decomposition is unidentifiable from 0.5C curves with generic half-cell references: five stabilization variants were tried and the boundary is physical, not a bug. So the interface shows a <b>hint with its stability score</b> for NCA and NMC, <b>nothing</b> for LFP, and a <b>quantitative split</b> only for the Oxford cells, where C/18.5 diagnostics and matched Kokam references took the pre-registered stability check from 1 of 8 to 8 of 8.`;
}

/* ---------- science ---------- */

function renderScience() {
  const pane = document.getElementById("pane-science");
  if (pane.dataset.rendered) return;
  pane.dataset.rendered = "1";
  pane.innerHTML = `
  <article class="reading">
    <h2>Three ideas, each earned the hard way.</h2>
    <p class="lead">Everything on the Fleet tab rests on three pieces of science: a signal that predicts cycle life from the first 100 cycles, a probability that is honest about its own uncertainty, and a way to read what is degrading from the shape of a voltage curve. This page explains each, including where they fail, because knowing that is most of the engineering.</p>

    <h3>The signal: ΔQ(V)</h3>
    <p>A battery's discharge curve, voltage falling as charge is drawn, is a fingerprint of its internal state. Early degradation barely moves the total capacity, which is why extrapolating a fade curve from 100 cycles fails: at cycle 100 most cells have lost almost nothing. Degradation does something subtler first. It <strong>redistributes where charge is stored along the voltage axis</strong>, as lithium is consumed by side reactions and electrode kinetics shift.</p>
    <p>Severson et&nbsp;al. (2019) showed how to expose this. Interpolate each cycle's discharge capacity onto a fixed grid of voltages, so curves from different cycles become directly subtractable, then take the difference between an early and a later cycle:</p>
    <div class="eq">ΔQ(V) = Q<sub>cycle 100</sub>(V) − Q<sub>cycle 10</sub>(V)</div>
    <p>For a healthy long-lived cell this difference is nearly flat. For a cell that will die young it already bulges at cycle 100, and the <strong>variance</strong> of ΔQ(V) is strikingly log-linear with eventual cycle life. Hectocycle's production model uses three statistics of this curve (<span class="mono">log₁₀ var</span>, <span class="mono">log₁₀ |min|</span>, <span class="mono">log₁₀ |mean|</span>) and nothing else.</p>
    <div class="callout"><strong>Why nothing else?</strong> The first model also used protocol covariates: charge time, internal resistance. In-domain they helped. Then we scored the model on the same cell model cycled in a different lab. Charge time there was about 2 hours instead of 7 to 11 minutes, roughly 50σ outside training, and the model confidently failed every healthy cell: <strong>0 of 9 correct</strong>. The ΔQ(V)-only model, a within-cell difference that cancels protocol effects, scored <strong>9 of 9</strong>. That experiment is why the fleet has a refusal: any input outside the training range gets no verdict, not a guess.</div>

    <h3>Honest probability: calibration and the interval</h3>
    <p>A qualification call feeds cost decisions, so the number attached to it must mean what it says: among cells given P(pass) = 0.9, about 90% should actually pass. That property is <strong>calibration</strong>, and it does not come free; a well-fit classifier can still be badly overconfident. Hectocycle measures it as expected calibration error (ECE) and treats it as a shipping gate. The first model was rejected with accuracy 0.92 because its ECE missed the bar (0.105 against 0.10).</p>
    <p>The production pipeline earns calibration twice. First, an isotonic map, a monotone and shape-free curve, is fitted from the classifier's raw scores to observed pass rates using only out-of-fold predictions, so the map never grades its own homework. Second, every cell also gets a <strong>Venn-ABERS interval</strong>: the calibration is refit twice per cell, once forcing its label to fail and once to pass, and the two answers [p₀,&nbsp;p₁] bracket what the probability is allowed to be. The width of that band is the model confessing how much it could be swayed, a guarantee that holds without distributional assumptions (Vovk &amp; Petej, 2014).</p>
    <div class="eq">verdict = PASS if p₀ &gt; 0.5 · FAIL if p₁ &lt; 0.5 · otherwise KEEP TESTING</div>
    <p>The abstention is the product's core honesty. On held-out test cells the rule calls <strong>74% of the fleet at cycle 100 with 100% accuracy on the calls</strong>, and the cells it refuses to call are precisely the ones whose true lives sit near the 700-cycle spec, where more testing is genuinely the right answer. Turned into a stopping policy that waits for two consecutive agreeing checkpoints, it frees 60 of 83 channels with zero wrong verdicts and cuts cycler-hours by 67%.</p>

    <h3>Reading degradation: ICA, DVA, and the three modes</h3>
    <p>The Diagnostics fleet asks a different question: not how long a cell will live, but what is killing it. The tools are two derivatives of the same slow charge curve. <strong>Incremental capacity</strong> (dQ/dV) turns flat plateaus into peaks, each peak a phase transition in an electrode as lithium fills successive lattice environments. <strong>Differential voltage</strong> (dV/dQ) does the inverse. As a cell ages these peaks shift, shrink, and separate, and the pattern of change is a signature of the mechanism.</p>
    <p>To turn signatures into numbers, Hectocycle fits each diagnostic curve with an electrode-alignment model in the tradition of Dahn's group:</p>
    <div class="eq">V(Q) = U<sub>pe</sub>(y₀ − Q/C<sub>pe</sub>) − U<sub>ne</sub>(x₀ + Q/C<sub>ne</sub>) + η</div>
    <p>Here U<sub>pe</sub> and U<sub>ne</sub> are reference potential curves for each electrode, and the fitted parameters say how much of each electrode is still active (C<sub>pe</sub>, C<sub>ne</sub>) and how the two are offset. Tracking them over life yields the three canonical degradation modes: <strong>LLI</strong>, loss of cyclable lithium consumed by SEI growth; <strong>LAM<sub>pe</sub></strong> and <strong>LAM<sub>ne</sub></strong>, loss of active material in the positive and negative electrode.</p>
    <p>The catch is <strong>identifiability</strong>: many parameter combinations can fit one smooth curve. We mapped exactly where the attribution can be trusted.</p>
    <table>
      <thead><tr><th>Data available</th><th>What is trustworthy</th><th>Evidence</th></tr></thead>
      <tbody>
      <tr><td>0.5C aging cycles + generic references</td><td>Curve tracking only, no mode split</td><td>NCA trajectories unstable across 5 fitting strategies</td></tr>
      <tr><td>~C/20 diagnostics + generic references</td><td>LLI and LAM<sub>pe</sub></td><td>ρ ≥ 0.92 on 8 of 8 Oxford cells; LAM<sub>ne</sub> absorbs reference error</td></tr>
      <tr><td>~C/20 diagnostics + matched half-cell references</td><td>Full three-way split</td><td>Pre-registered stability gate: 1 of 8 to <strong>8 of 8</strong>, ρ = 1.00</td></tr>
      </tbody>
    </table>
    <p>This ladder is enforced in the interface. LFP cells are marked muted (their flat 3.3&nbsp;V plateau compresses every feature into a 0.15&nbsp;V band), Sandia NCA and NMC cells get a qualitative hint with its stability score, and only the Oxford fleet, which has diagnostics-grade data and matched references, shows quantitative percentages.</p>

    <h3>The method: gates before features</h3>
    <p>Every capability above passed a <strong>pre-registered, falsifiable gate</strong> before it was allowed into the interface: pass criteria written down first, evaluated once, decisions taken as written. Two of the three validation studies initially missed their bars, the early call on calibration and the mode engine on stability, and the teardowns of those failures produced the two most valuable results in the project: the protocol-transfer discovery and the identifiability ladder. The Gates tab shows every number; the full teardown documents live in the repository.</p>
    <div class="stats">
      <div class="stat"><b>124 + 70 + 8</b><span>cells: Severson, Sandia, Oxford</span></div>
      <div class="stat"><b>0.043</b><span>production ECE, bar ≤ 0.10</span></div>
      <div class="stat"><b>1/8 → 8/8</b><span>mode stability, generic to matched references</span></div>
    </div>

    <div class="refs">
      <h3>Sources</h3>
      <p>Severson et&nbsp;al., <em>Nature Energy</em> 2019 (early prediction from ΔQ(V)) · Preger et&nbsp;al., <em>J.&nbsp;Electrochem.&nbsp;Soc.</em> 2020 (Sandia degradation study) · Birkl &amp; Howey 2017 (Oxford degradation dataset and OCV modelling) · Vovk &amp; Petej 2014 (Venn-ABERS predictors) · half-cell references from PyBaMM parameter sets and the Battery Intelligence Lab's SLIDE.</p>
      <p>Full teardowns: <a href="https://github.com/arjunsharma6251/hectocycle" target="_blank" rel="noopener">github.com/arjunsharma6251/hectocycle</a> (docs/early-call-study.md, docs/degradation-modes-study.md, docs/mode-identifiability-study.md).</p>
    </div>
  </article>`;
}

/* ---------- TRY IT: score your own cell, entirely in the browser ---------- */

/* isotonic regression via pool-adjacent-violators; ties on x averaged first
   (mirrors sklearn). Returns { ux, fitted }: fitted value per unique x. */
function pava(xs, ys) {
  const order = xs.map((_, i) => i).sort((a, b) => xs[a] - xs[b]);
  const xsS = order.map((i) => xs[i]), ysS = order.map((i) => ys[i]);
  const ux = [], uy = [], uw = [];
  for (let i = 0; i < xsS.length; i++) {
    if (ux.length && xsS[i] === ux[ux.length - 1]) {
      const k = ux.length - 1;
      uy[k] = (uy[k] * uw[k] + ysS[i]) / (uw[k] + 1);
      uw[k] += 1;
    } else { ux.push(xsS[i]); uy.push(ysS[i]); uw.push(1); }
  }
  const vals = [], wts = [], cnt = [];
  for (let i = 0; i < uy.length; i++) {
    vals.push(uy[i]); wts.push(uw[i]); cnt.push(1);
    while (vals.length > 1 && vals[vals.length - 2] >= vals[vals.length - 1]) {
      const n = vals.length;
      const v = (vals[n - 2] * wts[n - 2] + vals[n - 1] * wts[n - 1]) / (wts[n - 2] + wts[n - 1]);
      wts[n - 2] += wts[n - 1]; cnt[n - 2] += cnt[n - 1];
      vals.pop(); wts.pop(); cnt.pop();
      vals[vals.length - 1] = v;
    }
  }
  const fitted = [];
  for (let b = 0; b < vals.length; b++) for (let r = 0; r < cnt[b]; r++) fitted.push(vals[b]);
  return { ux, fitted };
}

function linearScore(params, x) {
  let z = params.intercept;
  for (let i = 0; i < x.length; i++) z += ((x[i] - params.mean[i]) / params.scale[i]) * params.coef[i];
  return z;
}

function scoreCell(feats) {
  const m = state.data.qual.model;
  const x = m.features.map((f) => feats[f]);
  const z = linearScore(m.point, x);
  const xs = m.point.iso_x, ys = m.point.iso_y;
  let p;
  if (z <= xs[0]) p = ys[0];
  else if (z >= xs[xs.length - 1]) p = ys[ys.length - 1];
  else {
    let i = 0;
    while (xs[i + 1] < z) i++;
    const t = xs[i + 1] === xs[i] ? 0 : (z - xs[i]) / (xs[i + 1] - xs[i]);
    p = ys[i] + t * (ys[i + 1] - ys[i]);
  }
  const p0s = [], p1s = [];
  for (const fold of m.cvap) {
    const s0 = linearScore(fold, x);
    for (const label of [0, 1]) {
      const { ux, fitted } = pava([...fold.cal_scores, s0], [...fold.cal_labels, label]);
      let idx = ux.findIndex((v) => v >= s0);
      if (idx === -1) idx = ux.length - 1;
      (label === 0 ? p0s : p1s).push(fitted[idx]);
    }
  }
  const mean = (a) => a.reduce((s, v) => s + v, 0) / a.length;
  const p0 = mean(p0s), p1 = mean(p1s);
  const env = state.data.qual.envelope;
  const violations = m.features.filter((f) => feats[f] < env[f][0] || feats[f] > env[f][1]);
  const verdict = violations.length ? "out-of-envelope" : (p0 > 0.5 ? "pass" : p1 < 0.5 ? "fail" : "keep-testing");
  return { p, p0, p1, verdict, violations, feats };
}

/* CSV -> DeltaQ(V) features. Expects discharge points for cycles ~10 and ~100. */
function featurizeCsv(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (lines.length < 20) throw new Error("That file looks too short. Expected discharge time-series rows for cycles 10 and 100.");
  const header = lines[0].toLowerCase().split(",").map((h) => h.trim());
  const col = (names) => header.findIndex((h) => names.some((n) => h === n || h.startsWith(n)));
  const ci = col(["cycle"]);
  const vi = col(["voltage", "v"]);
  const qi = col(["discharge_capacity", "capacity", "q"]);
  if (ci === -1 || vi === -1 || qi === -1)
    throw new Error("Could not find the columns. The header must include cycle, voltage_v, and discharge_capacity_ah (see the sample file).");
  const byCycle = new Map();
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    const c = Math.round(+parts[ci]), v = +parts[vi], q = +parts[qi];
    if (!Number.isFinite(c) || !Number.isFinite(v) || !Number.isFinite(q)) continue;
    if (!byCycle.has(c)) byCycle.set(c, []);
    byCycle.get(c).push([v, q]);
  }
  const nearest = (target, tol) => {
    let best = null;
    for (const c of byCycle.keys()) if (Math.abs(c - target) <= tol && (best === null || Math.abs(c - target) < Math.abs(best - target))) best = c;
    return best;
  };
  const cE = nearest(10, 3), cL = nearest(100, 5);
  if (cE === null || cL === null)
    throw new Error(`Need discharge data at cycle ~10 and cycle ~100. Found cycles: ${[...byCycle.keys()].sort((a, b) => a - b).slice(0, 12).join(", ")}${byCycle.size > 12 ? "…" : ""}`);
  const seg = (c) => {
    const pts = byCycle.get(c).filter((p) => p[1] >= 0).sort((a, b) => a[0] - b[0]);
    if (pts.length < 20) throw new Error(`Cycle ${c} has only ${pts.length} usable points. A full discharge branch is needed.`);
    return pts;
  };
  const A = seg(cE), B = seg(cL);
  const vLo = Math.max(A[0][0], B[0][0]) + 0.01;
  const vHi = Math.min(A[A.length - 1][0], B[B.length - 1][0]) - 0.01;
  if (vHi <= vLo) throw new Error("The two cycles' voltage ranges do not overlap. Check that the voltage column is in volts.");
  const interp = (pts, v) => {
    let i = 0;
    while (i < pts.length - 2 && pts[i + 1][0] < v) i++;
    const [v0, q0] = pts[i], [v1, q1] = pts[i + 1];
    return v1 === v0 ? q0 : q0 + (q1 - q0) * (v - v0) / (v1 - v0);
  };
  const N = 1000, dq = [];
  for (let k = 0; k < N; k++) {
    const v = vLo + (k / (N - 1)) * (vHi - vLo);
    dq.push(interp(B, v) - interp(A, v));
  }
  const meanDq = dq.reduce((s, v) => s + v, 0) / N;
  const varDq = dq.reduce((s, v) => s + (v - meanDq) ** 2, 0) / N;
  const minDq = Math.min(...dq);
  const EPS = 1e-12;
  return {
    feats: {
      log_var_dq: Math.log10(varDq + EPS),
      log_min_dq: Math.log10(Math.abs(minDq) + EPS),
      log_mean_dq: Math.log10(Math.abs(meanDq) + EPS),
    },
    cycles: [cE, cL], nPts: [A.length, B.length],
  };
}

function renderTry() {
  const pane = document.getElementById("pane-try");
  if (pane.dataset.rendered) return;
  pane.dataset.rendered = "1";
  pane.innerHTML = `
  <div class="reading">
    <h2>Drop a CSV. Get a verdict. Nothing leaves your browser.</h2>
    <p class="lead">Export the discharge time-series of <strong>cycle 10</strong> and <strong>cycle 100</strong> from your cycler as three columns: <span class="mono">cycle, voltage_v, discharge_capacity_ah</span>. Hectocycle computes the ΔQ(V) features and scores them with the exact production model: the same coefficients, the same calibration, the same envelope guard. All of it runs locally.</p>
    <div class="dropzone" id="dropzone" tabindex="0" role="button" aria-label="Choose a cell CSV to score">
      <svg><use href="#i-upload"/></svg>
      <span class="dz-main">Drop your CSV here, or click to choose</span>
      <span class="dz-sub"><a href="sample_cell.csv" download id="sample-link">Download a sample file</a>: a real Sandia LFP cell this model never trained on</span>
    </div>
    <input type="file" id="try-file" accept=".csv,text/csv" hidden>
    <div id="try-result"></div>
  </div>`;
  const dz = pane.querySelector("#dropzone");
  const input = pane.querySelector("#try-file");
  dz.addEventListener("click", (e) => { if (e.target.tagName !== "A") input.click(); });
  dz.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
  dz.addEventListener("drop", (e) => { e.preventDefault(); dz.classList.remove("drag"); if (e.dataTransfer.files[0]) handleTryFile(e.dataTransfer.files[0]); });
  input.addEventListener("change", () => { if (input.files[0]) handleTryFile(input.files[0]); });
}

function handleTryFile(file) {
  const out = document.getElementById("try-result");
  out.innerHTML = "";
  if (file.size > 12 * 1024 * 1024) {
    html("div", "try-error", out, `That file is ${(file.size / 1048576).toFixed(0)} MB. Export only cycles 10 and 100 (a few thousand rows) and try again.`);
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    let parsed;
    try { parsed = featurizeCsv(reader.result); }
    catch (err) { html("div", "try-error", out, err.message); return; }
    const r = scoreCell(parsed.feats);
    const card = html("div", "try-result", out);
    const head = html("div", "insp-head", card);
    const t = html("div", "", head);
    html("div", "insp-title", t, file.name);
    html("div", "insp-sub", t, `ΔQ(V) from cycles ${parsed.cycles[0]} → ${parsed.cycles[1]} · ${parsed.nPts[0]} + ${parsed.nPts[1]} points · scored in your browser`);
    const cons = html("div", `consequence ${r.verdict}`, card);
    cons.textContent = {
      pass: "Call it: this cell can come off the cycler.",
      fail: "Call it: reject early and reallocate the channel.",
      "keep-testing": "Keep testing: the interval straddles the decision line.",
      "out-of-envelope": `Refused: ${r.violations.map((f) => FEATURE_LABEL[f]).join(" and ")} outside the training envelope. The model refuses rather than extrapolate.`,
    }[r.verdict];
    const s = section(card, r.verdict === "out-of-envelope" ? "What the model would have said (not earned)" : "Record");
    if (r.verdict !== "out-of-envelope") {
      const ib = html("div", "", s); ib.style.margin = "4px 0 12px";
      ib.appendChild(intervalBar({ p_pass: r.p, p_lo: r.p0, p_hi: r.p1, verdict: r.verdict }));
    }
    kvList(s, [
      [`Calibrated P(pass ≥ ${T()} cycles)`, fmt(r.p, 3)],
      ["Venn-ABERS interval", `[${fmt(r.p0, 3)}, ${fmt(r.p1, 3)}]`],
      ...state.data.qual.model.features.map((f) => {
        const [lo, hi] = state.data.qual.envelope[f];
        const ok = r.feats[f] >= lo && r.feats[f] <= hi;
        return [FEATURE_LABEL[f], `${fmt(r.feats[f], 3)} · ${ok ? "in envelope" : `outside [${fmt(lo)}, ${fmt(hi)}]`}`, ok ? "" : "flag"];
      }),
    ]);
    html("p", "note", s, `Frame of reference: the model was trained on 1.1 Ah LFP fast-charge cells against a ${T()}-cycle spec. For other chemistries or specs, treat this as an out-of-distribution demonstration; the envelope guard exists for exactly that reason.`);
  };
  reader.readAsText(file);
}

/* ---------- fleet switch, search, boot ---------- */

function renderFleetAll(first = false) {
  renderChartHead();
  renderFleetChart();
  renderDisposition(first);
  renderLog();
}

document.querySelectorAll(".seg").forEach((s) => s.addEventListener("click", () => {
  if (state.fleet === s.dataset.fleet) return;
  state.fleet = s.dataset.fleet;
  state.queue = null; state.search = ""; state.sortKey = null; state.sortDir = 1;
  document.getElementById("search").value = "";
  document.querySelectorAll(".seg").forEach((x) => x.setAttribute("aria-pressed", x === s));
  state.selected = null; state.guided = false;
  renderFleetAll(!state.arrived[state.fleet]);
  renderIdleInspector();
  updateHash();
}));

document.getElementById("search").addEventListener("input", (e) => {
  state.search = e.target.value;
  renderDisposition(); renderLog(); renderFleetChart();
});

fetch("cockpit_data.json")
  .then((r) => r.json())
  .then((data) => {
    state.data = data;
    const raw = location.hash.replace("#", "");
    const [hFleet, hId] = raw.split("/");
    if (hFleet === "diag" || hFleet === "qual") {
      state.fleet = hFleet;
      document.querySelectorAll(".seg").forEach((x) => x.setAttribute("aria-pressed", x.dataset.fleet === hFleet));
    }
    renderFleetAll(true);
    if (hId && fleetCells().some((c) => c.id === hId)) select(hId, { scroll: true });
    else {
      renderIdleInspector();
      if (TABS.includes(raw) && raw !== "fleet") showTab(raw);
      else if (!localStorage.getItem("hectocycle-welcomed")) showWelcome();
    }
  })
  .catch((e) => {
    document.getElementById("pane-fleet").innerHTML =
      `<div class="insp-idle"><h3>The fleet data did not load.</h3><p>Reload the page. If this keeps happening, the demo bundle may be missing from the host. (${e.message})</p></div>`;
  });
