// List the surviving null vectors of a +-1 probe matrix (usage: bun survivors.js <file> <n>)
const [file, nArg] = process.argv.slice(2);
const n = parseInt(nArg, 10);
const lines = (await Bun.file(file).text()).trim().split("\n").filter((l) => !l.startsWith("#"));
const W = lines.map((l) => [...l.slice(0, n)].map((c) => (c === "+" ? 1 : -1)));
const q = W.length;
const nL = 15, nR = n - nL;
const fq = 10, aq = q - fq;
const p32 = [...Array(fq)].map((_, j) => Math.pow(32, j));
const a32 = [...Array(aq)].map((_, r) => Math.pow(32, r));
const dKey = new Float64Array(n), dAux = new Float64Array(n);
for (let i = 0; i < n; i++) {
  let k = 0, a = 0;
  for (let j = 0; j < fq; j++) k += W[j][i] * p32[j];
  for (let r = 0; r < aq; r++) a += W[fq + r][i] * a32[r];
  dKey[i] = k; dAux[i] = a;
}
const BITS = 25, SIZE = 1 << BITS, MASK = SIZE - 1;
const tKey = new Float64Array(SIZE).fill(-1);
const tAux = new Float64Array(SIZE);
const tIdx = new Uint32Array(SIZE);
const hash = (key) => {
  const lo = key % 33554432, hi = Math.floor(key / 33554432);
  return (Math.imul(lo, 0x9e3779b1) ^ Math.imul(hi, 0x85ebca77)) & MASK;
};
const sizeL = Math.pow(3, nL), sizeR = Math.pow(3, nR);
{
  let key = 0, aux = 0;
  for (let j = 0; j < fq; j++) { let s = 15; for (let i = 0; i < nL; i++) s -= W[j][i]; key += s * p32[j]; }
  for (let r = 0; r < aq; r++) { let s = 15; for (let i = 0; i < nL; i++) s -= W[fq + r][i]; aux += s * a32[r]; }
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
const nulls = [];
{
  let key = 0, aux = 0;
  for (let j = 0; j < fq; j++) { let s = 15; for (let i = nL; i < n; i++) s += W[j][i]; key += s * p32[j]; }
  for (let r = 0; r < aq; r++) { let s = 15; for (let i = nL; i < n; i++) s += W[fq + r][i]; aux += s * a32[r]; }
  const dg = new Int8Array(nR);
  for (let idx = 0; idx < sizeR; idx++) {
    let h = hash(key * 31 + aux);
    while (tKey[h] !== -1) {
      if (tKey[h] === key && tAux[h] === aux) {
        const z = new Int8Array(n);
        let a = tIdx[h];
        for (let i = 0; i < nL; i++) { z[i] = (a % 3) - 1; a = Math.floor(a / 3); }
        let b = idx;
        for (let i = 0; i < nR; i++) { z[nL + i] = (b % 3) - 1; b = Math.floor(b / 3); }
        if (z.some((v) => v !== 0)) nulls.push([...z]);
      }
      h = (h + 1) & MASK;
    }
    if (idx === sizeR - 1) break;
    let i = 0;
    while (dg[i] === 2) { dg[i] = 0; key += 2 * dKey[nL + i]; aux += 2 * dAux[nL + i]; i++; }
    dg[i]++; key -= dKey[nL + i]; aux -= dAux[nL + i];
  }
}
console.log(`nulls: ${nulls.length}`);
const support = new Set();
for (const z of nulls) {
  console.log(z.map((v) => (v === 1 ? "+" : v === -1 ? "-" : ".")).join(""));
  z.forEach((v, i) => { if (v !== 0) support.add(i); });
}
console.log("support columns (0-based):", [...support].sort((a, b) => a - b).join(","));
