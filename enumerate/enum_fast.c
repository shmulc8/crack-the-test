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
 * q=9 uses 7-bit packed coordinates; q<=8 keeps the original 8-bit layout.
 * Frontier dumping and forced prefixes support reproducible sampling and a
 * dynamically scheduled full run without changing the search tree.
 *
 * usage: enum q n [--split N --part B] [--maxsol K] [--report SEC]
 *                 [--splitdepth D] [--canondepth D]
 *                 [--dumpdepth D] [--prefix 0,T1,...]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include <errno.h>
#include <limits.h>
#include <math.h>

#define MAXQ 9
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
static int field_bits = 8;
static int dump_depth = -1;
static long long frontier_count = 0;
static int prefix_types[MAXN + 2], prefix_len = 0;

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
static int use_pivots = 0;
static unsigned char pivottab[MAXQ][256];

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

static int parse_prefix_arg(const char *text) {
    const char *p = text;
    prefix_len = 0;
    if (!*p) {
        fprintf(stderr, "invalid --prefix: empty value\n");
        return 0;
    }
    while (*p) {
        char *end = NULL;
        errno = 0;
        long value = strtol(p, &end, 10);
        if (errno || end == p || value < 0 || value > 255 ||
            prefix_len >= MAXN + 1 || (*end != '\0' && *end != ',')) {
            fprintf(stderr, "invalid --prefix: %s\n", text);
            return 0;
        }
        prefix_types[prefix_len++] = (int)value;
        if (*end == '\0') break;
        p = end + 1;
        if (!*p) {
            fprintf(stderr, "invalid --prefix: %s\n", text);
            return 0;
        }
    }
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

    for (int t = 0; t < NT; t++) pivottab[0][t] = (unsigned char)t;
    for (int R = 1; R < q; R++) {
        int r_bit = R - 1;
        for (int t = 0; t < NT; t++) {
            int b_R = (t >> r_bit) & 1;
            int new_t = 0;
            int out_bit = 0;
            if (b_R) new_t |= (1 << out_bit);
            out_bit++;
            for (int r_other = 0; r_other < k; r_other++) {
                if (r_other == r_bit) continue;
                int b_other = (t >> r_other) & 1;
                if (b_R ^ b_other) new_t |= (1 << out_bit);
                out_bit++;
            }
            pivottab[R][t] = (unsigned char)new_t;
        }
    }
}

