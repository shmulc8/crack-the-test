# New upper bounds for the metric dimension of hypercubes Q₂₆ and Q₂₉

Two explicit certificates improving the best published upper bounds on the metric
dimension β(Q_n) of the hypercube:

| n  | best published | this repo | certificate |
|----|----------------|-----------|-------------|
| 26 | 15 (Hertz 2020; Lu–Ye 2022) | **β(Q₂₆) ≤ 14** | [`matrices/beta_Q26_le_14.txt`](matrices/beta_Q26_le_14.txt) |
| 29 | 16 (Nikolić et al. 2017; Lu–Ye 2022) | **β(Q₂₉) ≤ 15** | [`matrices/beta_Q29_le_15.txt`](matrices/beta_Q29_le_15.txt) |

Equivalently, in riddle form: a score-only true/false test with 26 (resp. 29)
questions can be guaranteed perfect in **15** (resp. **16**) attempts — one fewer
than previously known. Interactive demo: **https://crack-the-test.netlify.app**

## Why a sign matrix is a certificate

**Lemma.** Let W be a q×n matrix with entries ±1 such that no nonzero
z ∈ {−1,0,1}ⁿ satisfies Wz = 0. Then the q vertices vᵢ = (1 − rowᵢ)/2 ∈ {0,1}ⁿ
form a resolving set of Q_n, hence β(Q_n) ≤ q.

*Proof.* For x, y ∈ {0,1}ⁿ, the Hamming distances satisfy
d(x, vᵢ) − d(y, vᵢ) = Σⱼ (xⱼ − yⱼ)(1 − 2vᵢⱼ) = rowᵢ · (x − y).
If x ≠ y have equal distance to every vᵢ, then z = x − y is a nonzero vector in
{−1,0,1}ⁿ with Wz = 0 — contradiction. ∎

So verifying each claim reduces to one finite check: **the matrix has no nonzero
ternary kernel vector**. The two matrices here pass that check exhaustively
(3¹⁵ ≈ 14.3M half-assignments, meet-in-the-middle over all 3ⁿ candidates).

## Verify it yourself

Two independent implementations, ~seconds each:

```sh
# JavaScript (bun or node >= 18)
bun verify.js matrices/beta_Q26_le_14.txt
bun verify.js matrices/beta_Q29_le_15.txt

# C
cc -O2 -o verify verify.c
./verify matrices/beta_Q26_le_14.txt
./verify matrices/beta_Q29_le_15.txt
```

Expected output ends with `VALID certificate: beta(Q_n) <= q`.
`./test.sh` runs both implementations on both matrices plus a negative control
(a deliberately broken matrix that must be rejected).

## How the matrices were found

Simulated annealing over ±1 sign matrices, scoring each candidate by the exact
size of its ternary kernel (meet-in-the-middle enumeration; millions of candidate
matrices over ~10 CPU-days). The 15×29 fell to annealing directly; the 14×26
turned up inside a random row/column slice of an already-solved 15×29. Both were
re-verified with independently written counters (the two in this repo reproduce
that check). Deleting any column of a valid certificate keeps it valid, so the
15×29 also witnesses β(Q₂₇) ≤ 15 and β(Q₂₈) ≤ 15, and the 14×26 gives
β(Q₂₄), β(Q₂₅) ≤ 14 — matching (not beating) the published values there.

## References

- OEIS [A303735](https://oeis.org/A303735) — metric dimension of Q_n (exact values, n ≤ 13).
- N. Mladenović, J. Kratica, V. Kovačević-Vujčić, M. Čangalović, *Variable neighborhood
  search for metric dimension and minimal doubly resolving set problems*, EJOR 220 (2012).
- J. Nikolić, et al., dynamic-programming bounds for β(Q_n) (2017).
- A. Hertz, *An IP-based swapping algorithm for the metric dimension and minimal doubly
  resolving set problems in hypercubes*, Optim. Lett. (2020).
- C. Lu, Q. Ye, *A bridge between the minimal doubly resolving set problem in (folded)
  hypercubes and the coin weighing problem*, Discrete Appl. Math. 309 (2022),
  [arXiv:2012.00396](https://arxiv.org/abs/2012.00396).
- D. G. Cantor, W. H. Mills, *Determination of a subset from certain combinatorial
  properties*, Canad. J. Math. 18 (1966) — the classical construction behind the
  n=30 riddle answer of 17 attempts.

## License

MIT
