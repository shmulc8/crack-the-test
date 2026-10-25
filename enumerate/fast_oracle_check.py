#!/usr/bin/env python3
"""Exact orbit-level check of a fast enumerator against a naive search.

For each (q, n) the naive side lists every detecting set of n types that
contains type 0, by plain DFS over increasing types with tuple subset sums:
no symmetry, no pruning beyond the definition. The enumerator under test
prints canonical representatives with all of its pruning enabled. The check
then requires:

1. soundness: every representative is detecting and is lex-least in its orbit
   under G = translations x bit permutations, found by looping over all of G;
2. distinctness: no representative is printed twice (lex-least sets of
   different orbits differ, so this means one per orbit);
3. completeness: sum over representatives of |orbit| * n / 2^(q-1) equals the
   number of naive solutions. G contains every translation, so exactly a
   fraction n / 2^(q-1) of any orbit's sets contain type 0; |orbit| comes from
   the stabiliser, computed by brute force.

Together these say the representatives are exactly one per orbit of detecting
sets. A missing orbit makes the sum too small; a non-canonical or duplicate
representative fails 1 or 2.

Usage: fast_oracle_check.py [--recompute] BINARY [extra flags passed to every run]
"""

from __future__ import annotations

import itertools
import math
import re
import subprocess
import sys
from pathlib import Path

SOLUTION_RE = re.compile(r"^SOLUTION #[0-9]+: types((?: [0-9]+)+)$", re.MULTILINE)

CASES = [(4, n) for n in range(2, 7)] + [(5, n) for n in range(2, 8)] + [(6, n) for n in range(2, 10)]

# naive_count(q, n) for every case, as computed by this file; --recompute rechecks them
NAIVE = {
    (4, 2): 7, (4, 3): 21, (4, 4): 29, (4, 5): 5, (4, 6): 0,
    (5, 2): 15, (5, 3): 105, (5, 4): 430, (5, 5): 990, (5, 6): 726, (5, 7): 0,
    (6, 2): 31, (6, 3): 465, (6, 4): 4405, (6, 5): 28315, (6, 6): 117876,
    (6, 7): 241486, (6, 8): 103720, (6, 9): 0,
}


def column(t: int, q: int) -> tuple[int, ...]:
    return (1,) + tuple(-1 if t >> j & 1 else 1 for j in range(q - 1))


def is_detecting(types: tuple[int, ...], q: int) -> bool:
    sums = {(0,) * q}
    for t in types:
        col = column(t, q)
        shifted = {tuple(a + b for a, b in zip(s, col)) for s in sums}
        if sums & shifted:
            return False
        sums |= shifted
    return True


def naive_count(q: int, n: int) -> int:
    nt = 1 << (q - 1)
    count = 0

    def dfs(last: int, depth: int, sums: frozenset) -> None:
        nonlocal count
        if depth == n:
            count += 1
            return
        for t in range(last + 1, nt - (n - depth) + 1):
            col = column(t, q)
            shifted = {tuple(a + b for a, b in zip(s, col)) for s in sums}
            if sums.isdisjoint(shifted):
                dfs(t, depth + 1, sums | shifted)

    zero = (0,) * q
    dfs(0, 1, frozenset({zero, column(0, q)}))
    return count


def group(q: int) -> list[tuple[int, tuple[int, ...]]]:
    k = q - 1
    return [(m, p) for m in range(1 << k) for p in itertools.permutations(range(k))]


def act(t: int, m: int, p: tuple[int, ...]) -> int:
    x = t ^ m
    out = 0
    for j, image in enumerate(p):
        if x >> j & 1:
            out |= 1 << image
    return out


def run(binary: Path, q: int, n: int, extra: list[str]) -> list[tuple[int, ...]]:
    extra = list(extra)
    if "--mitm" in extra:  # the anchor must be below n; cap it per case
        i = extra.index("--mitm") + 1
        extra[i] = str(min(int(extra[i]), n - 1))
    cmd = [str(binary), str(q), str(n), "--maxsol", "1000000000", "--report", "99999", *extra]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    return [tuple(int(x) for x in m.group(1).split()) for m in SOLUTION_RE.finditer(out)]


def main() -> int:
    argv = sys.argv[1:]
    recompute = bool(argv) and argv[0] == "--recompute"
    if recompute:
        argv = argv[1:]
    if not argv:
        print(__doc__)
        return 2
    binary = Path(argv[0]).resolve(strict=True)
    extra = argv[1:]
    for q, n in CASES:
        g = group(q)
        nt = 1 << (q - 1)
        reps = run(binary, q, n, extra)
        if len(set(reps)) != len(reps):
            raise AssertionError(f"{q}x{n}: duplicate representatives")
        covered = 0
        for s in reps:
            if not is_detecting(s, q):
                raise AssertionError(f"{q}x{n}: {s} is not detecting")
            key = tuple(sorted(s))
            stab = 0
            for m, p in g:
                image = tuple(sorted(act(t, m, p) for t in s))
                if image < key:
                    raise AssertionError(f"{q}x{n}: {s} is not lex-least (image {image})")
                stab += image == key
            covered += len(g) // stab * n
        expected = naive_count(q, n) if recompute else NAIVE[q, n]
        if covered % nt or covered // nt != expected:
            raise AssertionError(f"{q}x{n}: representatives cover {covered / nt} sets, naive search found {expected}")
        print(f"{q}x{n}: {len(reps)} orbits cover all {expected} naive solutions")
    print("ORACLE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
