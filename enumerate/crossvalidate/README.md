# Cross-validation against McKay's dissociated-set data (2014)

The enumerator's 8×13 output is checked against an independent dataset computed
by Brendan McKay in February 2014, by a different author, with different code,
in a different formulation, eight years before this project existed.

## The two formulations

A set `S ⊆ {0,1}^k` is **dissociated** when all `2^|S|` subset sums are
pairwise distinct; `D(k)` is the largest size of such a set. McKay computed
`D(k)` for `k ≤ 7` and published the extremal sets
([MathOverflow 157634](https://mathoverflow.net/q/157634)), conjecturing
`D(k) = ⌊½(k+1)log₂(k+1)⌋`.

Write `E(q)` for the largest `n` admitting a q×n detecting matrix, so
`β(Q_n) = min { q : E(q) ≥ n }`.

> **Proposition.** `E(q) ≥ D(q−1) + 1`.

*Proof.* Normalise row 0 of a detecting matrix to all +1 by column sign flips
(which preserve the detecting property, since `Wz = 0 ⟺ (WD)(Dz) = 0`). Every
column is then a point `c ∈ {0,1}^(q−1)`, and writing `w = 1 − 2c` the equation
`Wz = 0` becomes: `Σzᵢ = 0` from row 0, and `Σzᵢcᵢ = 0` from the rest. Given a
dissociated set `C′` of size `n−1`, take `C = {0} ∪ C′`. Any bad `z` restricted
to `C′` gives `Σyᵢc′ᵢ = 0`, so `y = 0` by dissociativity; then `Σz = z₀ = 0`, so
`z = 0`. Hence `C` is a detecting matrix of `n` columns. ∎

**The converse does not hold.** `{0} ∪ C′` is detecting exactly when no nonzero
`y ∈ {−1,0,1}^(n−1)` has `Σyᵢc′ᵢ = 0` **and** `|Σyᵢ| ≤ 1` — the bound on `|Σyᵢ|`
is forced because the coefficient `z₀` must itself lie in `{−1,0,1}`. That is
strictly weaker than dissociated, and `checkdiff.c` exhibits the gap explicitly.

Equality nevertheless holds at every computable point:

| q | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|
| E(q) | 3 | 5 | 6 | 8 | 10 | 13 |
| D(q−1) + 1 | 3 | 5 | 6 | 8 | 10 | 13 |

Whether `E(q) = D(q−1) + 1` in general is open.

## What the proposition buys

Since the 8×14 enumeration gives `E(8) = 13`, the proposition yields
`D(7) ≤ 12`. With McKay's explicit 12-element sets this re-derives
**`D(7) = 12`** from a computation sharing no code, no method and no author with
his — as far as we know, the first independent confirmation of that value.

Applied to the next case: a 9×16 nonexistence result would give `E(9) ≤ 15` and
hence `D(8) ≤ 14`, while `matrices/M14_le_8.txt` is already a dissociated
14-set in `{0,1}⁸`. Together those settle **`D(8) = 14`**, which McKay lists as
open and which his conjecture predicts (`⌊½·9·log₂9⌋ = 14`).

## The three checks

| program | what it establishes | result |
|---|---|---|
| `thm_check.c` | every McKay 12-set, adjoined with **0**, is a valid 8×13 detecting matrix | **118,485 / 118,485**, 0 failures |
| `reconcile.c` | canonicalise both sides under the same group (S₇ on the 7 bit positions) and compare as sets | all **118,485** of McKay's orbits occur among ours; **0** missing |
| `checkdiff.c` | deduplicate and re-test, by brute force over all 2¹² subset sums, every derived orbit *not* in McKay's file | **none** is dissociated — the gap is exactly the `|Σyᵢ| ≤ 1` slack |

`reconcile` reports 195,086 canonical forms on our side against McKay's 118,485.
The direction that matters for correctness is that nothing of his is missing:
had the enumerator dropped branches, orbits would be absent from our side. The
76,601 extra are accounted for in full by `checkdiff`.

## Reproducing

McKay's datasets are not redistributed here. Fetch `diff7_12.g6` from
[McKay's data page](https://users.cecs.anu.edu.au/~bdm/data/dissociated.html).
It holds the 118,485 extremal sets for `k = 7`. The complete comparison is one
command (about the same cost as a full 8×13 enumeration):

```sh
./run.sh /path/to/diff7_12.g6
```

`run.sh` decodes exactly 118,485 records, performs all ten 8×13 partitions,
requires exactly 108,865 emitted solutions, and makes every C checker fail
closed on missing, malformed, or incomplete input. `reconcile` tests the
one-way coverage relation; the 76,601 additional orbits are expected because
detecting sets satisfy a weaker condition than dissociated sets.

The complete output reproduced on 2026-08-09 is recorded in [`RESULT.md`](RESULT.md),
including the SHA-256 of the source dataset.

`decode2.py` recovers the bipartition by 2-colouring each component rather than
assuming the vertex order splits as (vectors, coordinates), which it does not.
