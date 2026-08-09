#!/usr/bin/env python3
"""Fail-closed validation and hashing of the ten decisive 8x14 logs."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


DONE_RE = re.compile(r"^DONE .* nodes/depth: \[([0-9,]+)\]", re.MULTILINE)
COUNT_RE = re.compile(r"^solutions found: ([0-9]+)$", re.MULTILINE)
EXPECTED_PREFIX = (0, 1, 6, 18, 143, 1082, 11364)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", choices=("c", "rust"), default="c")
    parser.add_argument("logs", nargs="+", type=Path)
    args = parser.parse_args()
    if len(args.logs) != 10:
        parser.error("exactly ten partition logs are required")

    seen: set[int] = set()
    engine_prefix = "" if args.engine == "c" else "rust "
    header_re = re.compile(
        rf"^{engine_prefix}q=8 n=14: 128 types, 5040 perms, split ([0-9]+)/10 "
        r"\(depth 6\), canon<=8$",
        re.MULTILINE,
    )
    for path in args.logs:
        data = path.read_bytes()
        text = data.decode("utf-8")
        headers = header_re.findall(text)
        done = DONE_RE.findall(text)
        counts = COUNT_RE.findall(text)
        if len(headers) != 1 or len(done) != 1 or len(counts) != 1:
            raise SystemExit(f"FAIL {path}: missing or duplicate header/DONE/count")
        part = int(headers[0])
        if part in seen or not 0 <= part < 10:
            raise SystemExit(f"FAIL {path}: duplicate or invalid partition {part}")
        seen.add(part)
        nodes = tuple(map(int, done[0].split(",")))
        if len(nodes) != 15 or nodes[:7] != EXPECTED_PREFIX:
            raise SystemExit(f"FAIL {path}: unexpected node vector {nodes}")
        if counts[0] != "0" or "SOLUTION #" in text:
            raise SystemExit(f"FAIL {path}: partition is not a clean zero-solution run")
        terminal = f"*** no solutions in 8x14 partition {part}/10 ***"
        if terminal not in text:
            raise SystemExit(f"FAIL {path}: missing terminal verdict")
        digest = hashlib.sha256(data).hexdigest()
        print(f"part {part}: nodes={nodes[7:]} sha256={digest}")

    if seen != set(range(10)):
        raise SystemExit(f"FAIL: missing partitions {sorted(set(range(10)) - seen)}")
    print("PARTITION LOG CHECK PASSED: all parts present, common frontier, zero solutions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