/* lex-min test with a popcount lower-bound precheck and optional row pivots */
static int canon_ok(const int *cur, int k) {
    unsigned char img[MAXN], lb[MAXN];
    int transformed[MAXN];
    canon_calls++;

    int max_pivots = use_pivots ? q : 1;

    for (int piv = 0; piv < max_pivots; piv++) {
        const unsigned char *piv_map = pivottab[piv];
        for (int i = 0; i < k; i++) transformed[i] = piv_map[cur[i]];

        for (int a = 0; a < k; a++) {
            int m = transformed[a];
            for (int i = 0; i < k; i++) {
                int w = __builtin_popcount((unsigned)(transformed[i] ^ m));
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
                for (int i = 0; i < k; i++) img[i] = P[transformed[i] ^ m];
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
    }
    return 1;
}

/* Minimal-image search under bit permutations (partition backtrack).
   A coset of permutations is an ordered list of cells (A_c -> B_c): input
   bits A_c map bijectively onto output bits B_c. The smallest value an
   unused element x can take is, per cell, the |x & A_c| lowest bits of B_c;
   the next point of the minimal image is the least such value, reached only
   when every cell sends x's bits onto those lowest bits. */
static unsigned char lowbits[256][9];
static void build_lowbits(void) {
    for (int b = 0; b < 256; b++)
        for (int j = 0; j <= 8; j++) {
            int out = 0, got = 0;
            for (int i = 0; i < 8 && got < j; i++) if (b >> i & 1) { out |= 1 << i; got++; }
            lowbits[b][j] = (unsigned char)(got == j ? out : 0xFF);
        }
}
static long long fast_canon_nodes = 0;
static int min_image_less(const int *X, int k, const int *cur, int i,
                          const unsigned char *A, const unsigned char *B, int ncell, unsigned used) {
    fast_canon_nodes++;
    if (i == k) return 0;
    int mi[MAXN], p = 1 << 30;
    for (int x = 0; x < k; x++) {
        if (used >> x & 1) { mi[x] = 1 << 30; continue; }
        int v = 0;
        for (int c = 0; c < ncell; c++) v |= lowbits[B[c]][__builtin_popcount(X[x] & A[c])];
        mi[x] = v;
        if (v < p) p = v;
    }
    if (p < cur[i]) return 1;
    if (p > cur[i]) return 0;
    for (int x = 0; x < k; x++) {
        if (mi[x] != p) continue;
        unsigned char A2[9], B2[9]; int n2 = 0;
        for (int c = 0; c < ncell; c++) {
            unsigned char a = (unsigned char)(X[x] & A[c]);
            unsigned char b = lowbits[B[c]][__builtin_popcount(a)];
            if (a) { A2[n2] = a; B2[n2] = b; n2++; }
            if (A[c] & ~a) { A2[n2] = (unsigned char)(A[c] & ~a); B2[n2] = (unsigned char)(B[c] & ~b); n2++; }
        }
        if (min_image_less(X, k, cur, i + 1, A2, B2, n2, used | 1u << x)) return 1;
    }
    return 0;
}
/* Same verdict as canon_ok: is cur lex-least in its orbit? */
static int canon_fast(const int *cur, int k) {
    canon_calls++;
    int max_pivots = use_pivots ? q : 1;
    int nb = q - 1;
    unsigned char A0 = (unsigned char)((1 << nb) - 1);
    for (int piv = 0; piv < max_pivots; piv++) {
        int transformed[MAXN], X[MAXN];
        for (int i = 0; i < k; i++) transformed[i] = pivottab[piv][cur[i]];
        for (int a = 0; a < k; a++) {
            int m = transformed[a];
            for (int i = 0; i < k; i++) X[i] = transformed[i] ^ m;
            unsigned char A[1] = {A0}, B[1] = {A0};
            if (min_image_less(X, k, cur, 1, A, B, 1, 1u << a)) return 0;
        }
    }
    return 1;
}
static int canon_mode = 0;   /* 0 brute force, 1 fast, 2 both with a mismatch abort */
static int canon_check(const int *cur, int k) {
    if (canon_mode == 0) return canon_ok(cur, k);
    if (canon_mode == 1) return canon_fast(cur, k);
    int a = canon_ok(cur, k), b = canon_fast(cur, k);
    if (a != b) {
        fprintf(stderr, "canon mismatch (brute=%d fast=%d):", a, b);
        for (int i = 0; i < k; i++) fprintf(stderr, " %d", cur[i]);
        fprintf(stderr, "\n"); exit(3);
    }
    return a;
}

static void progress(void) {
    printf("  t=%7.0fs nodes=[", elapsed(&t_start));
    for (int i = 0; i <= n; i++) printf("%lld%s", nodes[i], i < n ? "," : "");
    printf("] sols=%d canon=%lld skip=%lld\n", nsol, canon_calls, canon_skips);
    fflush(stdout);
}

/* v is in T(S) = Sums - Sums iff some s + v is a subset sum */
static inline int in_ternary_span(int d, long long count, int64_t v) {
    for (long long i = 0; i < count; i++)
        if (tab_has(d, sums[i] + v)) return 1;
    return 0;
}

typedef struct { uint64_t w[4]; } bits256;
static bits256 adj[MAXN + 2][256];   /* adjacency rows indexed by position in L */
static int clique_from = 1 << 30;
static int exact_clique = 0;     /* apply the compatibility-graph bound from this depth */
static long long clique_prunes[MAXN + 2];

/* Greedy colouring of the graph induced on vertices 0..m-1; returns a number of
   colours >= the clique number (each colour class is an independent set). */
static int colour_bound(bits256 *A, int m, int stop_at) {
    bits256 U = {{0, 0, 0, 0}};
    for (int i = 0; i < m; i++) U.w[i >> 6] |= 1ULL << (i & 63);
    int colours = 0;
    while (U.w[0] | U.w[1] | U.w[2] | U.w[3]) {
        if (++colours >= stop_at) return colours;
        bits256 Q = U;
        while (Q.w[0] | Q.w[1] | Q.w[2] | Q.w[3]) {
            int wi = 0; while (!Q.w[wi]) wi++;
            int v = (wi << 6) + __builtin_ctzll(Q.w[wi]);
            U.w[v >> 6] &= ~(1ULL << (v & 63));
            Q.w[v >> 6] &= ~(1ULL << (v & 63));
            for (int j = 0; j < 4; j++) Q.w[j] &= ~A[v].w[j];
        }
    }
    return colours;
}

/* Meet-in-the-middle membership in T(S) = { sum z_i c_i : z in {-1,0,1}^|S| }.
   For depth d <= anchor, ttab[d] hashes T(S_d) itself (at most 3^d entries).
   For d > anchor, S_d = P u R with P = S_anchor, and T(S_d) = T(P) + T(R):
   v is in T(S_d) iff v - r is in ttab[anchor] for some r in tr[d] = T(R). */
#define LOGT 16
#define TSIZE (1u << LOGT)
static int anchor = 0;
static uint64_t zero_key;
static uint64_t *ttab[MAXN + 2], *tlist[MAXN + 2];
static uint32_t *tstamp[MAXN + 2], tgen[MAXN + 2];
static long long tcount[MAXN + 2];
static int64_t *tr[MAXN + 2];
static long long trcount[MAXN + 2];

static inline uint32_t tslot(uint64_t x) { return (uint32_t)((x * 0x9E3779B97F4A7C15ULL) >> (64 - LOGT)); }
static inline int t_has(int d, uint64_t key) {
    uint32_t s = tslot(key);
    while (tstamp[d][s] == tgen[d]) {
        if (ttab[d][s] == key) return 1;
        s = (s + 1) & (TSIZE - 1);
    }
    return 0;
}
static inline void t_add(int d, uint64_t key) {
    uint32_t s = tslot(key);
    while (tstamp[d][s] == tgen[d]) {
        if (ttab[d][s] == key) return;
        s = (s + 1) & (TSIZE - 1);
    }
    ttab[d][s] = key; tstamp[d][s] = tgen[d];
    tlist[d][tcount[d]++] = key;
}
/* build the T structure for depth d from depth d-1 and the newest column */
static void t_build(int d) {
    int64_t c = delta[sol[d - 1]];
    if (d <= anchor) {
        tgen[d]++;
        if (tgen[d] == 0) { memset(tstamp[d], 0, TSIZE * sizeof(uint32_t)); tgen[d] = 1; }
        tcount[d] = 0;
        if (d == 1) { t_add(d, zero_key); t_add(d, zero_key + c); t_add(d, zero_key - c); return; }
        long long m = tcount[d - 1];
        if (3 * m > (long long)TSIZE / 2) { fprintf(stderr, "T table too small at depth %d\n", d); exit(2); }
        for (long long i = 0; i < m; i++) {
            uint64_t x = tlist[d - 1][i];
            t_add(d, x); t_add(d, x + c); t_add(d, x - c);
        }
    } else {
        long long m = (d - 1 == anchor) ? 1 : trcount[d - 1];
        int64_t *src = tr[d - 1], *dst = tr[d];
        if (d - 1 == anchor) { dst[0] = 0; dst[1] = c; dst[2] = -c; trcount[d] = 3; return; }
        for (long long i = 0; i < m; i++) { dst[3 * i] = src[i]; dst[3 * i + 1] = src[i] + c; dst[3 * i + 2] = src[i] - c; }
        trcount[d] = 3 * m;
    }
}
static inline int in_T(int d, int64_t v) {
    if (d <= anchor) return t_has(d, zero_key + (uint64_t)v);
    const int64_t *R = tr[d];
    for (long long i = 0; i < trcount[d]; i++)
        if (t_has(anchor, zero_key + (uint64_t)(v - R[i]))) return 1;
    return 0;
}

/* Exact k-clique existence in the graph A restricted to P (Tomita-style
   branch and bound: greedy colour P, expand vertices in decreasing colour,
   stop when the colour bound cannot reach k). */
static int popc256(const bits256 *x) {
    return __builtin_popcountll(x->w[0]) + __builtin_popcountll(x->w[1]) +
           __builtin_popcountll(x->w[2]) + __builtin_popcountll(x->w[3]);
}
static int has_clique(const bits256 *A, bits256 P, int k) {
    if (k <= 0) return 1;
    if (popc256(&P) < k) return 0;
    if (k == 1) return 1;
    int order[256], colour[256], m = 0, c = 0;
    bits256 U = P;
    while (U.w[0] | U.w[1] | U.w[2] | U.w[3]) {
        c++;
        bits256 Q = U;
        while (Q.w[0] | Q.w[1] | Q.w[2] | Q.w[3]) {
            int wi = 0; while (!Q.w[wi]) wi++;
            int v = (wi << 6) + __builtin_ctzll(Q.w[wi]);
            U.w[v >> 6] &= ~(1ULL << (v & 63));
            Q.w[v >> 6] &= ~(1ULL << (v & 63));
            for (int j = 0; j < 4; j++) Q.w[j] &= ~A[v].w[j];
            order[m] = v; colour[m] = c; m++;
        }
    }
    for (int i = m - 1; i >= 0; i--) {
        if (colour[i] < k) return 0;
        int v = order[i];
        bits256 NP;
        for (int j = 0; j < 4; j++) NP.w[j] = P.w[j] & A[v].w[j];
        if (has_clique(A, NP, k - 1)) return 1;
        P.w[v >> 6] &= ~(1ULL << (v & 63));
    }
    return 0;
}

static int dfs(int depth, long long count, int ncand, int prefiltered) {
    nodes[depth]++;
    if (dump_depth >= 0 && depth == dump_depth) {
        printf("FRONTIER ");
        for (int i = 0; i < depth; i++) printf("%d%s", sol[i], i + 1 < depth ? "," : "");
        printf("\n");
        frontier_count++;
        return 0;
    }
    if (elapsed(&t_last) > report_every) { clock_gettime(CLOCK_MONOTONIC, &t_last); progress(); }
    if (depth == n) {
        nsol++;
        printf("SOLUTION #%d: types", nsol);
        for (int i = 0; i < n; i++) printf(" %d", sol[i]);
        printf("\n"); fflush(stdout);
        return nsol >= maxsol;
    }
    if (ncand < n - depth) return 0;                 /* lookahead prune */

    if (!anchor && count >= TABSIZE) {
        fprintf(stderr, "hash table capacity exceeded at depth %d (%lld sums); refusing an incomplete search\n",
                depth, count);
        exit(2);
    }
    if (anchor) {
        t_build(depth);
    } else {
        gen[depth]++;
        if (gen[depth] == 0) { memset(stamp[depth], 0, TABSIZE * sizeof(uint32_t)); gen[depth] = 1; }
        for (long long i = 0; i < count; i++) tab_insert(depth, sums[i]);
    }

    /* filter the inherited candidates against the current sum set, once */
    int *C = cand[depth], *L = live[depth], nlive = 0;
    if (prefiltered) {
        for (int ci = 0; ci < ncand; ci++) L[nlive++] = C[ci];
    } else {
        for (int ci = 0; ci < ncand; ci++) {
            int t = C[ci]; int64_t d = delta[t]; int ok = 1;
            if (anchor) ok = !in_T(depth, d);
            else for (long long i = 0; i < count; i++)
                if (tab_has(depth, sums[i] + d)) { ok = 0; break; }
            if (ok) L[nlive++] = t;
        }
    }
    if (nlive < n - depth) return 0;                 /* lookahead prune */

    /* Compatibility graph: the remaining n-depth columns must be pairwise
       compatible, where a,b are compatible iff b is legal after adding a,
       i.e. a+b and a-b both lie outside T(S). A colouring with fewer colours
       than columns still needed proves there is no such clique. */
    int use_graph = depth >= clique_from && n - depth >= 2;
    bits256 *A = adj[depth];
    if (use_graph) {
        for (int i = 0; i < nlive; i++) A[i] = (bits256){{0, 0, 0, 0}};
        for (int i = 0; i < nlive; i++) {
            int64_t di = delta[L[i]];
            for (int j = i + 1; j < nlive; j++) {
                int64_t dj = delta[L[j]];
                if (anchor) {
                    if (in_T(depth, dj - di) || in_T(depth, dj + di)) continue;
                } else {
                    if (in_ternary_span(depth, count, dj - di)) continue;
                    if (in_ternary_span(depth, count, dj + di)) continue;
                }
                A[i].w[j >> 6] |= 1ULL << (j & 63);
                A[j].w[i >> 6] |= 1ULL << (i & 63);
            }
        }
        if (exact_clique) {
            bits256 all = {{0, 0, 0, 0}};
            for (int i = 0; i < nlive; i++) all.w[i >> 6] |= 1ULL << (i & 63);
            if (!has_clique(A, all, n - depth)) { clique_prunes[depth]++; return 0; }
        } else if (colour_bound(A, nlive, n - depth) < n - depth) { clique_prunes[depth]++; return 0; }
    }

    for (int ci = 0; ci < nlive; ci++) {
        if (nlive - ci < n - depth) break;           /* not enough left */
        int t = L[ci];
        if (depth < prefix_len && t != prefix_types[depth]) continue;
        if (depth == split_depth && nsplit > 1 && (split_counter++ % nsplit) != part) continue;
        sol[depth] = t;
        if (depth + 1 <= canon_depth && !canon_check(sol, depth + 1)) continue;
        int64_t d = delta[t];
        if (!anchor) for (long long i = 0; i < count; i++) sums[count + i] = sums[i] + d;
        int m = 0;
        if (use_graph) {
            for (int cj = ci + 1; cj < nlive; cj++)
                if (A[ci].w[cj >> 6] >> (cj & 63) & 1) cand[depth + 1][m++] = L[cj];
        } else {
            for (int cj = ci + 1; cj < nlive; cj++) cand[depth + 1][m++] = L[cj];
        }
        if (dfs(depth + 1, count * 2, m, use_graph)) return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: %s q n [--split N --part B] [--maxsol K] [--report S] [--splitdepth D] [--canondepth D] [--dumpdepth D] [--prefix 0,T1,...]\n", argv[0]); return 1; }
    if (!parse_int_arg("q", argv[1], &q) || !parse_int_arg("n", argv[2], &n)) return 1;
    int canon_depth_was_set = 0;
    for (int i = 3; i < argc; i++) {
        const char *flag = argv[i];
        if (!strcmp(flag, "--pivots")) { use_pivots = 1; continue; }
        if (!strcmp(flag, "--exact-clique")) { exact_clique = 1; continue; }
        if (!strcmp(flag, "--fast-canon")) { canon_mode = 1; continue; }
        if (!strcmp(flag, "--check-canon")) { canon_mode = 2; continue; }
        if (!strcmp(flag, "--no-pivots")) { use_pivots = 0; continue; }
        if (i + 1 >= argc) { fprintf(stderr, "missing value for %s\n", flag); return 1; }
        if (!strcmp(flag, "--split")) { if (!parse_int_arg(flag, argv[++i], &nsplit)) return 1; }
        else if (!strcmp(flag, "--part")) { if (!parse_int_arg(flag, argv[++i], &part)) return 1; }
        else if (!strcmp(flag, "--maxsol")) { if (!parse_int_arg(flag, argv[++i], &maxsol)) return 1; }
        else if (!strcmp(flag, "--report")) { if (!parse_double_arg(flag, argv[++i], &report_every)) return 1; }
        else if (!strcmp(flag, "--splitdepth")) { if (!parse_int_arg(flag, argv[++i], &split_depth)) return 1; }
        else if (!strcmp(flag, "--canondepth")) { if (!parse_int_arg(flag, argv[++i], &canon_depth)) return 1; canon_depth_was_set = 1; }
        else if (!strcmp(flag, "--dumpdepth")) { if (!parse_int_arg(flag, argv[++i], &dump_depth)) return 1; }
        else if (!strcmp(flag, "--prefix")) { if (!parse_prefix_arg(argv[++i])) return 1; }
        else if (!strcmp(flag, "--mitm")) { if (!parse_int_arg(flag, argv[++i], &anchor)) return 1; }
        else if (!strcmp(flag, "--clique")) { if (!parse_int_arg(flag, argv[++i], &clique_from)) return 1; }
        else { fprintf(stderr, "unknown option: %s\n", flag); return 1; }
    }
    if (q < 2 || q > MAXQ || n < 2 || n > MAXN) { fprintf(stderr, "require 2<=q<=9 and 2<=n<=20\n"); return 1; }
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
    if (dump_depth != -1 && (dump_depth < 1 || dump_depth >= n || nsplit != 1)) {
        fprintf(stderr, "require 1<=dumpdepth<n and no split partition while dumping a frontier\n");
        return 1;
    }
    if (prefix_len) {
        if (prefix_len > n || prefix_types[0] != 0) {
            fprintf(stderr, "prefix must start with normalized type 0 and contain at most n types\n");
            return 1;
        }
        for (int i = 1; i < prefix_len; i++) {
            if (prefix_types[i] <= prefix_types[i - 1]) {
                fprintf(stderr, "prefix types must be strictly increasing\n");
                return 1;
            }
        }
    }
    NT = 1 << (q - 1);
    for (int i = 0; i < prefix_len; i++) {
        if (prefix_types[i] >= NT) {
            fprintf(stderr, "prefix type %d is outside 0..%d for q=%d\n", prefix_types[i], NT - 1, q);
            return 1;
        }
    }
    field_bits = (q == 9) ? 7 : 8;
    for (int t = 0; t < NT; t++) {
        int64_t dd = 1;
        for (int j = 1; j < q; j++)
            dd += (int64_t)(((t >> (j - 1)) & 1) ? -1 : 1) * ((int64_t)1 << (field_bits * j));
        delta[t] = dd;
    }
    build_perms();
    build_lowbits();
    sums = malloc(sizeof(uint64_t) * ((size_t)1 << n));
    if (!sums) { fprintf(stderr, "out of memory allocating subset sums\n"); return 2; }
    for (int d = 0; d <= n + 1; d++) {
        tab[d] = malloc(sizeof(uint64_t) * TABSIZE);
        stamp[d] = calloc(TABSIZE, sizeof(uint32_t));
        if (!tab[d] || !stamp[d]) { fprintf(stderr, "out of memory allocating hash tables\n"); return 2; }
        gen[d] = 0;
    }
    uint64_t zero = 0;
    for (int j = 0; j < q; j++) zero += (uint64_t)BIAS << (field_bits * j);
    zero_key = zero;
    if (anchor < 0 || anchor > 9 || anchor >= n) { fprintf(stderr, "require 0<=mitm<=9 and mitm<n\n"); return 1; }
    if (anchor) {
        long long rmax = 1;
        for (int i = 0; i < n - anchor; i++) rmax *= 3;
        for (int d = 0; d <= n + 1; d++) {
            if (d <= anchor) {
                ttab[d] = malloc(sizeof(uint64_t) * TSIZE);
                tlist[d] = malloc(sizeof(uint64_t) * TSIZE);
                tstamp[d] = calloc(TSIZE, sizeof(uint32_t));
                if (!ttab[d] || !tlist[d] || !tstamp[d]) { fprintf(stderr, "out of memory\n"); return 2; }
            } else {
                tr[d] = malloc(sizeof(int64_t) * rmax);
                if (!tr[d]) { fprintf(stderr, "out of memory\n"); return 2; }
            }
        }
    }
    sums[0] = zero; sums[1] = zero + delta[0]; sol[0] = 0;
    int nc = 0;
    for (int t = 1; t < NT; t++) cand[1][nc++] = t;

    clock_gettime(CLOCK_MONOTONIC, &t_start); t_last = t_start;
    printf("q=%d n=%d: %d types, %d perms, split %d/%d (depth %d), canon<=%d%s\n",
           q, n, NT, NPERM, part, nsplit, split_depth, canon_depth, use_pivots ? ", pivots=on" : "");
    if (prefix_len) {
        printf("forced prefix:");
        for (int i = 0; i < prefix_len; i++) printf(" %d", prefix_types[i]);
        printf("\n");
    }
    if (dump_depth >= 0) printf("dumping canonical frontier at depth %d\n", dump_depth);
    fflush(stdout);

    dfs(1, 2, nc, 0);

    double el = elapsed(&t_start);
    long long tot = 0;
    for (int i = 0; i <= n; i++) tot += nodes[i];
    printf("\nDONE in %.2fs  nodes/depth: [", el);
    for (int i = 0; i <= n; i++) printf("%lld%s", nodes[i], i < n ? "," : "");
    printf("]  total=%lld  rate=%.0f nodes/s  canon=%lld skipped=%lld\n",
           tot, tot / (el > 0 ? el : 1), canon_calls, canon_skips);
    printf("clique prunes/depth: [");
    for (int i = 0; i <= n; i++) printf("%lld%s", clique_prunes[i], i < n ? "," : "");
    printf("]\n");
    printf("solutions found: %d\n", nsol);
    if (dump_depth >= 0) printf("frontier prefixes: %lld\n", frontier_count);
    else if (!nsol && prefix_len) printf("*** no solutions below the requested prefix ***\n");
    else if (!nsol && nsplit == 1) printf("*** NO %dx%d DETECTING MATRIX EXISTS ***\n", q, n);
    else if (!nsol) printf("*** no solutions in %dx%d partition %d/%d ***\n", q, n, part, nsplit);
    return 0;  /* a completed search is successful; inspect "solutions found" for the verdict */
}
