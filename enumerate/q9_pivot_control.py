#!/usr/bin/env python3
"""Derive the q=9 O(q,Z) pivot-canonical control prefix from the 9x15 certificate.

Unlike q9_positive_control.py (which canonicalizes under the row-0 stabilizer),
this reduces under the full signed row group enum.c --pivots quotients by:
first move reference row PIVOT_ROW into row 0 via enum.c's pivottab, then XOR
translate to contain 0, then permute the lower rows. The resulting prefix is the
orbit minimum, so enum --pivots accepts it at every depth; the baseline-canonical
prefix is (correctly) rejected under this larger group.
"""

from __future__ import annotations

import argparse
from pathlib import Path


PIVOT_ROW = 4
TRANSLATION = 212
PERMUTATION = (0, 5, 7, 3, 6, 4, 1, 2)
EXPECTED = (0, 3, 5, 24, 30, 46, 95, 99, 109, 112, 166, 171, 181, 204, 211)


def read_types(path: Path) -> list[int]:
    rows = [
        line.strip()
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if len(rows) != 9 or {len(row) for row in rows} != {15}:
        raise ValueError("expected a 9x15 sign matrix")
    if any(character not in "+-" for row in rows for character in row):
        raise ValueError("matrix entries must be + or -")

    types: list[int] = []
    for column in range(15):
        row_zero = 1 if rows[0][column] == "+" else -1
        value = 0
        for row in range(1, 9):
            entry = (1 if rows[row][column] == "+" else -1) * row_zero
            if entry == -1:
                value |= 1 << (row - 1)
        types.append(value)
    return types


def pivot(value: int, reference: int) -> int:
    """enum.c pivottab[reference]: move row `reference` into the row-0 slot."""
    if reference == 0:
        return value
    reference_bit = reference - 1
    base = (value >> reference_bit) & 1
    image = base & 1
    out_bit = 1
    for other in range(8):
        if other == reference_bit:
            continue
        if base ^ ((value >> other) & 1):
            image |= 1 << out_bit
        out_bit += 1
    return image


def transform(value: int) -> int:
    translated = pivot(value, PIVOT_ROW) ^ TRANSLATION
    image = 0
    for source, destination in enumerate(PERMUTATION):
        if (translated >> source) & 1:
            image |= 1 << destination
    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    args = parser.parse_args()
    actual = tuple(sorted(transform(value) for value in read_types(args.matrix)))
    if actual != EXPECTED:
        raise SystemExit(f"pivot-canonical control mismatch: {actual}")
    print("PIVOT CANONICAL Q9 CONTROL: " + ",".join(str(value) for value in actual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
