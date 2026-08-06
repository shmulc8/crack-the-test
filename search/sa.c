// Simulated annealing search for a 15-probe resolving set of Q_n (n=29,30):
// a 15 x n {+1,-1} matrix W with no nonzero z in {-1,0,1}^n s.t. Wz = 0.
// Exact null count per candidate via meet-in-the-middle:
//   rows 0..11 packed 5 bits each into a 60-bit key, rows 12..14 into a 15-bit aux;
//   enumerate 3^15 left / 3^(n-15) right ternary half-vectors, radix-sort keys, merge.
//
// usage: ./sa count <matrixfile> <n>
//        ./sa anneal <n> <seconds> <seedfile|RAND> <rngseed> <outfile>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

#ifndef Q
#define Q 15
#endif
#define KQ (Q < 12 ? Q : 12)   /* rows packed into the 60-bit key */
#define AQ (Q - KQ)            /* rows packed into the aux field  */
static int N, NL = 15, NR;
static long SL, SR;

static int8_t w[Q][32];

static int64_t ekL[32], ekR[32];
static int32_t eaL[32], eaR[32];

static uint64_t *keyEnumL, *keyEnumR, *kL, *kR, *tmpK;
static uint32_t *iL, *iR, *tmpI;
static uint16_t *auxEnumL, *auxEnumR;
static uint32_t *cdL, *cdR;      // ternary codes of bounded-enumerated half-vectors
static long activeL, activeR;    // entries in play per side (== SL/SR when WCAP off)
static int WCAP = 0;             // per-side weight cap; 0 = exact full enumeration

static long ipow3(int e) { long r = 1; while (e--) r *= 3; return r; }

#define MAXNULLS 512
static int8_t nullZ[MAXNULLS][32];
static int nNulls, nullOverflow;
static int staleL, staleR;

static void recordPair(long li, long ri) {
  int8_t z[32]; long a = li, b = ri; int nz = 0;
  for (int i = 0; i < NL; i++) { z[i] = (int8_t)(a % 3) - 1; a /= 3; nz |= z[i]; }
  for (int i = 0; i < NR; i++) { z[NL + i] = (int8_t)(b % 3) - 1; b /= 3; nz |= z[NL + i]; }
  if (!nz) return;
  if (nNulls >= MAXNULLS) { nullOverflow = 1; return; }
  memcpy(nullZ[nNulls++], z, 32);
}

static void computeDeltas(void) {
  for (int i = 0; i < N; i++) {
    int64_t k = 0; int32_t a = 0;
    for (int j = 0; j < KQ; j++) k += (int64_t)w[j][i] << (5 * j);
    for (int r = 0; r < AQ; r++) a += (int32_t)w[KQ + r][i] << (5 * r);
    // left tracks 15+s, right tracks 15-s
    ekL[i] = k;  eaL[i] = a;
    ekR[i] = -k; eaR[i] = -a;
  }
}

static void enumerateSide(int c0, int len, long size, const int64_t *ek, const int32_t *ea,
                          uint64_t *keys, uint16_t *auxs) {
  uint64_t key = 0; int32_t aux = 0;
  for (int j = 0; j < KQ; j++) {
    long f = 15;
    for (int i = c0; i < c0 + len; i++) f -= (ek == ekL ? w[j][i] : -w[j][i]);
    key |= (uint64_t)f << (5 * j);
  }
  for (int r = 0; r < AQ; r++) {
    long f = 15;
    for (int i = c0; i < c0 + len; i++) f -= (ek == ekL ? w[KQ + r][i] : -w[KQ + r][i]);
    aux |= (int32_t)f << (5 * r);
  }
  int8_t dg[16]; memset(dg, 0, sizeof dg);
  for (long idx = 0;; idx++) {
    keys[idx] = key; auxs[idx] = (uint16_t)aux;
    if (idx == size - 1) break;
    int i = 0;
    while (dg[i] == 2) { dg[i] = 0; key -= 2 * (uint64_t)ek[c0 + i]; aux -= 2 * ea[c0 + i]; i++; }
    dg[i]++; key += (uint64_t)ek[c0 + i]; aux += ea[c0 + i];
  }
}

static const uint32_t p3t[16] = {1,3,9,27,81,243,729,2187,6561,19683,59049,
                                 177147,531441,1594323,4782969,14348907};
