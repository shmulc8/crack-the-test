# Why `enum.c` is exhaustive

This note states the correctness argument for the computation
`beta(Q_14) = 9`. It is deliberately tied to the implementation in
[`enum.c`](enum.c): each optimization is either proved not to remove the last
representative of a solution orbit or is identified as an engineering check.

The decisive claim is finite and narrow:

> Ten completed runs of `enum 8 14 --maxsol 1 --split 10 --part p
> --splitdepth 6 --canondepth 8`, for `p = 0,...,9`, enumerate every normalized
> 8 by 14 detecting matrix up to the implemented symmetries. Since every run
> reports zero solutions, no such matrix exists.

This is a correctness argument for an exhaustive computation, not a formal
proof certificate. The independent checks at the end explain what has and has
not been verified by unrelated code and data.

## 1. Exact reduction

A `q` by `n` sign matrix `W` is detecting when

    W z != 0  for every nonzero z in {-1,0,1}^n.

For any `z`, let `A` contain its `+1` coordinates and `B` its `-1`
coordinates. Then `Wz = 0` exactly when the sum of the columns in `A` equals
the sum of the columns in `B`. Conversely, two equal subset sums give such a
ternary kernel vector after cancelling their intersection. Therefore:

> `W` is detecting if and only if all `2^n` subset sums of its columns are
> distinct.

