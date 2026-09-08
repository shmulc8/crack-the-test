# A386493: a(13..16) = 65, 65, 89, 89

A reproducible exhaustive computational proof for four terms of
[OEIS A386493](https://oeis.org/A386493). Computation: September 8, 2026.

The problem is to minimize the squared diameter of a set of integer lattice
points such that, at every selected point, its distances to all other selected
points are different. This excludes collinear midpoint triples as well as
ordinary isosceles triangles.

## Result

| Number of points | Minimum squared diameter |
|---:|---:|
| 13 | 65 |
| 14 | 65 |
| 15 | 89 |
| 16 | 89 |

## Upper bounds: explicit constructions

The 14-point construction, of squared diameter 65, is

```
(1,2), (1,3), (1,5), (1,6), (4,0), (4,1), (4,7), (4,8),
(7,1), (7,7), (8,2), (8,3), (8,5), (8,6).
```

The 16-point construction, of squared diameter 89, is

```
(8,3), (7,0), (1,5), (1,6), (4,0), (8,2), (4,8), (8,5),
(2,0), (5,0), (2,8), (1,2), (1,3), (8,6), (7,8), (5,8).
```

Deleting the final point gives the 13- and 15-point constructions. All four
are in `witnesses.json`. The verifier checks distinct integer coordinates,
the exact diameter, every apex's distance list, and every triple.

## Lower bounds: exhaustive exclusions

For squared diameter at most D, each coordinate span is at most floor(sqrt(D)).
Translating both coordinate minima to zero therefore places every possible
configuration in the complete square `{0,...,floor(sqrt(D))}^2`.

The programs enumerate increasing-index subsets of this entire domain; no
additional symmetry restriction is imposed. A chosen point eliminates all
future points too far from it and all future points that would form a forbidden
triple with it and an earlier selected point. Each feasible subset occurs in
the search. Branches with too few remaining candidates cannot contain a solution.

`exact_search.rs` also uses a proper graph-coloring upper bound. The graph
connects pairs of remaining candidates that can coexist with the selected
prefix. Each color class consists of mutually incompatible candidates, so a
completion uses at most one point per color.

| Program | Excluded configuration | Nodes visited |
|---|---|---:|
| `exact_search.rs` | 13 points, D <= 64 | 789,000 |
| `exact_search.rs` | 15 points, D <= 85 | 11,736,134 |
| `independent85.rs` | 15 points, D <= 85 | 46,676,991 |

The independent D=85 program uses candidate-count pruning only, with no
coloring bound, and constructs the forbidden triples by separately testing
all three apex positions. All three searches completed exhaustive exclusions.
The programs distinguish timeout from a completed exclusion.

The D=64 exclusion gives a lower bound of 65 for 13 points and hence for
14 points. The D=85 exclusion also covers 16 points by taking a 15-point
subset. None of 86, 87, or 88 is a sum of two integer squares, so there is no
possible squared lattice diameter between 85 and 89. Consequently, 89 is the
lower bound for both 15 and 16 points. The constructions attain these bounds.

## Reproduce the complete result

From the repository root, with Python 3.9+ and Rust installed, run:

```sh
python3 oeis-extensions/A386493/verification/verify.py
```

No Python packages or SAT solver are required. The script compiles both
Rust programs, runs the three complete exclusions, checks the deterministic
node counts, validates the four constructions, and writes `verification.json`.
The source programs perform exact integer arithmetic. Reported runtimes are
machine-dependent; an interrupted or timed-out run cannot establish a bound.

This is an exhaustive computational argument, not a proof-assistant certificate.
An additional independently checked SAT/DRAT certificate for the D=64
exclusion is available in the
[original evidence repository](https://github.com/shmulc8/crack-the-test/tree/dcb886fd614e3f5b996cb74f7e7069747b71d79e/oeis-extensions).
It is supplementary: the complete non-SAT replay above stands on its own.