static long bcnt;
static void enumB(int pos, int len, int c0, int wleft,
                  uint64_t key, int32_t aux, uint32_t code,
                  const int64_t *ek, const int32_t *ea,
                  uint64_t *keys, uint16_t *auxs, uint32_t *codes) {
  if (pos == len) { keys[bcnt] = key; auxs[code] = (uint16_t)aux; codes[bcnt] = code; bcnt++; return; }
  enumB(pos + 1, len, c0, wleft, key, aux, code, ek, ea, keys, auxs, codes);
  if (wleft > 0) {
    enumB(pos + 1, len, c0, wleft - 1, key + (uint64_t)ek[c0 + pos], aux + ea[c0 + pos],
          code + p3t[pos], ek, ea, keys, auxs, codes);
    enumB(pos + 1, len, c0, wleft - 1, key - (uint64_t)ek[c0 + pos], aux - ea[c0 + pos],
          code - p3t[pos], ek, ea, keys, auxs, codes);
  }
}

static void rsort(uint64_t *k, uint32_t *id, long n) {
  if (n <= 2048) { // insertion sort: radix's fixed histogram cost dwarfs tiny inputs
    for (long x = 1; x < n; x++) {
      uint64_t kv = k[x]; uint32_t iv = id[x];
      long y = x - 1;
      while (y >= 0 && k[y] > kv) { k[y + 1] = k[y]; id[y + 1] = id[y]; y--; }
      k[y + 1] = kv; id[y + 1] = iv;
    }
    return;
  }
  static long hist[4096];
  uint64_t *ks = k, *kd = tmpK; uint32_t *is = id, *id2 = tmpI;
  for (int pass = 0; pass < 5; pass++) {
    int sh = pass * 12;
    memset(hist, 0, sizeof hist);
    for (long x = 0; x < n; x++) hist[(ks[x] >> sh) & 4095]++;
    long acc = 0;
    for (int b = 0; b < 4096; b++) { long c = hist[b]; hist[b] = acc; acc += c; }
    for (long x = 0; x < n; x++) {
      long p = hist[(ks[x] >> sh) & 4095]++;
      kd[p] = ks[x]; id2[p] = is[x];
    }
    uint64_t *tk = ks; ks = kd; kd = tk;
    uint32_t *ti = is; is = id2; id2 = ti;
  }
  if (ks != k) { memcpy(k, ks, n * 8); memcpy(id, is, n * 4); }
}

static void buildSide(int left) {
  int len = left ? NL : NR, c0 = left ? 0 : NL;
  uint64_t *keys = left ? keyEnumL : keyEnumR, *k = left ? kL : kR;
  uint16_t *auxs = left ? auxEnumL : auxEnumR;
  uint32_t *codes = left ? cdL : cdR, *id = left ? iL : iR;
  const int64_t *ek = left ? ekL : ekR;
  const int32_t *ea = left ? eaL : eaR;
  long full = left ? SL : SR, act;
  if (WCAP) {
    uint64_t k0 = 0; int32_t a0 = 0; uint32_t code0 = 0;
    for (int j = 0; j < KQ; j++) k0 |= (uint64_t)15 << (5 * j);
    for (int r = 0; r < AQ; r++) a0 |= 15 << (5 * r);
    for (int i = 0; i < len; i++) code0 += p3t[i];
    bcnt = 0;
    enumB(0, len, c0, WCAP, k0, a0, code0, ek, ea, keys, auxs, codes);
    act = bcnt;
    memcpy(k, keys, act * 8);
    memcpy(id, codes, act * 4);
  } else {
    enumerateSide(c0, len, full, ek, ea, keys, auxs);
    memcpy(k, keys, full * 8);
    for (long x = 0; x < full; x++) id[x] = (uint32_t)x;
    act = full;
  }
  rsort(k, id, act);
  if (left) activeL = act; else activeR = act;
}

