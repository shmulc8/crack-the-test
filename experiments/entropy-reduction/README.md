# Exact entropy and dimension-reduction experiment

This is an independent prototype, separate from the paper's existing enumerator and from Victor Miller's code. It produces checkable proofs on smaller cases. **It has not proved 8x14 or reproduced the reported 29-second method.**

## New: certified linear-dependency reduction

Enable with `--linear`. For any nonzero integer coefficient vector a on the
already selected sign rows, collect the columns where a dot column = 0.
On this block, one selected row is a linear combination of the others and
can be deleted without losing detection. Therefore the block has at most
E(q-1) columns. A larger block is a sound contradiction.

The generator currently searches signed relations involving **four rows**,
including the most recently added row, before the final depth. This is a
bounded search for linear dependencies, not enumeration of all possible
dependencies. Testing only new relations is sufficient for this pruning
policy because ancestors tested the earlier ones. Skipping a relation only
misses a pruning opportunity; it cannot invalidate a negative result.

The certificate stores the coefficients. The independent checker recomputes
the zero block using exact integer arithmetic, verifies its size against a
proved capacity premise, and accepts arbitrary integer coefficients without
trusting the generator's coefficient search or cached tables. Zero vectors
and false equations are rejected.

Concrete example from the 5x7 proof: profile `[1,2,2,0,2,0,0,0]` has six
columns satisfying `R0-R1-R2-R3=0`. Deleting one dependent row on that block
would give a 4x6 detecting matrix, contradicting the already checked E(4)<=5.

Fresh paired 6x9 runs (same code, exact integer collision encoding):

| Mode | States | Linear rejections | Elapsed seconds |
|---|---:|---:|---:|
| Baseline | 41,007 | 0 | 1.721 |
| `--linear` | 33,276 | 331 | 1.320 |

This is 18.9% fewer states and about 23% less elapsed time in that paired run.
Both complete certificates passed the separate checker. Timings are local
measurements, not a controlled comparison with Victor or the C enumerator.
A 60-second 7x11 run still returned UNKNOWN (506,315 visited states, 1,030
linear rejections). A 30-second 8x14 run also returned UNKNOWN (108,314
visited states, 73 linear rejections), conditional on the existing E(7)<=10
bound. These runs do not demonstrate a speedup on the larger cases.
See `results/linear-*.json.gz`, `results/check-linear.log`, and
`results/tests-linear.log`. Ten tests pass, including complete small-instance
comparisons, positive controls, and corrupted/scaled linear witnesses.

## What works

- Complete, separately checked nonexistence certificate chain: **3x4, 4x6, 5x7, 6x9**. This establishes capacity upper bounds E(3)<=3, E(4)<=5, E(5)<=6, E(6)<=8 without using the existing C search.
- The exact fixed-weight entropy bound alone closes 3x4.
- Row splitting plus smaller-dimension bounds closes the other cases. A row-pair refinement reduced the 6x9 search from 109,451 to 41,007 states (about 6.71 to 2.43 seconds in the recorded Python runs).
- A separate checker verifies every branch and collision witness. It refuses unsupported smaller-dimension premises. No search code is imported by the checker.
- Ten tests cover 18 complete small existence decisions against raw enumeration, larger positive witnesses, exact entropy equality, the distinction between balanced and unrestricted subset-sum collisions, budget exhaustion, and damaged certificates.

## Current limitations and measured decision

- 7x11: still UNKNOWN after a 60-second, 530,131-state bounded run. The smaller 6x9 improvement is not evidence of competitiveness with the existing C enumerator.
- 8x14: still UNKNOWN after a 20,000-state budget. This exploratory run assumes E(7)<=10 from the existing work; that premise has **not** been independently derived by this new prototype. The checker would refuse it without a checked 7x11 certificate.
- Using E(7)<=10 reduces the admissible 8x14 row weights to 4..7, giving 120 multisets. All 120 pass the basic exact entropy filter. Repeating or optimizing this filter will not settle 8x14.
- The new conditional-entropy probe rejects 0/4 sampled prefixes at depth 3, 0/4 at depth 4, and **2/24 at depth 5** (two rows remaining). All 24 had admissible candidate rows; the two rejections really use entropy. The 24 evaluations took about 10.73 seconds. These are bounded, biased exploratory samples, not an estimated global pruning rate.
- Conditional entropy is a research probe, not yet a rule accepted in the certificate format. It preserves tested prefixes of known positive matrices. It needs stronger validation and an end-to-end speed comparison before integration.

