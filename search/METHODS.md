# Search methods

Research-grade code, published for reproducibility — expect rough edges. The
certificates in `../matrices/` do not depend on any of this: they are verified
by the standalone checkers in the repo root.

## The engine: `sa.c`

One C file, compiled per row count: `cc -O3 -DQ=<rows> -o sa_q<rows> sa.c`.
Core primitive: exact ternary-kernel counting by meet-in-the-middle — enumerate
all 3^(n/2) half-assignments, pack each half's q row-sums into 5-bit fields
(offset so every field stays in [0,31]), radix-sort one side and merge. Modes:

- `anneal <n> <sec> <seed|RAND> <rng> <out> [wcap]` — simulated annealing on the
  ±1 entries, objective = exact kernel count (optionally weight-capped for speed,
  with exact re-certification of any claimed zero).
- `count <file> <n>` — exact kernel count of a given matrix.
- `extend <n> <file> ...` — one-pass scan of all 2^q candidate columns; columns
  whose targets have no ternary preimage extend the matrix to n+1 with the
  zero-kernel property intact.
- `pair <n> <file>` — two-column extension scan (c1, c2, c1±c2 all preimage-free).
- `polish`, `circ` — local repair and an exhaustive circulant-family search.

## The pipeline that actually found the records

1. **Anneal** at the target size. β(Q₂₉) ≤ 15 fell this way (`best29_a`).
2. **Slice audit** (`sliceaudit.js`): take random row/column submatrices of a
   solved matrix and exact-count them. β(Q₂₆) ≤ 14 was a raw 14×26 slice of a
   solved 15×29 — cost: one evaluation.
3. **Slice + extend** (`hunt.sh`, `process_base.py`): industrialize step 2 —
   slice many children (e.g. 13×23), then `extend`-scan each for one more
   column. β(Q₂₄) ≤ 13 came from two independent 13×23 slices that extend by
   the same column.
4. **Sibling pipeline** (`pairhunt2.sh`): delete one column of a solved matrix,
   `extend`-scan the base to materialize *sibling* solutions, and scan those for
   a further extension. This surfaced the observation that one column-deleted
   15×28 of `best29_a` is universally extendable — all 2^15 columns work.
5. **Verification discipline**: every claimed record is re-counted by two
   independently written implementations (`survivors.js` here; `../verify.c` /
   `../verify.js` are clean-room versions of the same check).

`gen_all.sh` regenerates a best-known-size landmark matrix for every n ≤ 30
(used by the interactive site).

## Lower-bound side: `cegar2.py`

Counterexample-guided search over the same matrix space with an incremental SAT
solver (CaDiCaL via PySAT): propose a matrix, find a kernel vector, ban it for
ALL matrices via a totalizer encoding, repeat until UNSAT (which would prove the
bound tight at that size). Symmetry breaking: first row/column fixed, double-lex
ordering. State (the ban list) persists across restarts.

## Provenance

The search was built and orchestrated end-to-end with Claude (Anthropic Fable 5),
including this code. Verification is independent of the AI: run the checkers.
