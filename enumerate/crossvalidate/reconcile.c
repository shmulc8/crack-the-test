/* Reconcile our canonical 8x13 detecting matrices against McKay's dissociated 12-sets.
   Both sides are canonicalised under the SAME group: permutations of the 7 bit
   positions. A set is a 128-bit map; sorted-sequence lex order on sets equals
   "the set owning the lowest differing bit is smaller". */
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
static inline int lex_less(u128 a, u128 b) {       /* sorted-sequence lex order */
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
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: %s <mckay7.txt> <all813.txt>\n", argv[0]); return 2; }
    build();
    fprintf(stderr, "permutations: %d\n", NP);

    /* McKay side */
    FILE *f = fopen(argv[1], "r");
    if (!f) { perror(argv[1]); return 2; }
    size_t cap = 200000, nm = 0; u128 *M = malloc(cap * sizeof(u128));
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
    printf("McKay   : %zu sets -> %zu distinct canonical forms\n", nm, nmu);

    /* our side: each 13-set T yields 13 candidate 12-sets (XOR by a member, drop 0) */
    f = fopen(argv[2], "r");
    if (!f) { perror(argv[2]); free(M); return 2; }
    size_t cap2 = 4000000, no = 0; u128 *O = malloc(cap2 * sizeof(u128));
    if (!O) { fprintf(stderr, "out of memory\n"); fclose(f); free(M); return 2; }
    char line[512]; size_t nsol = 0;
    while (fgets(line, sizeof line, f)) {
        if (!strstr(line, "SOLUTION #")) continue;
        char *p = strstr(line, "types");
        if (!p) continue;
        p += 5;
        int T[16], k = 0;
        while (k < 16 && sscanf(p, "%d", &T[k]) == 1) {
            while (*p == ' ') p++;
            while (*p && *p != ' ') p++;
            k++;
            if (*p != ' ' && *p != '\0' && *p != '\n') break;
            if (*p == '\0' || *p == '\n') break;
        }
        if (k != 13) continue;
        for (int i = 0; i < 13; i++) {
            if (T[i] < 0 || T[i] >= 128) { fprintf(stderr, "invalid type in solution %zu\n", nsol + 1); fclose(f); free(M); free(O); return 2; }
        }
        nsol++;
        for (int a = 0; a < 13; a++) {
            unsigned char d[12]; int w = 0;
            for (int b = 0; b < 13; b++) if (b != a) d[w++] = (unsigned char)(T[b] ^ T[a]);
            if (no >= cap2) {
                cap2 *= 2;
                u128 *grown = realloc(O, cap2 * sizeof(u128));
                if (!grown) { fprintf(stderr, "out of memory\n"); fclose(f); free(M); free(O); return 2; }
                O = grown;
            }
            O[no++] = canon(d, 12);
        }
    }
    fclose(f);
    size_t nou = uniq(O, no);
    printf("ours    : %zu solutions -> %zu derived 12-sets -> %zu distinct canonical forms\n", nsol, no, nou);

    /* set comparison */
    size_t i = 0, j = 0, both = 0, onlyM = 0, onlyO = 0;
    while (i < nmu && j < nou) {
        if (M[i] == O[j]) { both++; i++; j++; }
        else if (M[i] < O[j]) { onlyM++; i++; }
        else { onlyO++; j++; }
    }
    onlyM += nmu - i; onlyO += nou - j;
    printf("in both : %zu\nMcKay only: %zu\nours only : %zu\n", both, onlyM, onlyO);
    int pass = nm == 118485 && nmu == 118485 && nsol == 108865 &&
               nou == 195086 && both == 118485 && onlyM == 0 && onlyO == 76601;
    printf(pass ? "\nCOVERAGE PASS: all McKay orbits occur; the expected 76601 weaker detecting-set orbits remain\n"
                : "\nCOVERAGE FAIL: counts differ from the recorded complete comparison\n");
    free(M); free(O);
    return pass ? 0 : 1;
}
