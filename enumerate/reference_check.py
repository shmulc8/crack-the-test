#!/usr/bin/env python3
"""Differential checks for enum.c using deliberately simple Python code.

This is not a second 8x14 enumerator. It exhausts small instances directly
with itertools.combinations and tuple-valued subset sums, then compares the
complete solution sets with enum.c both with and without canonical pruning.
It also checks that split runs are disjoint and their union is complete.
"""

from __future__ import annotations

import argparse
import functools
import itertools
import re
import subprocess
from pathlib import Path


SOLUTION_RE = re.compile(r"^SOLUTION #[0-9]+: types((?: [0-9]+)+)$", re.MULTILINE)
COUNT_RE = re.compile(r"^solutions found: ([0-9]+)$", re.MULTILINE)


def column(type_id: int, q: int) -> tuple[int, ...]:
    return (1,) + tuple(-1 if type_id & (1 << j) else 1 for j in range(q - 1))


def is_detecting(types: tuple[int, ...], q: int) -> bool:
    sums = {(0,) * q}
    for type_id in types:
        col = column(type_id, q)
        shifted = {tuple(a + b for a, b in zip(value, col)) for value in sums}
        if sums & shifted:
            return False
        sums |= shifted
    return True


def reference_solutions(q: int, n: int) -> set[tuple[int, ...]]:
    # Fixing type 0 is without loss of generality; see ENUMERATION_PROOF.md.
    return {
        (0,) + tail
        for tail in itertools.combinations(range(1, 1 << (q - 1)), n - 1)
        if is_detecting((0,) + tail, q)
    }


def permute_type(type_id: int, permutation: tuple[int, ...]) -> int:
    image = 0
    for source, destination in enumerate(permutation):
        if type_id & (1 << source):
            image |= 1 << destination
    return image


def canonical_form(types: tuple[int, ...], q: int) -> tuple[int, ...]:
    """Brute-force the whole-set orbit, independently of prefix pruning."""
    best = types
    for translate in types:
        translated = tuple(type_id ^ translate for type_id in types)
        for permutation in itertools.permutations(range(q - 1)):
            image = tuple(sorted(permute_type(type_id, permutation) for type_id in translated))
            if image < best:
                best = image
    return best


@functools.lru_cache(maxsize=None)
def pivot_transforms(q: int) -> list[list[int]]:
    """Every distinct O(q,Z)=(Z_2)^q x| S_q action on the normalized type set.

    A type encodes a length-q +/-1 column with row 0 pinned to +1. Applying a
    row permutation and row sign-flips, then renormalizing each column so row 0
    is +1 again, maps the type set to itself. This is the full group that
    enum.c's --pivots quotients by (the baseline canonical_form above only uses
    the row-0 stabilizer: translations and S_{q-1}). Each transform is a table
    mapping type_id -> type_id; duplicates are collapsed.
    """
    size = 1 << (q - 1)
    columns = [column(type_id, q) for type_id in range(size)]
    tables: set[tuple[int, ...]] = set()
    for permutation in itertools.permutations(range(q)):
        for sign_mask in range(1 << q):
            table = []
            for value in columns:
                flipped = [(-1 if (sign_mask >> i) & 1 else 1) * value[permutation[i]] for i in range(q)]
                if flipped[0] == -1:
                    flipped = [-entry for entry in flipped]
                table.append(sum(1 << j for j in range(q - 1) if flipped[j + 1] == -1))
            tables.add(tuple(table))
    return [list(table) for table in tables]


def canonical_form_pivots(types: tuple[int, ...], q: int) -> tuple[int, ...]:
    """Whole-set orbit minimum under the full O(q,Z) row group (row pivoting)."""
    best = tuple(sorted(types))
    for table in pivot_transforms(q):
        image = tuple(sorted(table[type_id] for type_id in types))
        if image < best:
            best = image
    return best


def run_enum(binary: Path, q: int, n: int, extra: list[str]) -> set[tuple[int, ...]]:
    command = [
        str(binary),
        str(q),
        str(n),
        "--maxsol",
        "2147483647",
        "--report",
        "99999",
        *extra,
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    solutions = [tuple(map(int, match.split())) for match in SOLUTION_RE.findall(completed.stdout)]
    counts = COUNT_RE.findall(completed.stdout)
    if len(counts) != 1 or int(counts[0]) != len(solutions):
        raise RuntimeError(f"malformed or inconsistent output from: {' '.join(command)}")
    if len(set(solutions)) != len(solutions):
        raise RuntimeError(f"duplicate solution emitted by: {' '.join(command)}")
    return set(solutions)


def compare(label: str, expected: set[tuple[int, ...]], actual: set[tuple[int, ...]]) -> None:
    if expected == actual:
        return
    missing = sorted(expected - actual)[:3]
    extra = sorted(actual - expected)[:3]
    raise AssertionError(f"{label}: missing={missing}, extra={extra}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("enum_binary", type=Path)
    args = parser.parse_args()
    binary = args.enum_binary.resolve(strict=True)

    cases = ((3, 4), (4, 4), (5, 6))
    references: dict[tuple[int, int], set[tuple[int, ...]]] = {}
    for q, n in cases:
        expected = reference_solutions(q, n)
        references[q, n] = expected
        actual = run_enum(binary, q, n, ["--canondepth", "0"])
        compare(f"raw {q}x{n}", expected, actual)
        print(f"raw {q}x{n}: exact match ({len(expected)} solutions)")

    q, n = 5, 6
    expected_canonical = {canonical_form(solution, q) for solution in references[q, n]}
    canonical = run_enum(binary, q, n, ["--canondepth", str(n)])
    compare("canonical 5x6", expected_canonical, canonical)
    print(f"canonical 5x6: exact orbit match ({len(canonical)} representatives)")

    parts: list[set[tuple[int, ...]]] = []
    for part in range(3):
        result = run_enum(
            binary,
            q,
            n,
            [
                "--canondepth",
                str(n),
                "--split",
                "3",
                "--part",
                str(part),
                "--splitdepth",
                "3",
            ],
        )
        for earlier, previous in enumerate(parts):
            overlap = result & previous
            if overlap:
                raise AssertionError(f"partitions {earlier} and {part} overlap: {sorted(overlap)[:3]}")
        parts.append(result)

    union = set().union(*parts)
    compare("partition union 5x6", expected_canonical, union)
    print(f"partition 5x6: disjoint and complete ({[len(part) for part in parts]})")

    for q, n in cases:
        expected_pivots = {canonical_form_pivots(solution, q) for solution in references[q, n]}
        pivoted = run_enum(binary, q, n, ["--pivots", "--canondepth", str(n)])
        compare(f"pivots {q}x{n}", expected_pivots, pivoted)
        print(f"pivots {q}x{n}: exact O(q,Z)-orbit match ({len(pivoted)} representatives)")

    print("REFERENCE CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
