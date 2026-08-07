# Findings

A lab notebook for the whole investigation, including the parts that failed.
Negative results and measurements are recorded because they were expensive to
obtain and are not, as far as we can tell, written down anywhere else.

Everything below concerns **detecting matrices**: a q×n matrix with entries ±1
such that no nonzero z ∈ {−1,0,1}ⁿ has Wz = 0. See the root README for why
β(Q_n) = min { q : a q×n detecting matrix exists }.

---

## 1. Results

| result | status | how |
|---|---|---|
| **β(Q₁₄) = 9** | proved | no 8×14 and no 7×14 detecting matrix exists (exhaustive) |
| **β(Q₁₅) = 9** | proved | no 8×15 (column deletion from 8×14); 9×15 matrix in `matrices/` |
| **M(14) = 8** | proved | Erdős–Rényi coin weighing, via the Lu–Ye bridge |
| β(Q₂₄) ≤ 13, β(Q₂₆) ≤ 14, β(Q₂₉) ≤ 15 | certified | explicit matrices in `matrices/` |
| β(Q₁₁) = β(Q₁₂) = β(Q₁₃) = 8 | reproduced | agrees with OEIS A303735 (Miller, MaxSAT, 2023) |

β(Q₁₄) = 9 confirms the value Mladenović et al. (2012) predicted from an
approximation algorithm. It was previously unproved: A303735 stops at n = 13.

---

## 2. What worked: enumeration, not search

The winning method (`enumerate/`) rests on one reformulation. Normalising row 0
to all +1 by flipping column signs makes every column one of 2^(q−1) *types*, and

> W is detecting ⟺ the 2ⁿ subset sums of its columns are pairwise distinct.

This is the classical coin-weighing formulation, and it collapses the search from
2^112 sign matrices (for 8×14) to 14-subsets of a 128-element set. Adding a
column `c` to a set with subset-sum set `S` is legal iff `(S + c) ∩ S = ∅` — one
hash probe per existing sum, early exit on collision.

### Measured effect of each optimisation (7×11, single core)

| version | nodes | time |
|---|---|---|
| plain DFS, first two columns canonicalised | 256,123,828 | 107 s |
| \+ Read–Faradžev lex-min pruning to depth 6 | 847,356 | 2.40 s |
| \+ monotone candidate lists, lookahead prune, popcount precheck | **189,831** | **1.75 s** |

**1,350× fewer nodes, 61× faster.** Lex-min pruning is sound because a lex-least
set has lex-least prefixes: if a group element made some prefix smaller it would
make the whole set smaller. Verified by rerunning with symmetry breaking off —
same verdicts, 2.5× more nodes.

### What canonical pruning does to the 8×14 frontier

| depth | nodes without lex-min pruning | with it |
|---|---|---|
| 5 | 1,282,411 | 1,082 |
| 6 | 34,942,921 | 11,364 |

A ~3,000× reduction. This is what turned 8×14 from an estimated 3.5 × 10¹³ nodes
(≈ a year on a laptop) into ~340 million nodes and **9.5 minutes on 10 cores**.

### Cost estimates, for calibration

Deeper canonicalisation keeps cutting nodes but costs more per node, so there is
an optimum. On 7×11: depth 6 → 2.40 s, depth 7 → 1.75 s, depth 8 → 5.30 s,
depth 9 → 12.85 s. Pick it empirically per (q, n).

---

## 3. What did not work

### CEGAR / SAT never closed the problem

A counterexample-guided loop (propose a matrix with a SAT solver, find a kernel
vector, forbid it for all matrices, repeat until UNSAT) is the obvious modern
approach and it **failed**, in an instructive way.

- It never closed **7×11** — the smallest open instance — after **13 hours** and
  ~6,600 accumulated constraints. The enumerator settled it in 1.75 s. Candidates
  reliably reached one or two kernel vectors and then crawled.
- The published-values ladder gives a sense of the growth in constraints needed:

  | instance | constraints at UNSAT |
  |---|---|
  | 3×4 | 9 |
  | 3×5 | 25 |
  | 4×6 | 60 |
  | 5×7 | 150 |
  | 5×8 | 238 |
  | 6×9 | 961 |
  | 6×10 | 1,440 |

  Extrapolating this curve suggested 8×14 would need ~100,000 constraints. It got
  past 29,000 with no sign of convergence.

### Encoding cardinality *disequality*: totalizers waste most of their work

Each forbidden kernel vector needs, per row, only the one-directional implication
"this row forces a nonzero dot product". A totalizer computes a full sorted
order. Measured on the real 29,000-constraint 8×14 instance:

| encoding | aux vars / constraint | clauses / constraint |
|---|---|---|
| totalizer | 218.5 | 947.5 |
| sequential counter (truncated) | 277.4 | 978.1 |
| binary adder tree | 116.7 | 646.9 |
| **direct forbid-each-exactly-half, support ≤ 8** | **54.9** | **565.1** |

