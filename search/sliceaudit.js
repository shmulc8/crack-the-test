// Mass slice audit: random q-row, n-col submatrices of the solved 15x29s,
// exact-counted immediately. Zero-null slices are new detecting matrices.
// usage: bun sliceaudit.js <q> <n> <tries> [rngseed]
import { spawnSync } from "bun";
import { readFileSync } from "fs";
const D = import.meta.dir;
const [q, n, tries, seed0] = process.argv.slice(2).map(Number);
const bases = ["best29_a", "sol29_17", "sol29_28", "sol29_58", "sol29_60"];
const mats = bases.map((b) => readFileSync(`${D}/${b}.txt`, "utf8").trim().split("\n").filter((l) => !l.startsWith("#")));
let s = (seed0 || 555) + q * 7919 + n * 104729;
const rnd = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x80000000; };
const pick = (total, keep) => {
  const idx = [...Array(total).keys()];
  for (let i = total - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  return idx.slice(0, keep).sort((a, b) => a - b);
};
let wins = 0, bestNulls = Infinity;
for (let t = 0; t < tries; t++) {
  const rows = mats[t % mats.length];
  const keepR = pick(15, q), keepC = pick(29, n);
  const txt = keepR.map((r) => keepC.map((c) => rows[r][c]).join("")).join("\n") + "\n";
  const tmp = `${D}/audit_tmp_${q}x${n}.txt`;
  await Bun.write(tmp, txt);
  const out = spawnSync([`${D}/sa_q${q}`, "count", tmp, String(n)]).stdout.toString();
  const nulls = parseInt(out.match(/nulls=(\d+)/)?.[1] ?? "-1", 10);
  if (nulls === 0) {
    wins++;
    const dst = `${D}/won_${q}x${n}_audit${t}.txt`;
    await Bun.write(dst, txt);
    console.log(`ZERO at try ${t}: base=${bases[t % 5]} rows=[${keepR}] cols=[${keepC}] -> ${dst}`);
  } else if (nulls > 0 && nulls < bestNulls) { bestNulls = nulls; }
  if ((t + 1) % 500 === 0) console.log(`${t + 1}/${tries}: ${wins} zeros, best nonzero ${bestNulls}`);
}
console.log(`AUDIT ${q}x${n}: ${wins} zero-null slices in ${tries} tries (best nonzero ${bestNulls})`);
