# The metric dimension of hypercubes: β(Q₁₄) = 9, and new upper bounds for Q₂₄, Q₂₆, Q₂₉

Two kinds of result on the metric dimension β(Q_n) of the hypercube, both with
machine-checkable certificates.

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
| M(14) = 8 | Erdős–Rényi coin-weighing constant, via the Lu–Ye bridge |

β(Q₁₅) ≥ 9 follows because deleting a column from an 8×15 detecting matrix would
leave an 8×14 one, so no 8×15 exists either. The matching upper bound is
[`matrices/beta_Q15_le_9.txt`](matrices/beta_Q15_le_9.txt), a 9×15 detecting
matrix found here and checkable in seconds — so both halves of β(Q₁₅) = 9 are
self-contained rather than resting on a published resolving set.

Code, method and reproduction instructions: [`enumerate/`](enumerate/). The
search also reproduces β(Q₁₁) = β(Q₁₂) = β(Q₁₃) = 8 in about a second each,
agreeing with Miller's independent MaxSAT computation — which is the strongest
correctness evidence available, since the two methods share nothing.

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
certified by exhibiting one, and a *lower* bound is certified by proving none
exists at that size. Hence β(Q_n) = min { q : a q×n detecting matrix exists },
which is exactly what [`enumerate/`](enumerate/) decides.

## Verify it yourself

Every upper-bound certificate in `matrices/` reduces to one finite check — the
matrix has no nonzero ternary kernel vector — done exhaustively by
meet-in-the-middle over all 3ⁿ candidates (≈14.3M half-assignments at q=15). Two
independent implementations, seconds each:

```sh
# JavaScript (bun or node >= 18)
bun verify.js matrices/beta_Q24_le_13.txt

# C
cc -O2 -o verify verify.c
./verify matrices/beta_Q24_le_13.txt
```

Expected output ends with `VALID certificate: beta(Q_n) <= q`.
`./test.sh` runs both implementations on all three matrices plus a negative
control (a deliberately broken matrix that must be rejected).

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
- P. Erdős, A. Rényi, *On two problems of information theory*, Publ. Math. Inst.
  Hungar. Acad. Sci. 8 (1963) — the coin-weighing problem and the constant M(n).
- D. G. Cantor, W. H. Mills, *Determination of a subset from certain combinatorial
  properties*, Canad. J. Math. 18 (1966) — the classical construction behind the
  n=30 riddle answer of 17 attempts.

## License

MIT