The direct encoding uses **no auxiliary variables at all**, at a cost of
C(|S|,t) clauses per row; above support 8 that trade goes bad, so it falls back
to a totalizer. The support-8 cutoff beats cutoffs of 6, 10 and 12 on *both*
variables and clauses. Effect: 6×9 went from 40 s / 72,913 variables to
**4 s / 5,437 variables**, and iterations on 8×14 got ~100× cheaper.

Anyone encoding "the number of true literals is not exactly t" should check this
before reaching for a totalizer.

### Transplanted constraints are dead weight

Workers seeded with a shared pool of ~33,000 previously-discovered constraints
ran **two to three orders of magnitude slower per iteration** than workers that
started empty and learned their own (~3 iterations/hour versus ~15/minute). The
constraints were valid and the pool was hard-won; it still hurt. Whatever a CDCL
solver derives for itself is cheaper to carry than what you hand it.

### Symmetry-aware counterexample mining fixed the wrong problem

Mining each proposal's symmetry orbit and forbidding those kernel vectors too
raised the fresh-constraint rate ~50× (from ~10 to ~500 per iteration) but did
**not** reduce the kernel-vector count over five rounds. The surviving
near-misses were genuinely distinct matrices, not disguised duplicates. The
symmetry needed exploiting at the level of *object generation*, not constraint
learning — which is what the enumerator does.

### The first-moment heuristic is wildly wrong here

Treating the 2¹⁴ subset sums as independent predicts on the order of 10¹⁵ valid
8×14 matrices. There are none. Correlations dominate completely; do not use
counting heuristics to decide whether to look.

---

## 4. Verification discipline

For the exact value, in order of how much weight we place on it:

1. **External agreement.** The enumerator reproduces β(Q₁₁), β(Q₁₂), β(Q₁₃) = 8,
   computed independently by V. S. Miller in 2023 with a MaxSAT solver. Two
   unrelated methods, same answers. This matters more than any self-check.
2. **An independent reimplementation.** A clean-room CEGAR SAT solver, written by
   a different model (Gemini, via the Antigravity CLI) from the problem statement
   alone with no access to this code, agrees on **18 of 19** decidable instances —
   every nonexistence result up to and including **7×14**, and every existence
   result up to 8×13. It could *not* settle 8×14: it stalled after ~308,000
   counterexamples and estimated 10–50 hours, independently rediscovering the
   CEGAR wall described in §3. So the 7×14 half of the β(Q₁₄) lower bound has
   external confirmation; the 8×14 half does not.
3. **Positive control on the machinery.** The identical code and flags — including
   the work-splitting — *do* find matrices for 8×11, 8×12 and 8×13, in every
   part. A checker that cannot fail is not a checker.
4. **Partition coherence.** All ten parts of the 8×14 run report identical node
   counts down to the split depth (`0,1,6,18,143,1082,11364`) and disjoint work
   below it.
5. **A different logical route.** `enumerate/verify_extensions.py` never searches
   to depth 14. Deleting a column from an 8×14 matrix leaves an 8×13 one, so if
   every 8×13 matrix is extension-maximal, no 8×14 exists. Written in Python,
   sums rebuilt from scratch, sharing no code with the C search.

**Known limitation.** The enumerator and the extension checker were written by
the same author in the same sitting, so items 3–5 are internal checks. Items 1
and 2 are external, and neither covers **8×14** itself — the one instance the
new value actually depends on. A second exhaustive run of 8×14 by unrelated
code, or a SAT proof emitting a DRAT certificate, would be worth more than any
further internal cross-check.

For β(Q₁₅) = 9 the upper bound is a plain certificate: `matrices/beta_Q15_le_9.txt`
is verified by `verify.c` and `verify.js`, written independently of each other and
of the search. The lower bound inherits whatever confidence 8×14 carries.

---

## 5. Open

- **a(16) of A303735.** The conjecture is 10, i.e. no 9×16 detecting matrix.
  This needs q = 9, which the current code does not support: the 64-bit packing
  uses 8 bits × 8 coordinates and would have to become 7 bits × 9. The search is
  also substantially larger (256 column types instead of 128).
- **Optimisations left on the table**, if a bigger case is attempted: replacing
  the brute-force permutation loop in the canonicity test with partition
  refinement (nauty-style) would allow canonicalising at the depths where the
  nodes actually are (11–12), and there is an additional symmetry of up to 8×
  from the freedom of *which* row is normalised to all +1 — permuting another row
  into position 0 and renormalising is not a bit-permutation-plus-XOR, so it lies
  outside the group currently used.
- **Upper bounds beyond n = 29.** Recomputing the Nikolić dynamic-programming
  cascade with our three improved seeds yields nothing new: the Lu–Ye bound
  dominates every path for n > 29.
