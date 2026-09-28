/* Hectocycle core: cycler-file parsing, DeltaQ(V) features and model scoring.
 *
 * DOM-free, so it runs in the page (window.HectoCore) and under Node
 * (module.exports) for tests/js/parity.mjs. Parsing and featurizing mirror
 * src/ingest.py and src/transfer.py line for line; scoring mirrors the
 * exported EarlyVerdictModel + cross Venn-ABERS (tests/test_model_export.py).
 */
(function (root) {
  "use strict";

  const BINARY_EXT = { ".nda": "Neware", ".ndax": "Neware", ".mpr": "BioLogic", ".res": "Arbin", ".xlsx": "Excel", ".xls": "Excel" };
  const DEADBAND_A = 0.05;
  const EARLY = [10, 3], LATE = [100, 5];
  const EPS = 1e-12;
  const V_WINDOW = [2.0, 3.5];
  const DQ_FEATURES = ["log_var_dq", "log_min_dq", "log_mean_dq"];

  const CYCLE = new Set(["cycleindex", "cycleid", "cycle", "cyclenumber", "cyclec", "cyc"]);
  const VOLT = new Set(["voltage", "volts", "ewe", "ecell", "voltagev"]);
  const CURR = new Set(["current", "amps", "i", "currenta"]);
  const QDIS = new Set(["dischargecapacity", "capacitancedchg", "dchgcap", "qdischarge", "dischargecapacityah", "dchgcapacity"]);
  const QANY = new Set(["amphr", "capacity"]);
  const STATE = new Set(["state", "md"]);
  const STEP = new Set(["step", "stepindex", "stepid", "ns"]);
  const SCALE = { v: 1, mv: 1e-3, a: 1, ma: 1e-3, ah: 1, ahr: 1, mah: 1e-3 };

  class IngestError extends Error {}

  function parseHeader(h) {
    h = h.trim().toLowerCase();
    const m = h.match(/^(.*?)\s*[(/]\s*([^)]*)\)?\s*$/);
    const name = m ? m[1] : h, unit = m ? m[2] : "";
    return [name.replace(/[^a-z0-9]/g, ""), unit.replace(/[^a-z]/g, "")];
  }

  function num(s) {
    s = s.trim();
    if (s.includes(",") && !s.includes(".")) s = s.replace(/,/g, ".");
    if (s === "") return NaN;
    const v = Number(s);
    return Number.isNaN(v) ? NaN : v;
  }

  function splitTable(lines) {
    const head = lines[0];
    const count = (d) => head.split(d).length - 1;
    let delim = "\t";
    for (const d of [",", ";"]) if (count(d) > count(delim)) delim = d;
    return [head.split(delim), lines.slice(1).map((ln) => ln.split(delim))];
  }

  const find = (cols, names) => cols.findIndex(([n]) => names.has(n));

  function csvFields(line) {  // quote-aware split, as Python's csv.reader
    const out = []; let cur = "", q = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (q) {
        if (ch === '"') { if (line[i + 1] === '"') { cur += '"'; i++; } else q = false; }
        else cur += ch;
      } else if (ch === '"') q = true;
      else if (ch === ",") { out.push(cur); cur = ""; }
      else cur += ch;
    }
    out.push(cur);
    return out;
  }

  /* Discharge segments from step-structured exports (Maccor, nested Neware); mirrors _Segments in src/ingest.py. */
  class Segments {
    constructor() { this.rows = []; this.seg = -1; this.cycle = null; this.step = null; this.offset = 0; this.lastQ = 0; this.charged = true; }
    charge() { this.charged = true; }
    discharge(cycle, step, v, q) {
      if (this.charged || cycle !== this.cycle) { this.seg++; this.offset = 0; this.lastQ = 0; }
      else if (step !== this.step) this.offset += this.lastQ;
      this.charged = false; this.cycle = cycle; this.step = step; this.lastQ = q;
      this.rows.push([this.seg, cycle, v, q + this.offset]);
    }
    cycles() {
      const segs = new Map();
      for (const [seg, c, v, q] of this.rows) {
        if (!segs.has(seg)) segs.set(seg, [c, [], []]);
        segs.get(seg)[1].push(v); segs.get(seg)[2].push(q);
      }
      const nCyc = new Set([...segs.values()].map(([c]) => c)).size;
      const renumber = segs.size > 1.5 * nCyc;
      const best = new Map();
      [...segs.keys()].sort((a, b) => a - b).forEach((seg, i) => {
        const [c, vs, qs] = segs.get(seg);
        const key = renumber ? i + 1 : c;
        if (!best.has(key) || Math.max(...qs) > Math.max(...best.get(key)[1])) best.set(key, [vs, qs]);
      });
      const out = new Map();
      for (const key of [...best.keys()].sort((a, b) => a - b)) {
        const [vs, qs] = best.get(key);
        out.set(key, { I: vs.map(() => -1), V: vs, Q: qs });
      }
      return out;
    }
  }

  /* Nested Neware BTS export (cycle / step / record rows interleaved), or null. */
  function newareNested(lines) {
    const rows = lines.map(csvFields);
    if (rows.length < 4 || !CYCLE.has(parseHeader(rows[0][0])[0])) return null;
    if (rows[1].length < 3 || rows[2].length < 3 || rows[2][0].trim() || rows[2][1].trim()) return null;
    const rec = rows[2].map(parseHeader);
    const vi = find(rec, VOLT), ii = find(rec, CURR), qi = find(rec, new Set(["capacity"]));
    if (Math.min(vi, ii, qi) < 0) return null;
    const vs = SCALE[rec[vi][1]] ?? 1, qs = SCALE[rec[qi][1]] ?? 1;
    const segs = new Segments();
    let cyc = null, step = "", dis = false;
    for (const r of rows.slice(3)) {
      if (r.length && r[0].trim()) cyc = Math.round(num(r[0]));
      else if (r.length > 2 && r[1].trim()) {
        step = r[1].trim();
        const name = r[2].trim().toLowerCase();
        dis = name.includes("dchg");
        if (name.includes("chg") && !dis) segs.charge();
      } else if (cyc !== null && dis && r.length > Math.max(vi, ii, qi)) {
        const v = num(r[vi]) * vs, q = num(r[qi]) * qs;
        if (Number.isFinite(v) && Number.isFinite(q)) segs.discharge(cyc, step, v, q);
      }
    }
    return segs.cycles();
  }

  function readText(text, filename = "") {
    const dot = filename.lastIndexOf(".");
    const ext = dot >= 0 ? filename.slice(dot).toLowerCase() : "";
    if (BINARY_EXT[ext])
      throw new IngestError(`${filename} is a binary ${BINARY_EXT[ext]} file. Export it from the cycler software as text (CSV, TXT or MPT) and try again.`);
    const lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
    let vendor = null, start = 0;
    const m = text.slice(0, 4000).match(/nb header lines\s*:\s*(\d+)/i);
    if (m) { vendor = "BioLogic"; start = parseInt(m[1], 10) - 1; }
    else {
      for (let i = 0; i < Math.min(lines.length, 60); i++) {
        const fields = lines[i].split("\t").map((f) => parseHeader(f)[0]);
        if (fields.includes("cyc") || fields.includes("cyclec")) { vendor = "Maccor"; start = i; break; }
      }
    }
    if (vendor === null) {
      const nested = newareNested(lines.filter((ln) => ln.trim()));
      if (nested !== null) return { vendor: "Neware", cycles: nested };
    }
    const body = lines.slice(start).filter((ln) => ln.trim());
    if (body.length < 20) throw new IngestError("That file looks too short. Expected discharge time-series rows for cycles 10 and 100.");
    const [header, rows] = splitTable(body);
    const cols = header.map(parseHeader);
    const ci = find(cols, CYCLE), vi = find(cols, VOLT), ii = find(cols, CURR);
    let qi = find(cols, QDIS);
    const si = find(cols, STATE), ti = find(cols, STEP);
    if (qi === -1 && si !== -1) qi = find(cols, QANY);
    if (ci === -1 || vi === -1 || qi === -1)
      throw new IngestError("Could not find cycle, voltage and discharge-capacity columns. Supported: Arbin, Maccor, Neware and BioLogic text exports, or cycle,voltage_v,discharge_capacity_ah.");
    if (vendor === null) {
      const names = new Set(cols.map(([n]) => n));
      vendor = (names.has("ewe") || names.has("ecell") || names.has("qdischarge")) ? "BioLogic"
        : names.has("cycleindex") ? "Arbin"
        : (names.has("cycleid") || names.has("capacitancedchg") || names.has("dchgcap")) ? "Neware"
        : ii === -1 ? "Hectocycle CSV" : "CSV";
    }
    const vs = SCALE[cols[vi][1]] ?? 1, qs = SCALE[cols[qi][1]] ?? 1, is = ii !== -1 ? (SCALE[cols[ii][1]] ?? 1) : 1;
    const width = Math.max(ci, vi, qi, ii, si, ti);

    const cycles = new Map(), segs = new Segments();
    for (const r of rows) {
      if (r.length <= width) continue;
      let c = num(r[ci]), v = num(r[vi]) * vs, q = num(r[qi]) * qs, cur;
      if (!(Number.isFinite(c) && Number.isFinite(v) && Number.isFinite(q))) continue;
      c = Math.round(c);
      if (si !== -1) {  // Maccor: state flags charge / discharge; capacity restarts every step
        const state = r[si].trim().toUpperCase();
        if (state.startsWith("C")) segs.charge();
        else if (state.startsWith("D")) segs.discharge(c, ti !== -1 ? r[ti].trim() : "", v, q);
        continue;
      } else if (ii !== -1) {
        cur = num(r[ii]) * is;
        if (!Number.isFinite(cur)) continue;
      } else cur = -1;
      if (!cycles.has(c)) cycles.set(c, { I: [], V: [], Q: [] });
      const d = cycles.get(c);
      d.I.push(cur); d.V.push(v); d.Q.push(q);
    }
    return { vendor, cycles: si !== -1 ? segs.cycles() : cycles };
  }

  /* Discharge branch as strictly ascending V with mean Q per repeated V (src/transfer.py). */
  function dischargeQV(d, minPts = 20) {
    const sums = new Map(), counts = new Map();
    let n = 0;
    for (let i = 0; i < d.I.length; i++) {
      if (!(d.I[i] < -DEADBAND_A && d.Q[i] >= 0)) continue;
      n++;
      sums.set(d.V[i], (sums.get(d.V[i]) ?? 0) + d.Q[i]);
      counts.set(d.V[i], (counts.get(d.V[i]) ?? 0) + 1);
    }
    if (n < minPts) return null;
    const v = [...sums.keys()].sort((a, b) => a - b);
    if (v.length < 2) return null;
    return [v, v.map((x) => sums.get(x) / counts.get(x))];
  }

  const nDischarge = (d) => d.I.reduce((s, I, i) => s + (I < -DEADBAND_A && d.Q[i] >= 0 ? 1 : 0), 0);

  function interp(x, xp, fp) {  // numpy.interp for x inside strictly increasing xp
    let lo = 0, hi = xp.length - 1;
    if (x >= xp[hi]) return fp[hi];
    while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (xp[mid] <= x) lo = mid; else hi = mid; }
    return (fp[lo + 1] - fp[lo]) / (xp[lo + 1] - xp[lo]) * (x - xp[lo]) + fp[lo];
  }

  function dqFeatures(a, b, nGrid = 1000) {
    // overlap trimmed 10 mV, clipped to Severson's 2.0-3.5 V Qdlin window (src/transfer.py V_WINDOW)
    const vLo = Math.max(Math.max(a[0][0], b[0][0]) + 0.01, V_WINDOW[0]);
    const vHi = Math.min(Math.min(a[0][a[0].length - 1], b[0][b[0].length - 1]) - 0.01, V_WINDOW[1]);
    if (vHi <= vLo) return null;
    const step = (vHi - vLo) / (nGrid - 1), dq = new Array(nGrid);
    for (let k = 0; k < nGrid; k++) {
      const v = k === nGrid - 1 ? vHi : vLo + k * step;
      dq[k] = interp(v, b[0], b[1]) - interp(v, a[0], a[1]);
    }
    const mean = dq.reduce((s, x) => s + x, 0) / nGrid;
    const variance = dq.reduce((s, x) => s + (x - mean) ** 2, 0) / nGrid;
    return {
      log_var_dq: Math.log10(variance + EPS),
      log_min_dq: Math.log10(Math.abs(Math.min(...dq)) + EPS),
      log_mean_dq: Math.log10(Math.abs(mean) + EPS),
    };
  }

  function nearest(keys, target, tol) {
    let best = null;
    for (const c of [...keys].sort((x, y) => x - y))
      if (Math.abs(c - target) <= tol && (best === null || Math.abs(c - target) < Math.abs(best - target))) best = c;
    return best;
  }

  function featurizeText(text, filename = "") {
    const { vendor, cycles } = readText(text, filename);
    const dis = new Map([...cycles].filter(([, d]) => nDischarge(d) > 0));
    const cE = nearest(dis.keys(), ...EARLY), cL = nearest(dis.keys(), ...LATE);
    if (cE === null || cL === null) {
      const found = [...dis.keys()].sort((x, y) => x - y);
      throw new IngestError(`Need discharge data at cycle ~10 and cycle ~100. Found cycles: ${found.slice(0, 12).join(", ")}${found.length > 12 ? "…" : ""}`);
    }
    for (const c of [cE, cL]) {
      const n = nDischarge(dis.get(c));
      if (n < 20) throw new IngestError(`Cycle ${c} has only ${n} usable points. A full discharge branch is needed.`);
    }
    const a = dischargeQV(dis.get(cE)), b = dischargeQV(dis.get(cL));
    const feats = a && b ? dqFeatures(a, b) : null;
    if (!feats) throw new IngestError("The two cycles' voltage ranges do not overlap. Check that the voltage column is in volts.");
    return { vendor, cycles: [cE, cL], nPoints: [nDischarge(dis.get(cE)), nDischarge(dis.get(cL))], feats };
  }

  /* ---- scoring (exported production model) ---- */

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

  function scoreCell(model, envelope, feats) {
    const x = model.features.map((f) => feats[f]);
    const z = linearScore(model.point, x);
    const xs = model.point.iso_x, ys = model.point.iso_y;
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
    for (const fold of model.cvap) {
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
    const violations = model.features.filter((f) => feats[f] < envelope[f][0] || feats[f] > envelope[f][1]);
    const verdict = violations.length ? "out-of-envelope" : (p0 > 0.5 ? "pass" : p1 < 0.5 ? "fail" : "keep-testing");
    return { p, p0, p1, verdict, violations, feats };
  }

  const api = { IngestError, DQ_FEATURES, parseHeader, readText, featurizeText, pava, linearScore, scoreCell };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HectoCore = api;
})(typeof window !== "undefined" ? window : globalThis);
