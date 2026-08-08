#!/usr/bin/env python3
"""Verify a weighing certificate for the Erdos-Renyi constant M(n).

A file holds an m x n matrix over {0,1}: row j is a weighing (which coins go on
the scale), column i is coin i. The certificate is valid when the 2^n subset
sums are pairwise distinct, i.e. every distribution of counterfeit coins gives a
different vector of readings, so m weighings determine the subset and M(n) <= m.

usage: verify_weighing.py <file>
"""
import sys


def read_matrix(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if any(c not in "01" for c in line):
                sys.exit(f"bad char in row {len(rows)}: expected only 0/1")
            rows.append([int(c) for c in line])
    if not rows:
        sys.exit("no rows found")
    if len({len(r) for r in rows}) != 1:
        sys.exit("rows have differing lengths")
    return rows


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    rows = read_matrix(path)
    m, n = len(rows), len(rows[0])

    # column i as an m-vector; accumulate subset sums over all 2^n subsets
    cols = [[rows[j][i] for j in range(m)] for i in range(n)]
    seen = {}
    sums = [tuple([0] * m)]
    for i, c in enumerate(cols):
        nxt = []
        for s in sums:
            nxt.append(tuple(s[j] + c[j] for j in range(m)))
        sums = sums + nxt
    for idx, s in enumerate(sums):
        if s in seen:
            print(f"INVALID: subsets {seen[s]:0{n}b} and {idx:0{n}b} share the sum {s}")
            return 1
        seen[s] = idx

    print(f"VALID certificate: M({n}) <= {m}  ({len(sums)} subset sums, all distinct)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
