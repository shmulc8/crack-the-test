/* For every 12-set we derive that is NOT in McKay's file, verify from scratch
   that it is NOT dissociated: at least two of its 2^12 subset sums coincide.
   Sums are packed 8 bits per coordinate (max 12, so no carry). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef unsigned __int128 u128;
static unsigned char perm[5040][128];
static int NP = 0;

static void build(void) {
    int idx[7]; for (int i = 0; i < 7; i++) idx[i] = i;
    while (1) {
        for (int t = 0; t < 128; t++) {
            int u = 0;
            for (int j = 0; j < 7; j++) if ((t >> j) & 1) u |= 1 << idx[j];
            perm[NP][t] = (unsigned char)u;
        }
        NP++;
        int i = 5; while (i >= 0 && idx[i] >= idx[i+1]) i--;
        if (i < 0) break;
        int j = 6; while (idx[j] <= idx[i]) j--;
        int tm = idx[i]; idx[i] = idx[j]; idx[j] = tm;
        for (int a = i+1, b = 6; a < b; a++, b--) { tm = idx[a]; idx[a] = idx[b]; idx[b] = tm; }
    }
}
static inline int lex_less(u128 a, u128 b) {
    u128 d = a ^ b; if (!d) return 0;
    u128 lb = d & (~d + 1);
    return (a & lb) != 0;
}
static u128 canon(const unsigned char *s, int k) {
    u128 best = 0; int first = 1;
    for (int p = 0; p < NP; p++) {
        const unsigned char *P = perm[p];
        u128 m = 0;
        for (int i = 0; i < k; i++) m |= (u128)1 << P[s[i]];
        if (first || lex_less(m, best)) { best = m; first = 0; }
    }
    return best;
}
static int cmp_u128(const void *a, const void *b) {
    u128 x = *(const u128*)a, y = *(const u128*)b;
    return x < y ? -1 : (x > y ? 1 : 0);
}
static size_t uniq(u128 *v, size_t n) {
    qsort(v, n, sizeof(u128), cmp_u128);
    size_t w = 0;
    for (size_t i = 0; i < n; i++) if (i == 0 || v[i] != v[i-1]) v[w++] = v[i];
    return w;
}
static int bsearch_u128(const u128 *v, size_t n, u128 key) {
    size_t lo = 0, hi = n;
    while (lo < hi) { size_t m = (lo + hi) / 2; if (v[m] < key) lo = m + 1; else hi = m; }
    return lo < n && v[lo] == key;
}
static int cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t*)a, y = *(const uint64_t*)b;
    return x < y ? -1 : (x > y ? 1 : 0);
}
/* spread a 7-bit type into 7 bytes, one per coordinate */
static uint64_t spread(int t) {
    uint64_t r = 0;
    for (int j = 0; j < 7; j++) if ((t >> j) & 1) r |= (uint64_t)1 << (8 * j);
    return r;
}
static uint64_t sums[4096];
static int dissociated(const unsigned char *d, int k) {
    uint64_t sp[16];
    for (int i = 0; i < k; i++) sp[i] = spread(d[i]);
    int N = 1 << k;
    for (int m = 0; m < N; m++) {
        uint64_t s = 0;
        for (int i = 0; i < k; i++) if ((m >> i) & 1) s += sp[i];
        sums[m] = s;
    }
    qsort(sums, N, sizeof(uint64_t), cmp_u64);
    for (int i = 1; i < N; i++) if (sums[i] == sums[i-1]) return 0;
    return 1;
}
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s <mckay7.txt> <all813.txt>\n", argv[0]); return 2; }
    build();
    FILE *f = fopen(argv[1], "r");
    if (!f) { perror(argv[1]); return 2; }
    size_t nm = 0; u128 *M = malloc(200000 * sizeof(u128));
    if (!M) { fprintf(stderr, "out of memory\n"); fclose(f); return 2; }
    unsigned char s[16]; int v, rc;
    while ((rc = fscanf(f, "%d", &v)) == 1) {
        if (v < 0 || v >= 128) { fprintf(stderr, "invalid McKay type %d\n", v); fclose(f); free(M); return 2; }
        s[0] = (unsigned char)v;
        for (int i = 1; i < 12; i++) {
            if (fscanf(f, "%d", &v) != 1 || v < 0 || v >= 128) {
                fprintf(stderr, "malformed McKay record %zu\n", nm + 1); fclose(f); free(M); return 2;
            }
            s[i] = (unsigned char)v;
        }
        M[nm++] = canon(s, 12);
    }
    if (rc != EOF) { fprintf(stderr, "invalid token in McKay input\n"); fclose(f); free(M); return 2; }
    fclose(f);
    size_t nmu = uniq(M, nm);
    fprintf(stderr, "McKay canonical forms: %zu\n", nmu);

    f = fopen(argv[2], "r");
    if (!f) { perror(argv[2]); free(M); return 2; }
    char line[512];
    size_t nsol = 0, nextra = 0, nseen = 0;
    size_t capx = 400000, nx = 0; u128 *X = malloc(capx * sizeof(u128));
    if (!X) { fprintf(stderr, "out of memory\n"); fclose(f); free(M); return 2; }
    while (fgets(line, sizeof line, f)) {
        if (!strstr(line, "SOLUTION #")) continue;
        char *p = strstr(line, "types"); if (!p) continue;
        p += 5;
        int T[16], k = 0;
        while (k < 16) { int adv; if (sscanf(p, "%d%n", &T[k], &adv) != 1) break; p += adv; k++; }
        if (k != 13) continue;
        for (int i = 0; i < 13; i++) {
            if (T[i] < 0 || T[i] >= 128) { fprintf(stderr, "invalid type in solution %zu\n", nsol + 1); fclose(f); free(M); free(X); return 2; }
        }
        nsol++;
        for (int a = 0; a < 13; a++) {
            unsigned char d[12]; int w = 0;
            for (int b = 0; b < 13; b++) if (b != a) d[w++] = (unsigned char)(T[b] ^ T[a]);
            u128 c = canon(d, 12);
            nseen++;
            if (bsearch_u128(M, nmu, c)) continue;
            if (nx >= capx) {
                capx *= 2;
                u128 *grown = realloc(X, capx * sizeof(u128));
                if (!grown) { fprintf(stderr, "out of memory\n"); fclose(f); free(M); free(X); return 2; }
                X = grown;
            }
            X[nx++] = c;
            nextra++;
        }
    }
    fclose(f);
    size_t nxu = uniq(X, nx);
    size_t ndiss = 0, nnondiss = 0;
    for (size_t i = 0; i < nxu; i++) {
        unsigned char d[12]; int k = 0;
        for (int type = 0; type < 128; type++) {
            if ((X[i] >> type) & 1) {
                if (k >= 12) { fprintf(stderr, "canonical form has more than 12 types\n"); free(M); free(X); return 2; }
                d[k++] = (unsigned char)type;
            }
        }
        if (k != 12) { fprintf(stderr, "canonical form has %d types, expected 12\n", k); free(M); free(X); return 2; }
        if (dissociated(d, 12)) ndiss++; else nnondiss++;
    }
    printf("derived 12-sets            : %zu\n", nseen);
    printf("not in McKay (with mult.)  : %zu\n", nextra);
    printf("  distinct canonical forms : %zu\n", nxu);
    printf("  unexpectedly dissociated : %zu\n", ndiss);
    printf("  verified non-dissociated : %zu\n", nnondiss);
    int pass = nm == 118485 && nmu == 118485 && nsol == 108865 &&
               nseen == 108865u * 13u && nxu == 76601 && ndiss == 0;
    printf(pass ? "PASS: every extra orbit is non-dissociated\n"
                : "FAIL: counts or dissociativity differ from the recorded complete comparison\n");
    free(M); free(X);
    return pass ? 0 : 1;
}
