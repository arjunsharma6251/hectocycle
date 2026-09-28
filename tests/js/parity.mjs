// Browser/Python parity: app/static/core.js must reproduce src/ingest.py's
// features for every cycler fixture and the Python mirror's scores for the
// exported model. Expectations: tests/fixtures/parity.json, written by
// scripts/make_cycler_fixtures.py. Run: node tests/js/parity.mjs
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const core = createRequire(import.meta.url)(join(root, "app", "static", "core.js"));
const exp = JSON.parse(readFileSync(join(root, "tests", "fixtures", "parity.json"), "utf8"));
const bundle = JSON.parse(readFileSync(join(root, "app", "static", "cockpit_data.json"), "utf8"));

let failures = 0;
const check = (name, got, want, tol) => {
  const err = Math.abs(got - want);
  if (!(err <= tol)) { failures++; console.error(`FAIL ${name}: got ${got}, want ${want} (|err| ${err})`); }
};

for (const [file, want] of Object.entries(exp.features)) {
  const path = join(root, "tests", "fixtures", "cyclers", file);
  const text = readFileSync(path, file.endsWith(".mpt") ? "latin1" : "utf8");
  const got = core.featurizeText(text, file).feats;
  for (const k of core.DQ_FEATURES) check(`${file} ${k}`, got[k], want[k], 1e-9);
}

const { model, envelope } = bundle.qual;
exp.scores.forEach((s, i) => {
  const r = core.scoreCell(model, envelope, s.feats);
  check(`score[${i}].p`, r.p, s.p, 1e-6);
  check(`score[${i}].p0`, r.p0, s.p0, 1e-6);
  check(`score[${i}].p1`, r.p1, s.p1, 1e-6);
});

let nReal = 0;
for (const [file, want] of Object.entries(exp.real || {})) {
  const text = readFileSync(join(root, "tests", "fixtures", "real", file), want.encoding === "latin-1" ? "latin1" : "utf8");
  const { vendor, cycles } = core.readText(text, file);
  if (vendor !== want.vendor) { failures++; console.error(`FAIL ${file}: vendor ${vendor} != ${want.vendor}`); }
  const gotKeys = [...cycles.keys()].sort((a, b) => a - b).map(String);
  if (gotKeys.join() !== Object.keys(want.cycles).join()) { failures++; console.error(`FAIL ${file}: cycles ${gotKeys} != ${Object.keys(want.cycles)}`); continue; }
  for (const [c, w] of Object.entries(want.cycles)) {
    const d = cycles.get(+c);
    check(`${file} c${c} n`, d.V.length, w.n, 0);
    check(`${file} c${c} n_dis`, d.I.filter((x) => x < -0.05).length, w.n_dis, 0);
    check(`${file} c${c} q_max`, Math.max(...d.Q), w.q_max, 1e-9);
    check(`${file} c${c} v_sum`, d.V.reduce((s, x) => s + x, 0), w.v_sum, 1e-6);
  }
  nReal++;
}

for (const [text, name, pattern] of [
  ["", "run.ndax", /Export it/],
  ["a,b,c\n" + "1,2,3\n".repeat(30), "x.csv", /Could not find/],
]) {
  try { core.featurizeText(text, name); failures++; console.error(`FAIL: ${name} did not raise`); }
  catch (e) { if (!(e instanceof core.IngestError) || !pattern.test(e.message)) { failures++; console.error(`FAIL: ${name}: ${e.message}`); } }
}

const n = Object.keys(exp.features).length;
if (failures) { console.error(`${failures} parity failure(s)`); process.exit(1); }
console.log(`parity ok: ${n} files x 3 features, ${exp.scores.length} scores x 3, ${nReal} real exports (per-cycle structure), 2 error paths`);