Assessment: the certificate framework and dimension reduction are productive. The current search is too weak for the target, and the measured conditional bound does not yet establish a substantial improvement. The four-row linear rule above provides a modest verified improvement. Multiple independent dependencies on the same block, larger-support relations, and tighter joint information bounds remain untested directions. Do not claim an 8x14 result from any of these bounded runs.

## Reduction: search over column groups

Let E(q) be the largest number of columns of a detecting q-row sign matrix. Always E(q)<=2^(q-1), since normalized columns must be distinct.

Normalize the first row to all +1. After choosing r further rows, columns fall into 2^r groups with identical signatures on those rows. Store only group multiplicities, not labelled columns. A new row splits group size c into c-a and a, for each a in 0..c. Within-group column permutations make these counts exhaustive.

Within one group, the first r+1 rows are identical up to sign. Delete r redundant rows. The restricted block must remain detecting, so **every group has size at most E(q-r)**. This is the smaller-dimension reduction; it is necessary, not sufficient.

For any pair of rows, the agreeing and disagreeing columns likewise form blocks with one redundant row. Both sizes must be at most E(q-1). This applies to every chosen pair, not just pairs involving the normalized row.

Complement each binary row so its weight is at most floor(n/2), and order rows by weight. These operations preserve detection. Any redundant constant row may be replaced by a nonconstant row without losing information, so nonzero weights suffice for the existence search. When a new row has exactly half the weight, its complementary split has the same weight and equivalent detection; keep one lexicographic orientation.

## Exact entropy: no floating-point decisions

On the layer of s-element subsets, there are N=C(n,s) equiprobable inputs. A row of weight d has intersection-count fibers

    a_k = C(d,k) C(n-d,s-k).
    P(d,s) = product_k a_k ** a_k.

For m=q-1 rows, entropy subadditivity requires

    product_i P(d_i,s) <= N ** ((m-1)*N).

The generator and checker compare these integers exactly. Equality is accepted. The checker independently constructs fiber counts by enumerating actual subsets rather than using the generator's hypergeometric formula.

For example, 3x4 forces both binary row weights to be 2. On the s=2 layer, N=6 and fibers have sizes 1,4,1. The necessary inequality fails: 256^2=65,536 > 6^6=46,656. This is a short entropy certificate of nonexistence.

## Conditional-entropy probe

At a fixed prefix, let P be the product f^f over its fiber sizes in one subset layer. For each admissible future row, refine those fibers and compute the corresponding product Q. Let Q_min be the smallest such product and t the number of rows still available.

By conditional subadditivity, a necessary condition is

    Q_min ** t <= P ** (t-1).

Proof: the unresolved information is log(P)/N, and every future row supplies at most log(P/Q_min)/N bits conditional on the fixed prefix. This maximization considers every row that could occur later, not just the next row in a particular sorted weight completion. Integer comparison determines the verdict; floating-point bit counts appear only in diagnostic output.

## Reproduce

Python 3.10+; standard library only. From this directory:

```sh
python3 -m unittest -v test_reduce
python3 check.py results/3x4.json results/4x6.json results/5x7.json results/6x9-pairs.json.gz
python3 reduce.py 6 9 --bounds '{"3":3,"4":5,"5":6}' --output /tmp/new-6x9.json.gz
python3 reduce.py 6 9 --bounds '{"3":3,"4":5,"5":6}' --linear --output /tmp/new-linear-6x9.json.gz
python3 check.py results/3x4.json results/4x6.json results/5x7.json /tmp/new-linear-6x9.json.gz
```

The bounds supplied to the search are premises. A standalone `UNSAT` JSON is not accepted as a proof until its complete lower-row certificate chain passes `check.py`. `UNKNOWN` carries no proof and exits with status 2. Search budgets are checked at state visits, not enforced as hard process timeouts.

The checker has five local rules: group capacity, entropy infeasibility, row-pair capacity, linear-dependency capacity, and an explicit balanced ternary kernel vector. Its branch rule independently enumerates every split, including checks for all discarded alternatives. The leaf collision routine retains cardinality, so equal sums of unequal-size binary subsets are never falsely treated as sign-matrix collisions.
