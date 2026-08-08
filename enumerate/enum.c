/* Exhaustive enumeration of detecting matrices — canonical + monotone-candidate.
 *
 * Columns are 2^(q-1) normalized types; "detecting" is equivalent to all 2^n
 * subset sums being distinct. Lex-min canonical pruning removes symmetric
 * prefixes under row permutations and row sign flips.
 *
 * What this version adds:
 *
 *  1. Monotone live-candidate lists.  If a type cannot be added to a set it can
 *     never be added to a superset (the sum set only grows, so a collision
 *     never disappears).  Each node therefore filters its parent's live list
 *     once and hands the surviving suffix to each child, instead of rescanning
 *     all types.
 *  2. Lookahead pruning.  If fewer live candidates remain than columns still
 *     needed, the subtree is dead — cut it at once rather than discovering it
 *     one level at a time.
 *  3. Popcount lower bound before the canonicity test.  Permutations preserve
 *     popcount and the least type index of popcount w is (1<<w)-1, so a sorted
 *     vector of those bounds is a lex lower bound on any permuted image; if it
 *     already exceeds the current set, all (q-1)! permutations can be skipped.
 *
 * usage: enum3 q n [--split N --part B] [--maxsol K] [--report SEC]
 *                  [--splitdepth D] [--canondepth D]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <errno.h>
#include <limits.h>
#include <math.h>

#define MAXQ 8
#define MAXN 20
#define LOGTAB 17
#define TABSIZE (1u << LOGTAB)
#define BIAS 64

static int q, n, NT;
static int64_t delta[256];
static int maxsol = 3, canon_depth = 8, split_depth = 5;
static double report_every = 60.0;
static int nsplit = 1, part = 0;
static long long split_counter = 0;

static uint64_t *sums;
static uint64_t *tab[MAXN + 2];
static uint32_t *stamp[MAXN + 2];
static uint32_t gen[MAXN + 2];
static int cand[MAXN + 2][256];
static int live[MAXN + 2][256];

static long long nodes[MAXN + 2], canon_calls = 0, canon_skips = 0;
static int nsol = 0, sol[MAXN + 2];
static struct timespec t_start, t_last;

static int NPERM;
static unsigned char *permtab;

static int parse_int_arg(const char *name, const char *text, int *out) {
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 10);
    if (errno || end == text || *end != '\0' || value < INT_MIN || value > INT_MAX) {
        fprintf(stderr, "invalid %s: %s\n", name, text);
        return 0;
    }
    *out = (int)value;
    return 1;
}

static int parse_double_arg(const char *name, const char *text, double *out) {
    char *end = NULL;
    errno = 0;
    double value = strtod(text, &end);
    if (errno || end == text || *end != '\0' || !isfinite(value)) {
        fprintf(stderr, "invalid %s: %s\n", name, text);
        return 0;
    }
    *out = value;
    return 1;
}

static inline uint32_t hash_slot(uint64_t x) {
    return (uint32_t)((x * 0x9E3779B97F4A7C15ULL) >> (64 - LOGTAB));
}
static inline void tab_insert(int d, uint64_t key) {
    uint32_t s = hash_slot(key);
    while (stamp[d][s] == gen[d] && tab[d][s] != key) s = (s + 1) & (TABSIZE - 1);
    tab[d][s] = key; stamp[d][s] = gen[d];
}
static inline int tab_has(int d, uint64_t key) {
    uint32_t s = hash_slot(key);
    while (stamp[d][s] == gen[d]) {
        if (tab[d][s] == key) return 1;
        s = (s + 1) & (TABSIZE - 1);
    }
    return 0;
}
static double elapsed(struct timespec *from) {
    struct timespec now; clock_gettime(CLOCK_MONOTONIC, &now);
    return (now.tv_sec - from->tv_sec) + (now.tv_nsec - from->tv_nsec) / 1e9;
}

static void build_perms(void) {
    int f = 1, k = q - 1;
    for (int i = 2; i <= k; i++) f *= i;
    NPERM = f;
    permtab = malloc((size_t)NPERM * NT);
    if (!permtab) { fprintf(stderr, "out of memory building permutations\n"); exit(2); }
    int idx[MAXQ], p = 0;
    for (int i = 0; i < k; i++) idx[i] = i;
    while (1) {
        for (int t = 0; t < NT; t++) {
            int u = 0;
            for (int j = 0; j < k; j++) if (t & (1 << j)) u |= 1 << idx[j];
            permtab[(size_t)p * NT + t] = (unsigned char)u;
        }
        p++;
        int i = k - 2;
        while (i >= 0 && idx[i] >= idx[i + 1]) i--;
        if (i < 0) break;
        int j = k - 1;
        while (idx[j] <= idx[i]) j--;
        int tmp = idx[i]; idx[i] = idx[j]; idx[j] = tmp;
        for (int a = i + 1, b = k - 1; a < b; a++, b--) { tmp = idx[a]; idx[a] = idx[b]; idx[b] = tmp; }
    }
}

/* lex-min test with a popcount lower-bound precheck */
static int canon_ok(const int *cur, int k) {
    unsigned char img[MAXN], lb[MAXN];
    canon_calls++;
    for (int a = 0; a < k; a++) {
        int m = cur[a];
        for (int i = 0; i < k; i++) {
            int w = __builtin_popcount((unsigned)(cur[i] ^ m));
            lb[i] = (unsigned char)((1u << w) - 1u);
        }
        for (int i = 1; i < k; i++) {           /* sort the bounds */
            unsigned char v = lb[i]; int j = i - 1;
            while (j >= 0 && lb[j] > v) { lb[j + 1] = lb[j]; j--; }
            lb[j + 1] = v;
        }
        int threat = 0;
        for (int i = 0; i < k; i++) {
            if (lb[i] < cur[i]) { threat = 1; break; }
            if (lb[i] > cur[i]) break;          /* bound already too large */
        }
        if (!threat) { canon_skips++; continue; }

        for (int p = 0; p < NPERM; p++) {
            const unsigned char *P = permtab + (size_t)p * NT;
            for (int i = 0; i < k; i++) img[i] = P[cur[i] ^ m];
            for (int i = 1; i < k; i++) {
                unsigned char v = img[i]; int j = i - 1;
                while (j >= 0 && img[j] > v) { img[j + 1] = img[j]; j--; }
                img[j + 1] = v;
            }
            for (int i = 0; i < k; i++) {
                if (img[i] < cur[i]) return 0;
                if (img[i] > cur[i]) break;
            }
        }
    }
    return 1;
}