static long mergeCount(int collect) {
  static uint32_t cnt[32768];
  static int32_t touched[4096];
  long a = 0, b = 0, total = 0;
  if (collect) { nNulls = 0; nullOverflow = 0; }
  while (a < activeL && b < activeR) {
    if (kL[a] < kR[b]) a++;
    else if (kL[a] > kR[b]) b++;
    else {
      uint64_t v = kL[a];
      long a2 = a; while (a2 < activeL && kL[a2] == v) a2++;
      long b2 = b; while (b2 < activeR && kR[b2] == v) b2++;
      long nt = 0;
      for (long x = a; x < a2; x++) {
        uint16_t av = auxEnumL[iL[x]];
        if (cnt[av]++ == 0 && nt < 4096) touched[nt++] = av;
      }
      if (nt >= 4096) { // fallback: clear all (rare)
        for (long y = b; y < b2; y++) total += cnt[auxEnumR[iR[y]]];
        memset(cnt, 0, sizeof cnt);
      } else {
        for (long y = b; y < b2; y++) total += cnt[auxEnumR[iR[y]]];
        for (long t = 0; t < nt; t++) cnt[touched[t]] = 0;
      }
      if (collect) {
        if ((a2 - a) * (b2 - b) <= 4000000) {
          for (long x = a; x < a2; x++)
            for (long y = b; y < b2; y++)
              if (auxEnumL[iL[x]] == auxEnumR[iR[y]]) recordPair(iL[x], iR[y]);
        } else nullOverflow = 1;
      }
      a = a2; b = b2;
    }
  }
  return total - 1; // z = 0
}

static long evalAll(int rebuildL, int rebuildR) {
  computeDeltas();
  if (rebuildL) buildSide(1);
  if (rebuildR) buildSide(0);
  return mergeCount(0);
}

static long evalFresh(int collect) { // rebuild whatever is stale, then merge
  computeDeltas();
  if (staleL) { buildSide(1); staleL = 0; }
  if (staleR) { buildSide(0); staleR = 0; }
  return mergeCount(collect);
}

static void dumpMatrix(const char *path, long nulls, long evals) {
  FILE *f = fopen(path, "w");
  fprintf(f, "# n=%d nulls=%ld evals=%ld\n", N, nulls, evals);
  for (int j = 0; j < Q; j++) {
    for (int i = 0; i < N; i++) fputc(w[j][i] > 0 ? '+' : '-', f);
    fputc('\n', f);
  }
  fclose(f);
}

// With WCAP on, a zero from the bounded counter is only a CLAIM: certify it
// with the exact counter. Returns 0 only if genuinely null-free; otherwise the
// exact count (and leaves nullZ holding the real nulls, WCAP restored).
static long certifyZero(long cur) {
  if (!(WCAP && cur == 0)) return cur;
  int sv = WCAP;
  WCAP = 0; staleL = staleR = 1;
  long f = evalFresh(1);
  printf("certify: bounded 0 -> full %ld\n", f); fflush(stdout);
  if (f == 0) return 0;
  WCAP = sv; staleL = staleR = 1;
  return f;
}

// count ternary preimages of target v (entries in {-2..2}), early exit past limit
static long preimages(const int8_t *v, long limit) {
  int64_t dk = 0; int32_t da = 0;
  for (int j = 0; j < KQ; j++) dk += (int64_t)v[j] << (5 * j);
  for (int r = 0; r < AQ; r++) da += (int32_t)v[KQ + r] << (5 * r);
  static uint32_t cnt[32768];
  static int32_t touched[4096];
  long a = 0, b = 0, matches = 0;
  while (a < activeL && b < activeR) {
    uint64_t rb = kR[b] + (uint64_t)dk;
    if (kL[a] < rb) a++;
    else if (kL[a] > rb) b++;
    else {
      uint64_t va = kL[a], vr = kR[b];
      long a2 = a; while (a2 < activeL && kL[a2] == va) a2++;
      long b2 = b; while (b2 < activeR && kR[b2] == vr) b2++;
      long nt = 0;
      for (long x = a; x < a2; x++) {
        uint16_t av = auxEnumL[iL[x]];
        if (cnt[av]++ == 0 && nt < 4096) touched[nt++] = av;
      }
      for (long y = b; y < b2; y++) matches += cnt[(uint16_t)(auxEnumR[iR[y]] + da)];
      if (nt >= 4096) memset(cnt, 0, sizeof cnt);
      else for (long t = 0; t < nt; t++) cnt[touched[t]] = 0;
      if (matches > limit) return matches;
      a = a2; b = b2;
    }
  }
  return matches;
}

static uint64_t rng_s;
static uint64_t rnd(void) {
  rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17;
  return rng_s;
}
static double rndU(void) { return (double)(rnd() >> 11) / 9007199254740992.0; }

