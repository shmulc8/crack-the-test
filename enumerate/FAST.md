# Fast search: full-depth isomorph rejection and a clique bound

`fast/` (Rust, rayon) and `enum_fast.c` (C) run the same search as `enum.c`:
row 0 normalised to all +1, columns as 2^(q−1) types, strictly increasing type
sequences, a column legal iff it is not a ternary combination of the chosen
ones. Three changes make it fast. Each is a pruning or a data-structure change
that keeps the search exhaustive.

## 1. Lex-min test at every depth, by minimal-image search

`enum.c` tests lex-minimality by looping over all (q−1)! bit permutations for
each translation, so it can only afford the test to depth 8. Below that depth,
prefixes with large stabilisers repeat as isomorphic copies.

`canon_fast` computes the same verdict with a minimal-image partition backtrack
(in the spirit of Linton's smallest-image algorithm). After translating some
element to 0, the remaining freedom is a bit permutation. This is kept as a list
of cells (A → B): input bits A map bijectively onto output bits B. The least
value an unused element x can reach is, per cell, the |x ∩ A| lowest bits of B.
The next point of the minimal image is the least such value, and it is reached
only when every cell sends x's bits onto those lowest bits. So the search
branches only on elements that tie for that value, and stops as soon as the
image drops below or rises above the tested set.

`enum_fast --check-canon` runs both tests on every node and aborts on any
disagreement. They agree at every node of 6×9, 7×11 and 7×12 (and 6×9 with
pivots).

## 2. Compatibility-graph clique bound

At a node with chosen set S, every two of the n − |S| columns still needed must
be compatible: b stays legal after adding a, i.e. a + b ∉ T(S) and a − b ∉ T(S),
where T(S) is the set of ternary combinations of S. The node's live candidates
form a graph under this relation. If it has no clique of size n − |S|, the node
is dead. This is decided exactly by Tomita-style branch and bound with greedy
colouring bounds on 256-bit adjacency sets. A child's candidate list is its row
of the graph, so the children's own filtering is skipped.

## 3. Meet-in-the-middle membership in T(S)

T(S) = T(P) + T(R) for the first `anchor` columns P and the rest R. The engine
hashes T(P) once per depth-`anchor` node (at most 3^anchor entries) and keeps
T(R) as a list. Then v ∈ T(S) iff v − r is in the hash for some r ∈ T(R): 3^|R|
probes instead of 2^|S|.

## Correctness

Notation: types are vectors in {±1}^q with first entry +1; for a set S of types,
T(S) = { Σ z_s s : z ∈ {−1,0,1}^S }. A set is detecting iff no nonzero ternary
combination vanishes. `ENUMERATION_PROOF.md` proves the reduction to type sets
containing type 0. It also proves that the prefixes of a lex-least set are
lex-least.

**Lemma 1 (legality).** If S is detecting and c ∉ S, then S ∪ {c} is detecting
iff c ∉ T(S).
*Proof.* A vanishing combination with z_c = 0 is one of S. One with z_c = ±1
gives c = ∓Σ z_s s ∈ T(S), and conversely. ∎

**Lemma 2 (compatibility).** If S ∪ {a, b} is detecting, then a + b ∉ T(S) and
a − b ∉ T(S).
*Proof.* T(S ∪ {a}) = T(S) ∪ (T(S) + a) ∪ (T(S) − a), and b ∉ T(S ∪ {a}) by
Lemma 1. So b − a ∉ T(S) and b + a ∉ T(S); T(S) is symmetric. ∎
For a, b both legal for S, the converse also holds: b is legal for S ∪ {a} iff
a ± b ∉ T(S). This is what makes a child's candidate list equal its row of the
graph.

**Lemma 3 (meet in the middle).** For disjoint P, R, T(P ∪ R) = T(P) + T(R),
so v ∈ T(P ∪ R) iff v − r ∈ T(P) for some r ∈ T(R).
Keys are packed as zero + Σ_j u_j·2^(f·j), with f = 7 bits per field when q = 9
and 8 otherwise, and bias 64. A probe for v − r matches a stored t ∈ T(P) iff
every field of (v − r) − t is zero. That difference is a ternary combination of
at most depth columns plus v = a ± b, so every coordinate has absolute value at
most depth + 2 ≤ n + 1 ≤ 21 < 64. Every field of every key therefore stays in
[0, 2^f), no field carries into its neighbour, and equal keys mean equal
vectors. For 9×16 with anchor 7, stored fields are within 64 ± 7 and queried
ones within 64 ± 10. T(P) has at most 3^9 = 19,683 entries in a table of 65,536
slots (both engines enforce this), so probing terminates. ∎

**Lemma 4 (exact clique test).** `has_clique(A, P, k)` returns true iff the
graph induced on P has a k-clique.
*Proof.* True is only returned after recursing into N(v) ∩ P with k − 1, which
builds a clique. The colouring splits P into independent sets, so a clique
meets each colour at most once. Vertices are processed in decreasing colour. At
step i, every k-clique through an already-processed vertex was searched for
when that vertex was expanded, and the vertex was then removed. The
unprocessed vertices carry colours ≤ colour[i]. So colour[i] < k proves that no
k-clique remains. ∎

**Lemma 5 (minimal image).** `canon_fast(S)` equals the brute-force verdict:
S is rejected iff some pivot, translation m and bit permutation σ give
sorted(σ(S' ⊕ m)) <lex S.
*Proof.* S[0] = 0 is the least possible point, so a smaller image must contain
0. Bit permutations fix 0, so σ(t ⊕ m) = 0 iff t = m. That forces m ∈ S', and
only those masks are tried. The entries of X are distinct and σ is a bijection,
so distinct elements have distinct images. In particular, at i = 1 every other
element maps above 0. Fix X = S' ⊕ m ∋ 0.
`min_image_less(i, cells, U)` keeps this invariant: every σ in the coset
Σ = {σ : σ(A_c) = B_c for all cells} maps the i used elements U onto
S[0..i−1], and these are the i smallest points of σ(X).
- *Minimum value.* The least value of σ(x) over Σ is
  mi(x) = OR_c lowbits(B_c, |x ∩ A_c|). The cells are independent and their
  output sets are disjoint.
- *The next point.* So p = min over unused x of mi(x) is the least possible
  (i+1)-th point. If p < S[i], some σ gives a smaller image. If p > S[i], every
  σ gives a larger one.
- *A tie.* If p = S[i], a smaller image needs σ(x) = p for some x with
  mi(x) = p. Because the output sets of the cells are disjoint, σ(x) = p
  exactly when each cell maps x ∩ A_c onto lowbits(B_c, |x ∩ A_c|). That is
  the refined coset passed to the recursion. In that coset every other unused
  element maps strictly above p, so the invariant holds.
- *Termination.* At i = |X| the image equals S. ∎

**Theorem (completeness and soundness).** Let F be any detecting n-set
containing 0, and F* = (f_0 < … < f_{n−1}) the lex-least set in its orbit.
Then the search visits every prefix F*_k.

Assume node F*_k is visited with candidate list ⊇ {f_k, …, f_{n−1}}. Then:
- each f_j, j ≥ k, survives filtering (Lemmas 1 and 3), so the lookahead holds;
- the f_j are pairwise compatible (Lemma 2), so they form a clique of the needed
  size and the node survives (Lemma 4);
- f_k comes before f_{k+1}, …, f_{n−1} in the live list, so the "not enough
  left" break does not fire before it;
- F*_{k+1} is lex-least, so `canon_fast` accepts it (Lemma 5);
- the child's list is f_k's row of the graph restricted to later types, which
  contains f_{k+1}, … (Lemma 2 converse).

By induction F* is output. Conversely, every output is detecting. Each added
type was either filtered by an exact legality test (Lemmas 1 and 3), or taken
from a prefiltered list whose members are legal for the parent and compatible
with the newly added type. By the converse of Lemma 2, that makes them legal for
the child. So "no solution"
means no detecting q×n matrix exists.

The parallel engine changes only the order in which subtrees are visited. Each
task rebuilds T for its prefix before continuing (`Engine::load`). Its per-depth
node counts equal those of the sequential C engine on every instance compared.

## Parallelism

The Rust engine hands every subtree rooted above `--pardepth` to rayon's
work-stealing pool. Node counts do not depend on scheduling.

## Validation

`./fast_controls.sh` runs:

- **Naive oracle** (`fast_oracle_check.py`), on both engines, for every q×n
  with q = 4, 5, 6. A plain DFS lists all detecting sets with no symmetry and
  no pruning. The engine's representatives must be detecting, lex-least (by a
  loop over the whole group) and distinct. Their orbit sizes, times
  n / 2^(q−1), must sum exactly to the naive count. For example, 6×7: 433
  orbits cover all 241,486 naive solutions.
- **Mutation test** (`fast_mutants.py`). Ten deliberately broken copies of
  `enum_fast.c` must each fail the oracle: one per lemma ingredient (clique
  bound, colour bound, both halves of T, the a ± b test, child lists, tie
  handling, low-bit table, lookahead). All ten fail.
- **Canonicity agreement**: at every node of 6×9, 7×11 and 7×12 (6×9 with
  pivots), on a full 9×16 subtree, and on random sets for q = 6…9 against a
  third, independent brute-force lex-min (`canon_random_check.c`).
- **Membership independence at q = 9**: on 9×16 subtrees, the C engine with
  plain subset-sum hashing (`--mitm 0`) gives the same node vectors as the
  Rust engine with meet-in-the-middle.
- **Identical per-depth node vectors** from C and Rust on 6×9, 7×11–7×14, 8×14
  and two 9×16 subtrees.
- **Known values** β(Q_n), n = 3…14: no (β−1)×n matrix, and a β×n matrix
  exists.
- **The 9×15 positive control.**

Outside the script:
- The full 8×13 solution list at canonical depth 8 matches `enum.c` line for
  line: 108,865 solutions.
- On 9×15 under the forced prefix 0,3,12,23,45,84,99, the Rust engine's
  canonical solutions equal those of `enum.c` after brute-force lex-min
  filtering (64 = 64).

On 8×14 both engines report the node vector
`0,1,6,18,143,1082,11364,115308,1112036,5215214,3155765,19114,649,0,0`
(9,630,700 nodes against about 340 million for `enum.c`) and no matrix. The C
engine takes 65 s on one core. The Rust engine takes 10.6 s on 14 threads.