Multiplying any column by `-1` is a bijection on ternary vectors, so it
preserves the kernel condition. Flip columns as necessary to make row 0 all
`+1`. Each column is now determined by its remaining `q-1` signs and is
encoded by a type in `0,...,2^(q-1)-1`; this is `NT` and `delta` in
[`main`](enum.c#L223-L255).

A detecting matrix cannot repeat a column: two equal columns give the kernel
vector `e_i-e_j`. Columns can therefore be treated as a set and sorted.
Finally, XORing every type by any selected type is the normalized form of
flipping lower rows and then choosing that selected column as type 0. Thus
every solution has an equivalent sorted representation containing type 0.
[`main`](enum.c#L265-L269) fixes that first type and starts with every larger
type as a candidate. No solution orbit is lost.

## 2. Complete depth-first traversal without pruning

At entry to [`dfs`](enum.c#L177-L220), `sol[0..depth-1]` is an increasing
prefix and `cand[depth]` contains larger types that have not already become
impossible.

Let `S` be the set of distinct subset sums of the prefix. Adding column `c`
produces exactly `S union (S+c)`. Since `S` is already collision-free, the
child is legal exactly when

    S intersect (S+c) is empty.

Lines [198-205](enum.c#L198-L205) test this condition. Lines
[208-218](enum.c#L208-L218) visit legal candidates in increasing order and pass
only the remaining suffix to the child. Consequently, with canonical and
partition pruning disabled, every legal sorted type set containing 0 is
visited exactly once.

The independent Python control in [`reference_check.py`](reference_check.py)
does not reproduce this DFS. It directly iterates over combinations, builds
tuple-valued subset sums, and compares the complete solution sets on tractable
instances.

## 3. Soundness of the ordinary pruning rules

### Monotone live candidates

If `c` is illegal for prefix `P`, there are `s1,s2` among the subset sums of
`P` with `s1=s2+c`. Both sums remain present for every superset of `P`, so `c`
can never become legal later. Removing it permanently at lines
[198-205](enum.c#L198-L205) is sound.

### Candidate-count lookahead

If fewer than `n-depth` legal larger candidates remain, the prefix cannot be
extended to `n` columns. The checks at lines [187](enum.c#L187) and
[206](enum.c#L206), and the loop cutoff at line [209](enum.c#L209), remove only
such prefixes.

### Hash table

The hash table is only an implementation of membership in `S`; collisions use
linear probing and keys are compared for equality at lines
[85-100](enum.c#L85-L100). Generation stamps logically clear a table between
nodes. A full table could make probing nonterminating, so line
[189](enum.c#L189) aborts before capacity is reached. In the decisive `n=14`
run the largest table built has only `2^13 = 8192` entries, versus capacity
`2^17 = 131072`.

## 4. Soundness of canonical-prefix pruning

After row 0 is normalized, the implemented group consists of:

1. permutations of the lower `q-1` rows; and
2. XOR translation of all types, followed by retaining a representation that
   contains type 0.

For a set already containing 0, every translated representation containing 0
is obtained by XORing with one of its members. This explains the outer loop
over `m = cur[a]` in [`canon_ok`](enum.c#L132-L168). `build_perms` enumerates
all `(q-1)!` lower-row permutations. Sorting each image accounts for arbitrary
column order. These operations preserve detectingness.

`canon_ok` rejects a prefix only when some group image is lexicographically
smaller. Why is it safe to canonicalize a prefix before seeing the suffix?
Let `A` be the first `k` elements of a sorted full set `X`. If a group element
makes sorted `g(A)` lexicographically smaller than `A`, the first `k` elements
of sorted `g(X)` are componentwise no larger than sorted `g(A)`, because
`g(A)` is a subset of `g(X)`. Hence `g(X) < X`. A lexicographically least
member of a full orbit therefore has lexicographically least prefixes.

It follows that pruning noncanonical prefixes cannot remove every member of a
solution orbit. The popcount precheck at lines [135-151](enum.c#L135-L151)
does not reject anything: it only skips permutations when a lower bound on
their sorted image is already not smaller than the current prefix.

The decisive run canonicalizes only through depth 8. Stopping there can leave
duplicate work, but cannot lose a solution.

The independent control computes whole-set canonical forms by brute force,
without prefix pruning, and checks that the C program emits exactly those
representatives for the complete small `5x6` instance.

### Optional row pivoting (`--pivots`)

`--pivots` enlarges the canonicalization group from the row-0 stabilizer above
to the full signed row group `O(q,Z) = (Z_2)^q x| S_q`, by additionally
allowing any row `R` to be pivoted into the row-0 position
([`pivottab`](enum.c#L168-L185), applied in `canon_ok`). Every added map is a
signed row permutation, which preserves detectingness, so the enlargement only
strengthens pruning and cannot lose a solution orbit. Its soundness and
completeness are checked directly: `reference_check.py` computes the `O(q,Z)`
whole-set orbit representatives by brute force and confirms that `enum --pivots`
emits exactly that set for the complete `3x4`, `4x4`, and `5x6` instances.

The flag is left off the decisive `beta(Q14)`/`beta(Q15)` runs by choice, not
distrust: those verdicts are already reachable with the smaller stabilizer and
are cross-checked by the independent Rust enumerator, which implements no
pivoting. Keeping the headline results on the minimal-symmetry path means their
soundness rides on the simplest canonicalization and stays reproducible by a
second, independent implementation. Row pivoting earns its place on the open
cases where the baseline does not finish in reach -- such as the `q=9, n=16`
frontier sampling -- and there the same-orbit guarantee above is what lets us
trust its verdict.

## 5. Packed subset sums are exact for this run

Each of the `q` coordinates occupies a fixed-width field of a `uint64_t`. The
field width is eight bits for `q<=8` and seven bits for `q=9`, chosen at
[enum.c#L350](enum.c#L350) so all `q` fields fit: `9*7 = 63 <= 64`. The empty
sum starts at bias 64 in every field; each column contributes `+1` or `-1` to
each coordinate, so every subset sum keeps each coordinate in `[64-n, 64+n]`.

For `n<=20` that interval is `[44, 84]`, which lies inside both `[0, 255]`
(eight-bit fields) and `[0, 127]` (seven-bit fields). No coordinate ever
reaches its field boundary, so ordinary 64-bit addition is exactly
componentwise addition with no inter-field carry or borrow. The decisive
`beta(Q14)`/`beta(Q15)` cases have `q=9`: nine seven-bit fields, coordinates in
`[49, 79]` and `[48, 80]`; the `q=9, n=16` frontier stays in `[48, 80]`.

The array has space for all `2^n` sums. A child writes its translated half at
`sums[count..2*count-1]` on lines [214-215](enum.c#L214-L215); recursive calls
write only beyond their own prefix, so returning to a sibling leaves the
parent's first `count` sums unchanged.

## 6. The ten partitions are disjoint and complete

Splitting happens only when `depth == split_depth`, at line
[211](enum.c#L211). Every process performs the identical deterministic search
above that depth. For every outgoing candidate encountered there, each
process increments the same zero-based `split_counter`. Part `p` retains the
candidate exactly when

    split_counter mod nsplit == p.

Every integer has exactly one residue modulo `nsplit`; therefore each outgoing
branch is assigned to exactly one part. Assignment occurs before canonical
testing of the child. A noncanonical child is soundly rejected by its assigned
part; a canonical child is explored by exactly that part.

This argument depends on all processes reaching the same split frontier. The
recorded node counts through depth 6 are identical:

    0, 1, 6, 18, 143, 1082, 11364

[`check_partition_logs.py`](check_partition_logs.py) requires that prefix,
requires exactly parts 0 through 9, rejects malformed or duplicate logs, and
requires a clean zero-solution completion from each. On a smaller complete
instance, `reference_check.py` also verifies that split outputs are pairwise
disjoint and their union equals the independently computed solution set.

## 7. Termination and the negative verdict

`dfs` returns early only after reaching `maxsol`. For the decisive case no
partition finds a solution, so that early return is never taken. Invalid
arguments, allocation failures, and hash-capacity failures terminate with a
nonzero exit rather than printing a completed negative verdict.

Each successful process reaches `DONE` and prints `solutions found: 0` plus its
partition-specific terminal line. A global nonexistence conclusion is drawn
only after all ten processes exit successfully and their logs pass the checks.
[`run_8x14_audit.sh`](run_8x14_audit.sh) performs that workflow and preserves
the source commit, source hash, environment, logs, and log hashes in a new
output directory that it refuses to overwrite.

## 8. Verification map and remaining limitation

| Claim | Evidence |
|---|---|
| Algebraic reduction | Argument in section 1; independent certificate verifiers use the same mathematical criterion |
| Raw DFS completeness | Exact complete-set comparison with direct Python combinations on `3x4`, `4x4`, `5x6` |
| Canonical pruning | Exact comparison with independently computed whole-orbit representatives on `5x6` |
| Partition coverage | Proof in section 6; disjoint-union comparison on `5x6`; checked ten-part logs for `8x14` |
| Adjacent large case | Complete comparison of `8x13` output with Brendan McKay's 118,485 independent dissociated-set classes |
| Decisive result | Ten completed C partitions and ten completed safe-Rust partitions, all with zero solutions and exact per-part node-vector agreement |

Run the fast independent controls with:

```sh
cc -O2 -Wall -Wextra -Wpedantic -o enum enum.c
python3 reference_check.py ./enum
```

Create a persistent decisive-run bundle with:

```sh
./run_8x14_audit.sh audit-8x14-YYYYMMDD
```

The remaining limitation is explicit: the final `8x14` nonexistence result now
has full C and safe-Rust implementations, but both implement the same orderly
generation method and were developed within the same project. This is much
stronger evidence against language-specific or memory-safety defects, especially
because all ten complete node vectors agree, but it is not an unrelated author's
enumeration or a compact formal proof object. An external implementation or a
checkable UNSAT proof would strengthen the result further; neither is assumed by
this correctness argument.
