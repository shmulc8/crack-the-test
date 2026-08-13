#!/usr/bin/env python3
"""Derive the q=9 canonical control prefix from the 9x15 certificate."""

from __future__ import annotations

import argparse
from pathlib import Path


TRANSLATION = 54
PERMUTATION = (1, 6, 5, 4, 7, 0, 2, 3)
EXPECTED = (0, 3, 12, 23, 45, 84, 99, 120, 127, 153, 174, 180, 197, 214, 218)


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


def transform(value: int) -> int:
    translated = value ^ TRANSLATION
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
        raise SystemExit(f"canonical control mismatch: {actual}")
    print("CANONICAL Q9 CONTROL: " + ",".join(str(value) for value in actual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
