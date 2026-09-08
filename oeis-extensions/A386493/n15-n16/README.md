# A386493: a(15) = a(16) = 89

Exact computational result, independently reproduced without SAT.

The problem asks for the smallest squared diameter of n integer lattice
points such that, from any selected point, the distances to the other
selected points are all different. Collinear midpoint triples are forbidden
as well as ordinary isosceles triangles, matching the OEIS definition.

## Construction

The following 16 points have squared diameter 89:

```
(8,3), (7,0), (1,5), (1,6), (4,0), (8,2), (4,8), (8,5),
(2,0), (5,0), (2,8), (1,2), (1,3), (8,6), (7,8), (5,8)
```

All 120 pair distances and all 560 triples were checked with exact integer
arithmetic. At each point, the 15 distances to other points are distinct.
Deleting the final point gives the separately checked 15-point construction,
also of squared diameter 89 (105 pairs and 455 triples).

Files: `local-n16-D89.json`, `local-D89-seed3864931503.json`,
`witness16-D89-validation.json`, `witness15-D89-validation.json`.

## Why no smaller diameter works

Any lattice configuration with squared diameter at most 85 has coordinate
spans at most floor(sqrt(85)) = 9. Translating its coordinate minima to zero
puts it inside the full 10-by-10 grid, with no loss of generality.

Two separate Rust programs exhaustively searched for 15 points in that grid.
They enforce every diameter-incompatible pair and every forbidden triple.
Both enumerate subsets in index order without imposing symmetry restrictions.

| Program | Pruning | Visited nodes | Result |
|---|---|---:|---|
| `exact_search.rs` | Candidate count and proper graph coloring | 11,736,134 | Exhaustive exclusion |
| `review-independent.rs` | Candidate count only | 46,676,991 | Exhaustive exclusion |

The independent program constructs triple violations by explicitly testing
each possible apex against an independently built squared-distance matrix.
It does not use the primary program's coloring bound. Tiny-domain exhaustive tests, known-term regressions, and independent code review also passed.

Squared lattice distances are sums of two integer squares. None of 86, 87,
or 88 has this form. Therefore no 15-point configuration has squared diameter
less than 89. The exclusion also covers 16 points, because any 16-point
configuration contains a 15-point subset. Combined with the constructions,
this gives **a(15) = a(16) = 89**.

This is an exhaustive computational argument supported by two implementations
and replayed runs; it does not use a SAT solver or claim a formal proof-assistant
certificate.

## Reproduce

From this directory, with Rust and Python installed:

```sh
python3 verify_result.py
```

The script compiles both exhaustive programs into a temporary directory,
reruns the full D=85 exclusions, checks their complete deterministic node
counts, and independently validates both point sets. No third-party Python
packages are required. Use `--witnesses-only` to check just the constructions.
The full replay is saved in `root-final-verification.json`; source and artifact
hashes are listed in `SHA256SUMS`.

## Source and computation

Problem definition: [OEIS A386493](https://oeis.org/A386493).
Computation and verification: September 8, 2026. The construction was found
by randomized local search; the exact lower bound comes from the two exhaustive
programs supplied here.
