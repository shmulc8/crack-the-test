/* Exact ternary-kernel check for a ±1 sign matrix (independent of verify.js).
 *
 *   cc -O2 -o verify verify.c && ./verify matrices/beta_Q29_le_15.txt
 *
 * Counts the nonzero z in {-1,0,1}^n with W z = 0 by meet-in-the-middle:
 * enumerate all 3^nL left half-assignments, sort their packed row-sum
 * signatures, then stream the 3^nR right half-assignments and binary-search
 * for exact cancellation. Zero kernel vectors  =>  the rows of W certify
 * beta(Q_n) <= q (see README.md).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static int q, n, W[16][32];

typedef struct { uint64_t a; uint32_t b; } Sig; /* rows 0-11 in a (5 bits each), rows 12-15 in b */
typedef struct { Sig s; uint32_t idx; } Ent;

static int cmp(const void *x, const void *y) {
  const Ent *p = x, *r = y;
  if (p->s.a != r->s.a) return p->s.a < r->s.a ? -1 : 1;
  if (p->s.b != r->s.b) return p->s.b < r->s.b ? -1 : 1;
  return 0;
}

/* pack row sums (each in [-15,15], offset +15 -> [0,30] < 32) */
static Sig pack(const int *sums) {
  Sig s = {0, 0};
  for (int j = 0; j < q && j < 12; j++) s.a |= (uint64_t)(sums[j] + 15) << (5 * j);
  for (int j = 12; j < q; j++) s.b |= (uint32_t)(sums[j] + 15) << (5 * (j - 12));
  return s;
}

int main(int argc, char **argv) {
  if (argc != 2) { fprintf(stderr, "usage: %s <matrix.txt>\n", argv[0]); return 2; }
  FILE *f = fopen(argv[1], "r");
  if (!f) { perror("open"); return 2; }
  char line[128];
  while (fgets(line, sizeof line, f)) {
    if (line[0] == '#' || line[0] == '\n') continue;
    int len = (int)strcspn(line, "\r\n");
    if (n == 0) n = len;
    if (len != n || q >= 16 || n > 32) { fprintf(stderr, "malformed matrix\n"); return 2; }
    for (int i = 0; i < n; i++) {
      if (line[i] != '+' && line[i] != '-') { fprintf(stderr, "bad char\n"); return 2; }
      W[q][i] = line[i] == '+' ? 1 : -1;
    }
    q++;
  }
  fclose(f);
  int nL = (n + 1) / 2; if (nL > 15) nL = 15;
  int nR = n - nL;
  long sizeL = 1, sizeR = 1;
  for (int i = 0; i < nL; i++) sizeL *= 3;
  for (int i = 0; i < nR; i++) sizeR *= 3;

  Ent *tab = malloc((size_t)sizeL * sizeof(Ent));
  if (!tab) { fprintf(stderr, "oom\n"); return 2; }

  /* left enumeration, incremental odometer starting at z = (-1,...,-1) */
  int sums[16] = {0};
  signed char dg[16] = {0};
  for (int j = 0; j < q; j++) { sums[j] = 0; for (int i = 0; i < nL; i++) sums[j] -= W[j][i]; }
  memset(dg, 0, sizeof dg);
  for (long idx = 0; idx < sizeL; idx++) {
    tab[idx].s = pack(sums); tab[idx].idx = (uint32_t)idx;
    if (idx == sizeL - 1) break;
    int i = 0;
    while (dg[i] == 2) { dg[i] = 0; for (int j = 0; j < q; j++) sums[j] -= 2 * W[j][i]; i++; }
    dg[i]++; for (int j = 0; j < q; j++) sums[j] += W[j][i];
  }
  qsort(tab, (size_t)sizeL, sizeof(Ent), cmp);

  /* right enumeration: need left sums equal to -(right sums) */
  long matches = 0, shown = 0;
  for (int j = 0; j < q; j++) { sums[j] = 0; for (int i = nL; i < n; i++) sums[j] += W[j][i]; } /* = -(sum at z=-1) */
  memset(dg, 0, sizeof dg);
  for (long idx = 0; idx < sizeR; idx++) {
    Sig want = pack(sums);
    long lo = 0, hi = sizeL;
    while (lo < hi) { long m = (lo + hi) / 2; Ent e = tab[m];
      if (e.s.a < want.a || (e.s.a == want.a && e.s.b < want.b)) lo = m + 1; else hi = m; }
    for (long m = lo; m < sizeL && tab[m].s.a == want.a && tab[m].s.b == want.b; m++) {
      matches++;
      long a = tab[m].idx, b = idx;
      int nz = 0; char zs[40];
      for (int i = 0; i < nL; i++) { int v = (int)(a % 3) - 1; a /= 3; zs[i] = "-.+"[v + 1]; nz |= v; }
      for (int i = 0; i < nR; i++) { int v = (int)(b % 3) - 1; b /= 3; zs[nL + i] = "-.+"[v + 1]; nz |= v; }
      zs[n] = 0;
      if (nz && shown++ < 10) printf("  %s\n", zs);
    }
    if (idx == sizeR - 1) break;
    int i = 0;
    while (dg[i] == 2) { dg[i] = 0; for (int j = 0; j < q; j++) sums[j] += 2 * W[j][nL + i]; i++; }
    dg[i]++; for (int j = 0; j < q; j++) sums[j] -= W[j][nL + i];
  }
  free(tab);
  long nulls = matches - 1; /* the z = 0 pairing always matches */
  printf("matrix: %d x %d\n", q, n);
  printf("nonzero ternary kernel vectors: %ld\n", nulls);
  if (nulls == 0) {
    printf("VALID certificate: beta(Q_%d) <= %d  (%d-attempt strategy for a %d-question test)\n", n, q, q + 1, n);
    return 0;
  }
  printf("INVALID: matrix does not resolve the hypercube\n");
  return 1;
}
