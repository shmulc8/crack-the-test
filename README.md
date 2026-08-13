# The metric dimension of hypercubes: β(Q₁₄) = 9, and new upper bounds for Q₂₄, Q₂₆, Q₂₉

Two kinds of result on the metric dimension β(Q_n) of the hypercube: explicit,
machine-checkable matrices for the upper bounds, and reproducible exhaustive
search code plus the recorded partition totals for the lower bound.

Journal-style manuscript: [`paper/main.tex`](paper/main.tex). Reproduction and
archival checklist: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md). A copy-ready
brief for an external mathematical reviewer is in
[`EXTERNAL_REVIEW.md`](EXTERNAL_REVIEW.md); no external message has been sent.

## 1. An exact value: β(Q₁₄) = 9

[OEIS A303735](https://oeis.org/A303735) gives β(Q_n) for n ≤ 13 —
`1,2,3,4,4,5,6,6,7,7,8,8,8` — and is tagged `hard,more`. Mladenović et al. (2012)
*conjectured* 8, 8, 8, 9, 9, 10, 10 for n = 11…17 from an approximation
algorithm; Victor S. Miller confirmed the first three of those in 2023 with a
MaxSAT solver. This repo proves the fourth:

| | result |
|---|---|
| **β(Q₁₄) = 9** | exhaustive: no 8×14 detecting matrix exists (and none for 7×14) |
| **β(Q₁₅) = 9** | corollary below, with its own certificate |
| **M(14) = 8** | Erdős–Rényi coin-weighing constant, with its own certificate |

β(Q₁₅) ≥ 9 follows because deleting a column from an 8×15 detecting matrix would
leave an 8×14 one, so no 8×15 exists either. The matching upper bound is
[`matrices/beta_Q15_le_9.txt`](matrices/beta_Q15_le_9.txt), a 9×15 detecting
matrix found here and checkable in seconds — so both halves of β(Q₁₅) = 9 are
self-contained rather than resting on a published resolving set.

**M(14) = 8.** The Erdős–Rényi constant M(n) is the least number of {0,1}
weighings that separate every subset of n coins on a spring scale. It is a
different quantity from β(Q_n), which counts ±1 rows, and the two are only
pinned to within one of each other:

> β(Q_n) − 1 ≤ M(n) ≤ β(Q_n).

The right inequality normalises row 0 of a detecting matrix to all +1 by column
sign flips — which preserves the detecting property, since Wz = 0 and (WD)(Dz) = 0
are the same condition — and reads the q rows off as q weighings, one of which is
the all-ones weighing that supplies the subset size. The left inequality adds an
all-ones row to a weighing strategy. The gap is genuinely not constant — for
n ≤ 10 it is 1 exactly at n = 4, 7, 9 and 0 elsewhere — so an exact β does
**not** by itself determine M.

This settles M(14) exactly. The upper half M(14) ≤ 8 was already reachable —
Lu–Ye (2022) Table 2 records Ψ(Q₁₄) = 9 from the VNS and IPBS searches, and
Ψ = M + 1 — but the matching lower bound was not available. β(Q₁₄) = 9 supplies
it: M(14) ≥ 8. [`matrices/M14_le_8.txt`](matrices/M14_le_8.txt) re-derives the
upper half here (14 vectors in {0,1}⁸ whose 2¹⁴ subset sums are pairwise
distinct), so M(14) = 8 is checkable end to end in this repo.

Code, method and reproduction instructions: [`enumerate/`](enumerate/). The
search also reproduces β(Q₁₁) = β(Q₁₂) = β(Q₁₃) = 8 in about a second each,
agreeing with Miller's independent MaxSAT computation. That is a useful external
control on the method at smaller parameters; it does not independently verify
the decisive 8×14 run.

The code-level exhaustiveness argument is written out in
[`enumerate/ENUMERATION_PROOF.md`](enumerate/ENUMERATION_PROOF.md), including
the proof obligations for every pruning rule and the ten-way split. A separate
small Python enumerator checks complete solution sets, symmetry representatives,
and partition unions on tractable instances without reusing the C search.
The full 8×14 computation has also been reproduced by a standalone safe-Rust
implementation whose ten complete node vectors match the C implementation
exactly and whose runtime is comparable.

## 2. Three improved upper bounds

| n  | best published | this repo | certificate |
|----|----------------|-----------|-------------|
| 24 | 14 (Hertz 2020; Lu–Ye 2022) | **β(Q₂₄) ≤ 13** | [`matrices/beta_Q24_le_13.txt`](matrices/beta_Q24_le_13.txt) |
| 26 | 15 (Hertz 2020; Lu–Ye 2022) | **β(Q₂₆) ≤ 14** | [`matrices/beta_Q26_le_14.txt`](matrices/beta_Q26_le_14.txt) |
| 29 | 16 (Nikolić et al. 2017; Lu–Ye 2022) | **β(Q₂₉) ≤ 15** | [`matrices/beta_Q29_le_15.txt`](matrices/beta_Q29_le_15.txt) |

In riddle form: a score-only true/false test with 24 / 26 / 29 questions can be
guaranteed perfect in **14 / 15 / 16** attempts — one fewer than previously known
in each case. Interactive demo: **https://crack-the-test.netlify.app**

## Why a sign matrix is a certificate

**Lemma.** Let W be a q×n matrix with entries ±1 such that no nonzero
z ∈ {−1,0,1}ⁿ satisfies Wz = 0. Then the q vertices vᵢ = (1 − rowᵢ)/2 ∈ {0,1}ⁿ
form a resolving set of Q_n, hence β(Q_n) ≤ q.

*Proof.* For x, y ∈ {0,1}ⁿ, the Hamming distances satisfy
d(x, vᵢ) − d(y, vᵢ) = Σⱼ (xⱼ − yⱼ)(1 − 2vᵢⱼ) = rowᵢ · (x − y).
If x ≠ y have equal distance to every vᵢ, then z = x − y is a nonzero vector in
{−1,0,1}ⁿ with Wz = 0 — contradiction. ∎

Call such a W a **detecting matrix**. The lemma runs both ways: an upper bound is
certified by exhibiting one, while a *lower* bound requires an exhaustive
nonexistence computation. Hence β(Q_n) = min { q : a q×n detecting matrix
exists }, which is exactly what [`enumerate/`](enumerate/) decides.

## Verify it yourself

Every upper-bound certificate in `matrices/` reduces to one finite check — the
matrix has no nonzero ternary kernel vector — done exhaustively by
meet-in-the-middle over all 3ⁿ candidates (the largest half has 3¹⁵ ≈ 14.3M
assignments for the 29-column certificate). Two
independent implementations, seconds each:

```sh
# JavaScript (bun or node >= 18)
bun verify.js matrices/beta_Q24_le_13.txt

# C
cc -O2 -o verify verify.c
./verify matrices/beta_Q24_le_13.txt
```

Expected output ends with `VALID certificate: beta(Q_n) <= q`.
`./test.sh` runs both implementations on all four sign matrices, checks the
M(14) weighing certificate, and requires both kinds of deliberately broken
certificate plus an empty matrix to be rejected.

For the exact value, `enumerate/ladder.sh` reproduces every published term of
A303735 and then settles 8×14.

## How the results were found

**The exact value (β(Q₁₄))** came from exhaustive enumeration, not search.
Normalising row 0 to all +1 makes every column one of 2^(q−1) types and turns
"detecting" into "all 2ⁿ subset sums are distinct"; a depth-first walk over
n-subsets with Read–Faradžev orderly generation then settles existence outright.
Details in [`enumerate/README.md`](enumerate/README.md).

**The upper bounds** came from simulated annealing over ±1 sign matrices, scored
by exact ternary-kernel size (millions of candidates over ~10 CPU-days). The
15×29 fell to annealing directly. The other two came from a cheaper trick — good
matrices contain smaller good ones: the 14×26 turned up inside a random
row/column slice of an already-solved 15×29, and the 13×24 came from
industrializing that observation, slicing many 13×23 children and scanning all
2¹³ candidate extension columns for each; two independent slices extended by the
same column. Deleting any column of a valid certificate keeps it valid, so the
15×29 also witnesses β(Q₂₇), β(Q₂₈) ≤ 15, the 14×26 gives β(Q₂₅) ≤ 14, and the
13×24 gives β(Q₂₃) ≤ 13 — matching (not beating) the published values there.

## Search code

- [`enumerate/`](enumerate/) — the exhaustive enumerator behind β(Q₁₄) = 9.
  It includes separate C and safe-Rust implementations plus a direct Python
  small-instance reference checker.
- [`search/`](search/) — the annealer and extension pipelines behind the upper
  bounds, plus a methods write-up in [`search/METHODS.md`](search/METHODS.md)
  that includes what did *not* work on the lower-bound side.

The certificates stand on their own: verification never touches the search code.

## References

- OEIS [A303735](https://oeis.org/A303735) — metric dimension of Q_n; exact
  values for n ≤ 13, with a(11)–a(13) contributed by V. S. Miller (2023).
- R. C. Read, *Every one a winner, or how to avoid isomorphism search*, Ann.
  Discrete Math. 2 (1978); I. A. Faradžev (1978) — orderly generation, the
  isomorph-rejection technique used by the enumerator.
- N. Mladenović, J. Kratica, V. Kovačević-Vujčić, M. Čangalović, *Variable neighborhood
  search for metric dimension and minimal doubly resolving set problems*, EJOR 220 (2012).
- N. Nikolić, M. Čangalović, I. Grujičić, *Symmetry properties of resolving sets and
  metric bases in hypercubes*, Optim. Lett. 11 (2017) — greedy bounds to n=22, then
  dynamic-programming bounds for 23 ≤ n ≤ 90.
- A. Hertz, *An IP-based swapping algorithm for the metric dimension and minimal doubly
  resolving set problems in hypercubes*, Optim. Lett. (2020).
- C. Lu, Q. Ye, *A bridge between the minimal doubly resolving set problem in (folded)
  hypercubes and the coin weighing problem*, Discrete Appl. Math. 309 (2022),
  [arXiv:2012.00396](https://arxiv.org/abs/2012.00396).
- S. Söderberg, H. S. Shapiro, *A combinatory detection problem*, Amer. Math. Monthly 70 (1963) 1066–1070 — foundational algebraic Kronecker product construction for detecting matrices and early bounds (including f(15) ≤ 9 and f(26) ≤ 15).
- R. K. Guy, R. J. Nowakowski, *Coin-Weighing Problems*, Amer. Math. Monthly 102 (1995) 164–167 — comprehensive survey of coin-weighing variants, exact-weight spring balance models, and historical bounds.
- P. Erdős, A. Rényi, *On two problems of information theory*, Publ. Math. Inst.
  Hungar. Acad. Sci. 8 (1963) — the coin-weighing problem and the constant M(n).
- D. G. Cantor, W. H. Mills, *Determination of a subset from certain combinatorial
  properties*, Canad. J. Math. 18 (1966) — the classical construction behind the
  n=30 riddle answer of 17 attempts.

## License

MIT