static void progress(void) {
    printf("  t=%7.0fs nodes=[", elapsed(&t_start));
    for (int i = 0; i <= n; i++) printf("%lld%s", nodes[i], i < n ? "," : "");
    printf("] sols=%d canon=%lld skip=%lld\n", nsol, canon_calls, canon_skips);
    fflush(stdout);
}

static int dfs(int depth, long long count, int ncand) {
    nodes[depth]++;
    if (elapsed(&t_last) > report_every) { clock_gettime(CLOCK_MONOTONIC, &t_last); progress(); }
    if (depth == n) {
        nsol++;
        printf("SOLUTION #%d: types", nsol);
        for (int i = 0; i < n; i++) printf(" %d", sol[i]);
        printf("\n"); fflush(stdout);
        return nsol >= maxsol;
    }
    if (ncand < n - depth) return 0;                 /* lookahead prune */

    if (count >= TABSIZE) {
        fprintf(stderr, "hash table capacity exceeded at depth %d (%lld sums); refusing an incomplete search\n",
                depth, count);
        exit(2);
    }
    gen[depth]++;
    if (gen[depth] == 0) { memset(stamp[depth], 0, TABSIZE * sizeof(uint32_t)); gen[depth] = 1; }
    for (long long i = 0; i < count; i++) tab_insert(depth, sums[i]);

    /* filter the inherited candidates against the current sum set, once */
    int *C = cand[depth], *L = live[depth], nlive = 0;
    for (int ci = 0; ci < ncand; ci++) {
        int t = C[ci]; int64_t d = delta[t]; int ok = 1;
        for (long long i = 0; i < count; i++)
            if (tab_has(depth, sums[i] + d)) { ok = 0; break; }
        if (ok) L[nlive++] = t;
    }
    if (nlive < n - depth) return 0;                 /* lookahead prune */

    for (int ci = 0; ci < nlive; ci++) {
        if (nlive - ci < n - depth) break;           /* not enough left */
        int t = L[ci];
        if (depth == split_depth && nsplit > 1 && (split_counter++ % nsplit) != part) continue;
        sol[depth] = t;
        if (depth + 1 <= canon_depth && !canon_ok(sol, depth + 1)) continue;
        int64_t d = delta[t];
        for (long long i = 0; i < count; i++) sums[count + i] = sums[i] + d;
        int m = 0;
        for (int cj = ci + 1; cj < nlive; cj++) cand[depth + 1][m++] = L[cj];
        if (dfs(depth + 1, count * 2, m)) return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s q n [--split N --part B] [--maxsol K] [--report S] [--splitdepth D] [--canondepth D]\n", argv[0]); return 1; }
    if (!parse_int_arg("q", argv[1], &q) || !parse_int_arg("n", argv[2], &n)) return 1;
    int canon_depth_was_set = 0;
    for (int i = 3; i < argc; i++) {
        const char *flag = argv[i];
        if (i + 1 >= argc) { fprintf(stderr, "missing value for %s\n", flag); return 1; }
        if (!strcmp(flag, "--split")) { if (!parse_int_arg(flag, argv[++i], &nsplit)) return 1; }
        else if (!strcmp(flag, "--part")) { if (!parse_int_arg(flag, argv[++i], &part)) return 1; }
        else if (!strcmp(flag, "--maxsol")) { if (!parse_int_arg(flag, argv[++i], &maxsol)) return 1; }
        else if (!strcmp(flag, "--report")) { if (!parse_double_arg(flag, argv[++i], &report_every)) return 1; }
        else if (!strcmp(flag, "--splitdepth")) { if (!parse_int_arg(flag, argv[++i], &split_depth)) return 1; }
        else if (!strcmp(flag, "--canondepth")) { if (!parse_int_arg(flag, argv[++i], &canon_depth)) return 1; canon_depth_was_set = 1; }
        else { fprintf(stderr, "unknown option: %s\n", flag); return 1; }
    }
    if (q < 2 || q > MAXQ || n < 2 || n > MAXN) { fprintf(stderr, "q<=8, n<=20\n"); return 1; }
    if (!canon_depth_was_set && canon_depth > n) canon_depth = n;
    if (nsplit < 1 || part < 0 || part >= nsplit) {
        fprintf(stderr, "partition must satisfy --split >= 1 and 0 <= --part < --split\n");
        return 1;
    }
    if (maxsol < 1 || report_every <= 0 || split_depth < 1 || (nsplit > 1 && split_depth >= n) ||
        canon_depth < 0 || canon_depth > n) {
        fprintf(stderr, "require maxsol>=1, report>0, splitdepth>=1 (and <n when split), and 0<=canondepth<=n\n");
        return 1;
    }
    NT = 1 << (q - 1);
    for (int t = 0; t < NT; t++) {
        int64_t dd = 1;
        for (int j = 1; j < q; j++)
            dd += (int64_t)(((t >> (j - 1)) & 1) ? -1 : 1) * ((int64_t)1 << (8 * j));
        delta[t] = dd;
    }
    build_perms();
    sums = malloc(sizeof(uint64_t) * ((size_t)1 << n));
    if (!sums) { fprintf(stderr, "out of memory allocating subset sums\n"); return 2; }
    for (int d = 0; d <= n + 1; d++) {
        tab[d] = malloc(sizeof(uint64_t) * TABSIZE);
        stamp[d] = calloc(TABSIZE, sizeof(uint32_t));
        if (!tab[d] || !stamp[d]) { fprintf(stderr, "out of memory allocating hash tables\n"); return 2; }
        gen[d] = 0;
    }
    uint64_t zero = 0;
    for (int j = 0; j < q; j++) zero += (uint64_t)BIAS << (8 * j);
    sums[0] = zero; sums[1] = zero + delta[0]; sol[0] = 0;
    int nc = 0;
    for (int t = 1; t < NT; t++) cand[1][nc++] = t;

    clock_gettime(CLOCK_MONOTONIC, &t_start); t_last = t_start;
    printf("q=%d n=%d: %d types, %d perms, split %d/%d (depth %d), canon<=%d\n",
           q, n, NT, NPERM, part, nsplit, split_depth, canon_depth);
    fflush(stdout);

    dfs(1, 2, nc);

    double el = elapsed(&t_start);
    long long tot = 0;
    for (int i = 0; i <= n; i++) tot += nodes[i];
    printf("\nDONE in %.2fs  nodes/depth: [", el);
    for (int i = 0; i <= n; i++) printf("%lld%s", nodes[i], i < n ? "," : "");
    printf("]  total=%lld  rate=%.0f nodes/s  canon=%lld skipped=%lld\n",
           tot, tot / (el > 0 ? el : 1), canon_calls, canon_skips);
    printf("solutions found: %d\n", nsol);
    if (!nsol && nsplit == 1) printf("*** NO %dx%d DETECTING MATRIX EXISTS ***\n", q, n);
    else if (!nsol) printf("*** no solutions in %dx%d partition %d/%d ***\n", q, n, part, nsplit);
    return 0;  /* a completed search is successful; inspect "solutions found" for the verdict */
}
