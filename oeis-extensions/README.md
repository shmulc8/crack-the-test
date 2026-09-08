# Certified lattice diameters and toroidal queen constructions

Computational contributions for OEIS A386493 and A279404, September 2026.

**[A386493: concise result, picture, proof, and one-command verification](A386493/README.md)**

## A386493: a(15) = a(16) = 89

[Constructions and two exhaustive Rust verifiers](A386493/n15-n16/README.md)
establish the next two terms without SAT. Both complete exclusions and both
point sets can be replayed with a single Python command.

## A386493: a(13) = a(14) = 65

The sequence minimizes the squared diameter of n points in the square
lattice, subject to all distances from each selected point to the others
being distinct. This uses the definition in the
[OEIS comment](https://oeis.org/A386493), including collinear equal-distance
triples.

The 13- and 14-point constructions are in
[witness 13](A386493/runs/bool-n13-D65.json) and
[witness 14](A386493/runs/bool-n14-D65.json). Their actual squared diameters
are 65, and all apex distance lists have distinct entries.

For the lower bound, any configuration of squared diameter at most 64 has
coordinate spans at most 8. Translating the minima of both coordinates to
zero puts it inside the complete square {0,...,8}^2. Thus it suffices to
consider all 81 candidate points in that square; no symmetry assumption
is needed.

The [CNF generator](A386493/gen_cnf.py) uses one Boolean per candidate,
forbids any selected pair at squared distance greater than 64, and forbids
each selected triple with two equal distances from an apex. A sequential
counter requires at least 13 selected points. The resulting
[CNF](A386493/runs/n13-D64.cnf) contains 965 variables and 9,753 clauses.

Kissat returned UNSAT. DRAT-trim independently verified the certificate;
see the [solver log](A386493/runs/n13-D64.kissat.log),
[verification log](A386493/runs/n13-D64.drat-trim.log), and
[second verification](A386493/runs/publication-recheck.log).
This excludes every configuration of at least 13 points at squared
diameter <=64. Together with the 14-point construction at 65, it proves
both exact terms (a 13-point subset supplies the other upper bound).

The [gzip-compressed DRAT proof](A386493/runs/n13-D64.drat.gz) decompresses
to SHA-256
`a05e9a5529523574452457a45ad1740a556b6eb6907a4fd5b0d5bc4949f4fbec`.

## A279404: 11-queen constructions at n=19 and n=20

The [19x19 construction](A279404/logs/n19-k11.json) and
[20x20 construction](A279404/logs/n20-k11.json) each have 11 queens.
Coordinates are zero-based, modulo n. No two queens share a row, column,
sum diagonal, or difference diagonal. Every board cell shares at least
one of these four classes with a selected queen, so the placements are
independent dominating sets.

Therefore A279404(19)<=11 and A279404(20)<=11. The existing ordinary
domination lower bounds [A279402(19)=A279402(20)=10](https://oeis.org/A279402/b279402.txt)
also apply to independent domination. Both values are consequently in
[10,11]. This contribution supplies the upper-bound constructions; it
does not supply new lower-bound certificates or determine either exact term.

## Reproduce the checks

From this directory, using Python without -O or -OO:

```sh
python3 validate_results.py
gzip -dk A386493/runs/n13-D64.drat.gz
drat-trim A386493/runs/n13-D64.cnf A386493/runs/n13-D64.drat
```

The witness checker uses only Python's standard library. It checks the
geometric definitions directly and does not import any solver.

To regenerate the CNF, use python-sat 1.9.dev7:

```sh
python3 A386493/gen_cnf.py --n 13 --D 64 --out regenerated.cnf
cmp regenerated.cnf A386493/runs/n13-D64.cnf
kissat regenerated.cnf regenerated.drat
drat-trim regenerated.cnf regenerated.drat
```

The original native solver was Kissat 4.0.4. A separate finite Boolean
model using Z3 4.15.4 is included in `A386493/solve_bool.py`.
The at-least-13 CNF is sufficient for both certified terms; a separate
14-point exclusion is unnecessary.

Primary sequence definitions and prior data:
- https://oeis.org/A386493
- https://oeis.org/A279404
- https://oeis.org/A279402

Original investigations of the lattice problem, linked by OEIS:
https://www.ilemaths.net/sujet-points-acceptables-894126.html