static int loadMatrix(const char *path) {
  FILE *f = fopen(path, "r");
  if (!f) return 0;
  char line[128];
  int j = 0;
  while (j < Q && fgets(line, sizeof line, f)) {
    if (line[0] == '#') continue;
    if ((int)strlen(line) < N) continue;
    for (int i = 0; i < N; i++) w[j][i] = line[i] == '+' ? 1 : -1;
    j++;
  }
  fclose(f);
  return j == Q;
}

int main(int argc, char **argv) {
  if (argc < 2) { fprintf(stderr, "usage\n"); return 1; }
  const char *mode = argv[1];
  int isCount = mode[0] == 'c' && mode[1] == 'o';
  N = atoi(isCount ? argv[3] : argv[2]);
  NL = (N + 1) / 2;
  if (NL > 15) NL = 15;
  NR = N - NL;
  SL = ipow3(NL); SR = ipow3(NR);
  if (!strcmp(mode, "pair")) {
    // preimages() adds a delta (dk/da) of up to +-2 per row (sum/diff targets
    // have entries in {-2,0,2}) onto the RIGHT side's packed 5-bit-per-row
    // fields (rb = kR[b] + dk). Each field holds 15+-s for s in [-side,side],
    // so it must stay within [2,29] (i.e. side <= 13) to absorb a +-2 delta
    // without carrying into/borrowing from the neighboring row's field. The
    // LEFT side never receives a delta, so it only needs [0,31], i.e. <= 15.
    NR = N / 2 < 13 ? N / 2 : 13;
    NL = N - NR;
    if (NL > 15) { NL = 15; NR = N - NL; }
  }
  NR = N - NL;
  SL = ipow3(NL); SR = ipow3(NR);
  long SM = SL > SR ? SL : SR;
  keyEnumL = malloc(SL * 8); keyEnumR = malloc(SR * 8);
  kL = malloc(SL * 8); kR = malloc(SR * 8);
  iL = malloc(SL * 4); iR = malloc(SR * 4);
  tmpK = malloc(SM * 8); tmpI = malloc(SM * 4);
  auxEnumL = malloc(SL * 2); auxEnumR = malloc(SR * 2);
  cdL = malloc(SL * 4); cdR = malloc(SR * 4);

  if (isCount) { // count <file> <n> [wcap]
    if (argc > 4) WCAP = atoi(argv[4]);
    if (!loadMatrix(argv[2])) { fprintf(stderr, "bad matrix\n"); return 1; }
    printf("nulls=%ld%s\n", evalAll(1, 1), WCAP ? " (weight-capped)" : "");
    return 0;
  }

  if (mode[0] == 'e') { // extend <n> <matrixfile> <candStart> <candEnd> [threshold]
    // find +-1 columns c with NO ternary preimage under the loaded matrix:
    // appending such a column keeps the null count at zero. threshold 0 = stop
    // merging a candidate at its first preimage (ZERO-only hunting, fastest).
    if (!loadMatrix(argv[3])) { fprintf(stderr, "bad matrix\n"); return 1; }
    long cs = atol(argv[4]), ce = atol(argv[5]);
    long thr = argc > 6 ? atol(argv[6]) : 4;
    computeDeltas(); buildSide(1); buildSide(0);
    static uint32_t cnt[32768];
    static int32_t touched[4096];
    for (long cand = cs; cand < ce; cand++) {
      int64_t dk = 0; int32_t da = 0;
      for (int j = 0; j < KQ; j++) dk += (((cand >> j) & 1) ? 1 : -1) * ((int64_t)1 << (5 * j));
      for (int r = 0; r < AQ; r++) da += (((cand >> (KQ + r)) & 1) ? 1 : -1) * (1 << (5 * r));
      long a = 0, b = 0, matches = 0;
      while (a < activeL && b < activeR) {
        uint64_t rb = kR[b] + (uint64_t)dk;
        if (kL[a] < rb) a++;
        else if (kL[a] > rb) b++;
        else {
          uint64_t v = kL[a], vr = kR[b];
          long a2 = a; while (a2 < activeL && kL[a2] == v) a2++;
          long b2 = b; while (b2 < activeR && kR[b2] == vr) b2++;
          long nt = 0;
          for (long x = a; x < a2; x++) {
            uint16_t av = auxEnumL[iL[x]];
            if (cnt[av]++ == 0 && nt < 4096) touched[nt++] = av;
          }
          for (long y = b; y < b2; y++) matches += cnt[(uint16_t)(auxEnumR[iR[y]] + da)];
          if (nt >= 4096) memset(cnt, 0, sizeof cnt);
          else for (long t = 0; t < nt; t++) cnt[touched[t]] = 0;
          if (matches > thr) break;
          a = a2; b = b2;
        }
      }
      if (matches <= thr) {
        printf("%s cand=%ld count=%ld col=", matches ? "LOW" : "ZERO", cand, matches);
        for (int j = 0; j < Q; j++) putchar(((cand >> j) & 1) ? '+' : '-');
        putchar('\n'); fflush(stdout);
      }
    }
    printf("range %ld..%ld done\n", cs, ce);
    return 0;
  }

  if (!strcmp(mode, "circ")) { // circ <n> <g1start> <g1end> — exhaustive circulant family
    // W = [C(g1) | C(g2)]: two circulant blocks over Z_Q, columns are the Q
    // rotations of each generator. Symmetries modded out: joint rotation
    // (canonicalize g1 over rotations and negation-rotations), per-orbit
    // negation (g2 <= ~g2), orbit swap handled by scanning all g2 per g1.
    // Cascade: weight-cap 2 -> 6 -> exact; survivors of each stage escalate.
    if (N != 2 * Q) { fprintf(stderr, "circ needs n == 2*Q\n"); return 1; }
    long g1s = atol(argv[3]), g1e = atol(argv[4]);
    long stride = argc > 5 ? atol(argv[5]) : 1;
    const long M = 1L << Q, MASK15 = M - 1;
    long tried = 0, s2 = 0, s3 = 0, found = 0;
    for (long g1 = g1s; g1 < g1e; g1 += stride) {
      int canon = 1;
      for (int k = 0; k < Q && canon; k++) {
        long r = ((g1 >> k) | (g1 << (Q - k))) & MASK15;
        if (r < g1 || (~r & MASK15) < g1) canon = 0;
        if (k == 0 && (~g1 & MASK15) < g1) canon = 0;
      }
      if (!canon) continue;
      // block C(g1) = columns 0..Q-1 = the entire left MITM side, so per stage
      // the left side is built ONCE per g1 and only the right side varies with g2.
      for (int j = 0; j < Q; j++)
        for (int k = 0; k < Q; k++)
          w[j][k] = ((g1 >> ((j + k) % Q)) & 1) ? 1 : -1;
      static long surv2[1 << 15], surv6[1 << 15];
      long ns2 = 0, ns6 = 0;
      int caps[3] = {2, 6, 0};
      for (int st = 0; st < 3; st++) {
        WCAP = caps[st];
        long nin = st == 0 ? 0 : (st == 1 ? ns2 : ns6);
        long *in = st == 1 ? surv2 : surv6;
        computeDeltas(); buildSide(1);
        for (long x = 0; st == 0 ? x < M : x < nin; x++) {
          long g2 = st == 0 ? x : in[x];
          if (st == 0 && (~g2 & MASK15) < g2) continue;
          for (int j = 0; j < Q; j++)
            for (int k = 0; k < Q; k++)
              w[j][Q + k] = ((g2 >> ((j + k) % Q)) & 1) ? 1 : -1;
          computeDeltas(); buildSide(0);
          if (mergeCount(0) > 0) continue;
          if (st == 0) { surv2[ns2++] = g2; tried = tried; }
          else if (st == 1) surv6[ns6++] = g2;
          else {
            found++;
            printf("CIRC FOUND g1=%ld g2=%ld\n", g1, g2); fflush(stdout);
            char path[64]; snprintf(path, sizeof path, "circ_%ld_%ld.txt", g1, g2);
            dumpMatrix(path, 0, tried);
          }
        }
        if (st == 0) tried += M / 2;
      }
      s2 += ns2; s3 += ns6;
      printf("g1=%ld done tried=%ld pass2=%ld pass6=%ld found=%ld\n", g1, tried, s2, s3, found);
      fflush(stdout);
    }
    printf("CIRC DONE range %ld..%ld tried=%ld pass2=%ld pass6=%ld found=%ld\n",
           g1s, g1e, tried, s2, s3, found);
    return found ? 0 : 2;
  }

  if (!strcmp(mode, "pair")) { // pair <n> <matrixfile>  — two-column extension
    // phase 1: all +-1 columns with zero ternary preimage under the loaded matrix;
    // phase 2: pairs (c1,c2) where c1+c2 and c1-c2 also have no preimage.
    // [W | c1 | c2] is then a detecting matrix on n+2 columns.
    if (!loadMatrix(argv[3])) { fprintf(stderr, "bad matrix\n"); return 1; }
    computeDeltas(); buildSide(1); buildSide(0);
    enum { MAXZ = 4096 };
    static int8_t zc[MAXZ][16]; int nz = 0;
    for (long cand = 0; cand < (1L << Q) && nz < MAXZ; cand++) {
      int8_t v[16];
      for (int j = 0; j < Q; j++) v[j] = ((cand >> j) & 1) ? 1 : -1;
      if (preimages(v, 0) == 0) { memcpy(zc[nz++], v, Q); }
    }
    printf("zero-preimage columns: %d\n", nz); fflush(stdout);
    long pairs = 0;
    for (int i = 0; i < nz; i++)
      for (int j = i + 1; j < nz; j++) {
        int8_t sum[16], dif[16];
        for (int r = 0; r < Q; r++) { sum[r] = zc[i][r] + zc[j][r]; dif[r] = zc[i][r] - zc[j][r]; }
        if (preimages(sum, 0) == 0 && preimages(dif, 0) == 0) {
          pairs++;
          printf("PAIR i=%d j=%d c1=", i, j);
          for (int r = 0; r < Q; r++) putchar(zc[i][r] > 0 ? '+' : '-');
          printf(" c2=");
          for (int r = 0; r < Q; r++) putchar(zc[j][r] > 0 ? '+' : '-');
          putchar('\n'); fflush(stdout);
        }
      }
    printf("pair scan done: %d zero-cols, %ld valid pairs\n", nz, pairs);
    return pairs > 0 ? 0 : 2;
  }

  if (mode[0] == 'p') { // polish <n> <seconds> <matrixfile> <rngseed> <outfile> [wcap]
    int seconds = atoi(argv[3]);
    rng_s = strtoull(argv[5], NULL, 10) * 2654435761u + 1;
    const char *outfile = argv[6];
    if (argc > 7) WCAP = atoi(argv[7]);
    if (!loadMatrix(argv[4])) { fprintf(stderr, "bad seed\n"); return 1; }
    time_t t0 = time(NULL);
    staleL = staleR = 1;
    long cur = certifyZero(evalFresh(1));
    long best = cur, evals = 1;
    int8_t bw[Q][32]; memcpy(bw, w, sizeof w);
    uint32_t bestSup = 0;
    for (int t = 0; t < nNulls; t++)
      for (int i = 0; i < N; i++) if (nullZ[t][i]) bestSup |= 1u << i;
    printf("polish start nulls=%ld (listed %d%s)\n", cur, nNulls, nullOverflow ? "+" : "");
    fflush(stdout);
    dumpMatrix(outfile, best, 0);
    while (time(NULL) - t0 < seconds && best > 0) {
      uint32_t sup = 0;
      for (int t = 0; t < nNulls; t++)
        for (int i = 0; i < N; i++) if (nullZ[t][i]) sup |= 1u << i;
      if (nullOverflow || sup == 0) sup = (uint32_t)((1ull << N) - 1);
      long bestD = 0; int bj = -1, bi = -1;
      for (int i = 0; i < N && time(NULL) - t0 < seconds; i++) {
        if (!(sup & (1u << i))) continue;
        for (int j = 0; j < Q; j++) {
          w[j][i] = -w[j][i];
          if (i < NL) staleL = 1; else staleR = 1;
          long nn = evalFresh(0); evals++;
          if (nn - cur < bestD) { bestD = nn - cur; bj = j; bi = i; }
          w[j][i] = -w[j][i];
          if (i < NL) staleL = 1; else staleR = 1;
        }
      }
      if (bj >= 0) {
        w[bj][bi] = -w[bj][bi];
        if (bi < NL) staleL = 1; else staleR = 1;
        cur = certifyZero(evalFresh(1)); evals++;
        printf("t=%lds descend flip(%d,%d) -> nulls=%ld (evals=%ld)\n",
               time(NULL) - t0, bj, bi, cur, evals);
        fflush(stdout);
        if (cur < best) {
          best = cur; memcpy(bw, w, sizeof w);
          bestSup = 0;
          for (int t = 0; t < nNulls; t++)
            for (int i = 0; i < N; i++) if (nullZ[t][i]) bestSup |= 1u << i;
          dumpMatrix(outfile, best, evals);
          printf("t=%lds NEW BEST %ld\n", time(NULL) - t0, best);
          fflush(stdout);
        }
      } else { // local minimum: kick from global best on its null-support columns
        memcpy(w, bw, sizeof w);
        uint32_t ks = bestSup ? bestSup : (uint32_t)((1ull << N) - 1);
        int nk = 2 + (int)(rnd() % 4);
        for (int k = 0; k < nk; k++) {
          int i; do { i = (int)(rnd() % N); } while (!(ks & (1u << i)));
          int j = (int)(rnd() % Q);
          w[j][i] = -w[j][i];
        }
        staleL = staleR = 1;
        cur = certifyZero(evalFresh(1)); evals++;
        printf("t=%lds kick(%d) -> nulls=%ld\n", time(NULL) - t0, nk, cur);
        fflush(stdout);
      }
    }
    printf("FINAL polish n=%d best=%ld evals=%ld\n", N, best, evals);
    memcpy(w, bw, sizeof w);
    dumpMatrix(outfile, best, evals);
    return best == 0 ? 0 : 2;
  }

  // anneal <n> <seconds> <seedfile|RAND> <rngseed> <outfile> [wcap]
  int seconds = atoi(argv[3]);
  rng_s = strtoull(argv[5], NULL, 10) * 2654435761u + 1;
  const char *outfile = argv[6];
  if (argc > 7) WCAP = atoi(argv[7]);
  if (strcmp(argv[4], "RAND") == 0) {
    for (int j = 0; j < Q; j++) for (int i = 0; i < N; i++) w[j][i] = (rnd() & 1) ? 1 : -1;
  } else if (!loadMatrix(argv[4])) { fprintf(stderr, "bad seed\n"); return 1; }

  time_t t0 = time(NULL);
  long cur = evalAll(1, 1);
  long best = cur, evals = 1, sinceBest = 0;
  int8_t bw[Q][32]; memcpy(bw, w, sizeof w);
  double T = 3.0;
  printf("start nulls=%ld\n", cur); fflush(stdout);
  dumpMatrix(outfile, best, 0);

  while (time(NULL) - t0 < seconds && best > 0) {
    int j = (int)(rnd() % Q);
    int i = (int)(rnd() % N);
    int colMove = rndU() < 0.05;
    int8_t save[Q];
    for (int r = 0; r < Q; r++) save[r] = w[r][i];
    if (colMove) { for (int r = 0; r < Q; r++) w[r][i] = (rnd() & 1) ? 1 : -1; }
    else w[j][i] = -w[j][i];

    long nn = evalAll(i < NL, i >= NL);
    evals++;
    long dE = nn - cur;
    if (dE <= 0 || rndU() < exp(-(double)dE / T)) {
      cur = nn;
      if (WCAP && cur == 0) {
        cur = certifyZero(cur);
        if (cur == 0) { best = 0; memcpy(bw, w, sizeof w); dumpMatrix(outfile, 0, evals); break; }
        // false zero: nudge one entry on a real null's support, keep going
        if (nNulls > 0) {
          int t = (int)(rnd() % nNulls);
          int ii; do { ii = (int)(rnd() % N); } while (!nullZ[t][ii]);
          int jj = (int)(rnd() % Q);
          w[jj][ii] = -w[jj][ii];
        }
        cur = evalAll(1, 1); evals++;
        sinceBest++;
        continue;
      }
      if (cur < best) {
        best = cur; sinceBest = 0;
        memcpy(bw, w, sizeof w);
        dumpMatrix(outfile, best, evals);
        printf("t=%lds evals=%ld best=%ld T=%.2f\n", time(NULL) - t0, evals, best, T);
        fflush(stdout);
      } else sinceBest++;
    } else {
      for (int r = 0; r < Q; r++) w[r][i] = save[r];
      computeDeltas();
      if (i < NL) buildSide(1); else buildSide(0);
      sinceBest++;
    }
    T = fmax(0.4, T * 0.9995);
    if (sinceBest > 1500) { // reheat from best
      memcpy(w, bw, sizeof w);
      cur = evalAll(1, 1); evals++;
      T = 2.5; sinceBest = 0;
      printf("t=%lds reheat, back to best=%ld\n", time(NULL) - t0, best); fflush(stdout);
    }
  }
  printf("FINAL n=%d best=%ld evals=%ld elapsed=%lds\n", N, best, evals, time(NULL) - t0);
  memcpy(w, bw, sizeof w);
  dumpMatrix(outfile, best, evals);
  return best == 0 ? 0 : 2;
}
