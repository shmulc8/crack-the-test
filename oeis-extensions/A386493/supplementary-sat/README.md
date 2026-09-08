# Supplementary SAT certificate for a(13) = a(14) = 65

The [main proof](../PROOF.md) verifies all four terms without SAT. This directory
retains the original independent SAT/DRAT evidence.

The sequence minimizes the squared diameter of n points in the square
lattice, subject to all distances from each selected point to the others
being distinct. This uses the definition in the
[OEIS comment](https://oeis.org/A386493), including collinear equal-distance
triples.

The 13- and 14-point constructions are in
[witness 13](runs/bool-n13-D65.json) and
[witness 14](runs/bool-n14-D65.json). Their actual squared diameters
are 65, and all apex distance lists have distinct entries.

For the lower bound, any configuration of squared diameter at most 64 has
coordinate spans at most 8. Translating the minima of both coordinates to
zero puts it inside the complete square {0,...,8}^2. Thus it suffices to
consider all 81 candidate points in that square; no symmetry assumption
is needed.

The [CNF generator](gen_cnf.py) uses one Boolean per candidate,
forbids any selected pair at squared distance greater than 64, and forbids
each selected triple with two equal distances from an apex. A sequential
counter requires at least 13 selected points. The resulting
[CNF](runs/n13-D64.cnf) contains 965 variables and 9,753 clauses.

Kissat returned UNSAT. DRAT-trim independently verified the certificate;
see the [solver log](runs/n13-D64.kissat.log),
[verification log](runs/n13-D64.drat-trim.log), and
[second verification](runs/publication-recheck.log).
This excludes every configuration of at least 13 points at squared
diameter <=64. Together with the 14-point construction at 65, it proves
both exact terms (a 13-point subset supplies the other upper bound).

The [gzip-compressed DRAT proof](runs/n13-D64.drat.gz) decompresses
to SHA-256
`a05e9a5529523574452457a45ad1740a556b6eb6907a4fd5b0d5bc4949f4fbec`.

## Reproduce

From this directory, with DRAT-trim installed:

```sh
gzip -dc runs/n13-D64.drat.gz > /tmp/a386493-n13-D64.drat
drat-trim runs/n13-D64.cnf /tmp/a386493-n13-D64.drat
```

To regenerate the CNF, use python-sat 1.9.dev7:

```sh
python3 gen_cnf.py --n 13 --D 64 --out regenerated.cnf
cmp regenerated.cnf runs/n13-D64.cnf
kissat regenerated.cnf regenerated.drat
drat-trim regenerated.cnf regenerated.drat
```

The original native solver was Kissat 4.0.4. A separate finite Boolean
model using Z3 4.15.4 is included in `solve_bool.py`.
The at-least-13 CNF is sufficient for both certified terms; a separate
14-point exclusion is unnecessary.

