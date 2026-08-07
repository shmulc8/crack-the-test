# β(Q₁₄) = 9 — exhaustive verification

The metric dimension of the 14-dimensional hypercube is **9**.

[OEIS A303735](https://oeis.org/A303735) lists the metric dimension of Qₙ for
n = 1…13 (`1,2,3,4,4,5,6,6,7,7,8,8,8`) and is tagged `hard,more`; a(14) was not
known. Mladenović, Kratica, Kovačević-Vujčić and Čangalović
([EJOR 220:328–337, 2012](https://doi.org/10.1016/j.ejor.2012.02.019))
*conjectured* 9 for n = 14 from an approximation algorithm. This is a proof.

## What is computed

A **q×n detecting matrix** has entries in {+1,−1} and no nonzero ternary vector
in its kernel: no `z ∈ {−1,0,+1}ⁿ`, `z ≠ 0`, with `Wz = 0`. Such a matrix
exists exactly when n coordinates can be resolved by q queries, so

> β(Qₙ) = min { q : a q×n detecting matrix exists }.

`enum.c` decides existence exhaustively. Results:

| instance | verdict | time |
|---|---|---|
| 7×11, 7×12, 7×13, 7×14 | no matrix exists | ~1 s each |
| 8×11, 8×12, 8×13 | matrix exists | instant |
| **8×14** | **no matrix exists** | 9.5 min on 10 cores |

The first two rows give β(Q₁₁) = β(Q₁₂) = β(Q₁₃) = 8, matching A303735 exactly —
those terms were computed independently by Victor S. Miller in 2023 with the RC2
MaxSAT solver. The third row gives **β(Q₁₄) = 9**, since 7×14 also fails.

Two corollaries: **β(Q₁₅) = 9** (deleting a column from an 8×15 matrix would
leave an 8×14 one, so none exists; a 9-element resolving set for n = 15 is
already known) and **M(14) = 8** for the Erdős–Rényi coin-weighing constant.

## Method

Normalise row 0 to all +1 by flipping column signs. Every column is then one of
2^(q−1) *types* — a ±1 vector whose first entry is +1 — and

> W is detecting ⟺ the 2ⁿ subset sums of its columns are pairwise distinct.

(The row-0 coordinate contributes the subset size, so only equal-sized subsets
can collide.) The search is a depth-first walk over n-subsets of the type set in
increasing order. Adding a column `c` to a set whose subset-sum set is `S` is
legal iff `(S + c) ∩ S = ∅`, one hash probe per existing sum.

Three things make it fast:

- **Orderly generation** (Read 1978, Faradžev 1978). The group permuting and
  sign-flipping rows 1…q−1 has order (q−1)!·2^(q−1) — 645,120 for q = 8. Any
  partial set that is not lexicographically least in its orbit is rejected. This
  is sound because a lex-least set has lex-least prefixes: if some group element
  made a prefix smaller it would make the whole set smaller too.
- **Monotone candidate lists.** A type that cannot be added to a set can never
  be added to a superset, so each node filters its parent's live list once. When
  fewer live candidates remain than columns still needed, the subtree is dead.
- **Packed sums.** A subset sum is stored in one 64-bit word, 8 bits per
  coordinate, biased so no field carries into its neighbour; adding a column is
  a single 64-bit addition.

On 7×11 these reduce the search from 256,123,828 nodes / 107 s to
189,831 nodes / 1.75 s.

The technique is classical; the new value of a(14) is the result.

## Reproducing

```sh
./ladder.sh                       # every published term, plus 8x14
cc -O3 -o enum enum.c
./enum 7 11 --maxsol 1            # ~2 s   -> no matrix exists
./enum 8 13 --maxsol 1            # instant -> matrix exists
# 8x14, split across 10 cores (~10 min):
for p in $(seq 0 9); do
  ./enum 8 14 --maxsol 1 --split 10 --part $p --splitdepth 6 --canondepth 8 &
done; wait
```

Each part prints its node counts per depth. The counts down to the split depth
are identical across parts, which is what a coherent partition looks like; below
it the parts are disjoint. All ten report `solutions found: 0`.

## Independent checks

- The identical machinery, same flags, **does** find matrices for 8×11, 8×12 and
  8×13 in every part — so the work-splitting is not silently dropping branches.
- β(Q₁₁), β(Q₁₂), β(Q₁₃) reproduce A303735, i.e. an outside computation by a
  different author using a different method (MaxSAT).
- `verify_extensions.py` takes a different route entirely: deleting a column
  from an 8×14 detecting matrix leaves an 8×13 one, so if every 8×13 matrix
  admits no 14th column then no 8×14 exists. It rebuilds each matrix from
  scratch in Python, re-verifies it is detecting, and tries all 128 possible
  columns. Sampled 8×13 matrices are all detecting and none extends.
