#!/usr/bin/env python3
"""Decode McKay's bipartite graph6 data into sets of binary vectors.

Each output line contains ``m`` integers in ``[0, 2**n)``, one set per graph.
Diagnostics go to stderr so the emitted dataset can be redirected safely.
"""

import argparse
import sys
from collections import deque


def g6_decode(line):
    line = line.strip()
    if not line or line.startswith(">>"):
        raise ValueError("expected a short graph6 record without a header")
    size = ord(line[0]) - 63
    if not 0 <= size <= 62:
        raise ValueError("only short graph6 records (0..62 vertices) are supported")
    bits = []
    for char in line[1:]:
        value = ord(char) - 63
        if not 0 <= value <= 63:
            raise ValueError("invalid graph6 character")
        bits.extend((value >> bit) & 1 for bit in range(5, -1, -1))
    needed = size * (size - 1) // 2
    if len(bits) < needed:
        raise ValueError("truncated graph6 record")
    adjacency = [set() for _ in range(size)]
    index = 0
    for right in range(1, size):
        for left in range(right):
            if bits[index]:
                adjacency[left].add(right)
                adjacency[right].add(left)
            index += 1
    return size, adjacency


def bipartition(size, adjacency, left_size):
    """Two-colour components and orient them so the left side has left_size vertices."""
    colour = [-1] * size
    components = []
    for start in range(size):
        if colour[start] != -1:
            continue
        colour[start] = 0
        queue = deque([start])
        side0, side1 = [start], []
        while queue:
            vertex = queue.popleft()
            for neighbour in adjacency[vertex]:
                if colour[neighbour] == -1:
                    colour[neighbour] = 1 - colour[vertex]
                    (side0 if colour[neighbour] == 0 else side1).append(neighbour)
                    queue.append(neighbour)
                elif colour[neighbour] == colour[vertex]:
                    raise ValueError("graph is not bipartite")
        components.append((side0, side1))

    reachable = {0: []}
    for side0, side1 in components:
        next_reachable = {}
        for total, choices in reachable.items():
            for pick, side in ((0, side0), (1, side1)):
                new_total = total + len(side)
                if new_total <= left_size and new_total not in next_reachable:
                    next_reachable[new_total] = choices + [pick]
        reachable = next_reachable
    if left_size not in reachable:
        raise ValueError(f"no bipartition with a side of size {left_size}")

    left, right = [], []
    for (side0, side1), pick in zip(components, reachable[left_size]):
        left.extend(side0 if pick == 0 else side1)
        right.extend(side1 if pick == 0 else side0)
    return sorted(left), sorted(right)


def to_matrix(line, rows, columns):
    size, adjacency = g6_decode(line)
    if size != rows + columns:
        raise ValueError(f"record has {size} vertices, expected {rows + columns}")
    left, right = bipartition(size, adjacency, rows)
    return [[int(column_vertex in adjacency[row_vertex]) for column_vertex in right]
            for row_vertex in left]


def row_types(matrix):
    return [sum(bit << column for column, bit in enumerate(row)) for row in matrix]


def dissociated(matrix, columns):
    sums = [tuple([0] * columns)]
    for row in matrix:
        shifted = [tuple(total[j] + row[j] for j in range(columns)) for total in sums]
        sums += shifted
    return len(set(sums)) == len(sums)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph6_file")
    parser.add_argument("rows", type=int, help="vectors per set (12 for diff7_12.g6)")
    parser.add_argument("columns", type=int, help="bits per vector (7 for diff7_12.g6)")
    parser.add_argument("--limit", type=int, help="decode only the first N records")
    parser.add_argument("--check", action="store_true", help="also check dissociativity in Python")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.rows < 1 or args.columns < 1 or args.limit is not None and args.limit < 1:
        raise SystemExit("rows, columns, and --limit must be positive")

    total = emitted = bad = 0
    with open(args.graph6_file, encoding="ascii") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip() or line.startswith(">>"):
                continue
            total += 1
            if args.limit is not None and emitted >= args.limit:
                continue
            try:
                matrix = to_matrix(line, args.rows, args.columns)
            except ValueError as error:
                raise SystemExit(f"{args.graph6_file}:{line_number}: {error}") from error
            if args.check and not dissociated(matrix, args.columns):
                bad += 1
            print(" ".join(str(value) for value in row_types(matrix)))
            emitted += 1

    check_result = f"{bad} failures" if args.check else "not checked (thm_check performs the exhaustive C check)"
    print(f"decoded {emitted} of {total} records; dissociativity: {check_result}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
