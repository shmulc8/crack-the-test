// Exact ternary-kernel check for a ±1 sign matrix.
//
//   usage: bun verify.js <matrix.txt>     (node >= 18 works too)
//
// The matrix file holds q rows of n characters from {+,-} (lines starting
// with '#' are ignored). The script counts, exactly, the nonzero vectors
// z in {-1,0,1}^n with W z = 0, by meet-in-the-middle enumeration of the
// 3^(n/2) half-assignments. If the count is 0, the rows of W are a valid
// certificate that beta(Q_n) <= q (see README.md for the one-line lemma).
const file = process.argv[2];
if (!file) { console.error("usage: verify.js <matrix.txt>"); process.exit(2); }
const { readFileSync } = await import("fs");
const lines = readFileSync(file, "utf8").trim().split("\n").filter((l) => !l.startsWith("#"));
const n = lines[0].length;
const q = lines.length;
if (lines.some((l) => l.length !== n || /[^+-]/.test(l))) { console.error("malformed matrix"); process.exit(2); }
if (q > 15 || n > 32) { console.error("checker supports q <= 15, n <= 32"); process.exit(2); }
const W = lines.map((l) => [...l].map((c) => (c === "+" ? 1 : -1)));

// Split columns into left (nL) and right (n - nL); pack each half-assignment's
// q row-sums (offset by nL so digits stay in [0, 2*nL] < 32) into one number
// per 10 rows: 10 base-32 digits fit exactly in a float64 mantissa.
const nL = Math.min(15, Math.ceil(n / 2)), nR = n - nL;
const fq = Math.min(q, 10), aq = q - fq;
const OFF = 15; // digit offset; row sums over <=15 columns fit [-15,15]
const p32 = [...Array(fq)].map((_, j) => Math.pow(32, j));
const a32 = [...Array(aq)].map((_, r) => Math.pow(32, r));
const dKey = new Float64Array(n), dAux = new Float64Array(n);
for (let i = 0; i < n; i++) {
  let k = 0, a = 0;
  for (let j = 0; j < fq; j++) k += W[j][i] * p32[j];
  for (let r = 0; r < aq; r++) a += W[fq + r][i] * a32[r];
  dKey[i] = k; dAux[i] = a;
}
const BITS = n >= 27 ? 25 : 22, SIZE = 1 << BITS, MASK = SIZE - 1;
const tKey = new Float64Array(SIZE).fill(-1), tAux = new Float64Array(SIZE), tIdx = new Uint32Array(SIZE);
const hash = (key) => {
  const lo = key % 33554432, hi = Math.floor(key / 33554432);
  return (Math.imul(lo, 0x9e3779b1) ^ Math.imul(hi, 0x85ebca77)) & MASK;
};
const sizeL = Math.pow(3, nL), sizeR = Math.pow(3, nR);
// left half: insert every z_L with key = packed(OFF + sum_j W_L z_L)
{
  let key = 0, aux = 0; // start at z = (-1,...,-1)
  for (let j = 0; j < fq; j++) { let s = OFF; for (let i = 0; i < nL; i++) s -= W[j][i]; key += s * p32[j]; }
  for (let r = 0; r < aq; r++) { let s = OFF; for (let i = 0; i < nL; i++) s -= W[fq + r][i]; aux += s * a32[r]; }
  const dg = new Int8Array(nL);
  for (let idx = 0; idx < sizeL; idx++) {
    let h = hash(key * 31 + aux);
    while (tKey[h] !== -1) h = (h + 1) & MASK;
    tKey[h] = key; tAux[h] = aux; tIdx[h] = idx;
    if (idx === sizeL - 1) break;
    let i = 0;
    while (dg[i] === 2) { dg[i] = 0; key -= 2 * dKey[i]; aux -= 2 * dAux[i]; i++; }
    dg[i]++; key += dKey[i]; aux += dAux[i];
  }
}
// right half: for every z_R, look up z_L with W_L z_L = -W_R z_R
const nulls = [];
{
  let key = 0, aux = 0;
  for (let j = 0; j < fq; j++) { let s = OFF; for (let i = nL; i < n; i++) s += W[j][i]; key += s * p32[j]; }
  for (let r = 0; r < aq; r++) { let s = OFF; for (let i = nL; i < n; i++) s += W[fq + r][i]; aux += s * a32[r]; }
  const dg = new Int8Array(nR || 1);
  for (let idx = 0; idx < sizeR; idx++) {
    let h = hash(key * 31 + aux);
    while (tKey[h] !== -1) {
      if (tKey[h] === key && tAux[h] === aux) {
        const z = new Int8Array(n);
        let a = tIdx[h];
        for (let i = 0; i < nL; i++) { z[i] = (a % 3) - 1; a = Math.floor(a / 3); }
        let b = idx;
        for (let i = 0; i < nR; i++) { z[nL + i] = (b % 3) - 1; b = Math.floor(b / 3); }
        if (z.some((v) => v !== 0)) nulls.push(z);
      }
      h = (h + 1) & MASK;
    }
    if (idx === sizeR - 1) break;
    let i = 0;
    while (dg[i] === 2) { dg[i] = 0; key += 2 * dKey[nL + i]; aux += 2 * dAux[nL + i]; i++; }
    dg[i]++; key -= dKey[nL + i]; aux -= dAux[nL + i];
  }
}
console.log(`matrix: ${q} x ${n}`);
console.log(`nonzero ternary kernel vectors: ${nulls.length}`);
for (const z of nulls.slice(0, 10)) console.log("  " + [...z].map((v) => "-.+"[v + 1]).join(""));
if (nulls.length === 0) {
  console.log(`VALID certificate: beta(Q_${n}) <= ${q}  (${q + 1}-attempt strategy for a ${n}-question test)`);
} else {
  console.log("INVALID: matrix does not resolve the hypercube");
  process.exit(1);
}
