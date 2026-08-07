#!/usr/bin/env python3
"""Independent confirmation route for "no 8x14 detecting matrix exists".

Logic, different from the depth-14 search: deleting any column from an 8x14
detecting matrix leaves an 8x13 detecting matrix (a subset of a set with
distinct subset sums still has distinct subset sums). So if EVERY 8x13
detecting matrix — up to symmetry — admits no 14th column, no 8x14 exists.

This script takes the classification produced by
    enum3 8 13 --maxsol <big> --canondepth 13
(one "SOLUTION #k: types ..." line per isomorphism class), rebuilds each class
from scratch, re-verifies that it really is detecting, then tries all 2^(q-1)
column types as a 14th column.

Sharing no code with the C search, this is a genuine second opinion: it would
catch a bug in the C incremental test, the packing, or the pruning.

usage: verify_extensions.py <classification.log> [q] [n]
"""
import itertools, re, sys

LOG = sys.argv[1]
q = int(sys.argv[2]) if len(sys.argv) > 2 else 8
n = int(sys.argv[3]) if len(sys.argv) > 3 else 13
NT = 1 << (q - 1)

def col(t):
    """column type index -> the +/-1 column vector (first entry +1)"""
    return (1,) + tuple(-1 if (t >> j) & 1 else 1 for j in range(q - 1))

def subset_sums(types):
    """all subset sums, as a set of tuples; returns None if any collision"""
    sums = {(0,) * q}
    for t in types:
        c = col(t)
        new = set()
        for s in sums:
            v = tuple(a + b for a, b in zip(s, c))
            if v in sums or v in new:
                return None                 # collision => not detecting
            new.add(v)
        sums |= new
    return sums

classes = []
for line in open(LOG):
    m = re.match(r"SOLUTION #\d+: types ([\d ]+)", line)
    if m:
        classes.append([int(x) for x in m.group(1).split()])

print(f"read {len(classes)} classes of {q}x{n} from {LOG}")
bad_class, extendable, checked = 0, [], 0
for i, cls in enumerate(classes):
    if len(cls) != n:
        print(f"  class {i}: wrong size {len(cls)}"); bad_class += 1; continue
    sums = subset_sums(cls)
    if sums is None:
        print(f"  *** class {i} {cls} is NOT detecting — C search is wrong ***")
        bad_class += 1
        continue
    if len(sums) != (1 << n):
        print(f"  *** class {i}: {len(sums)} sums, expected {1<<n} ***")
        bad_class += 1
        continue
    checked += 1
    for t in range(NT):
        if t in cls:
            continue
        c = col(t)
        shifted = {tuple(a + b for a, b in zip(s, c)) for s in sums}
        if not (shifted & sums):
            extendable.append((i, cls, t))
    if (i + 1) % 25 == 0:
        print(f"  ...{i+1}/{len(classes)} classes checked, {len(extendable)} extendable so far", flush=True)

print()
print(f"classes verified as genuine {q}x{n} detecting matrices: {checked}/{len(classes)}")
print(f"malformed / non-detecting classes: {bad_class}")
print(f"classes admitting a {n+1}-th column: {len(extendable)}")
if extendable:
    for i, cls, t in extendable[:5]:
        print(f"  EXTENDS: class {i} {cls} + type {t}")
    print(f"*** A {q}x{n+1} DETECTING MATRIX EXISTS — the search verdict is WRONG ***")
elif bad_class == 0 and checked:
    print(f"*** every {q}x{n} class is extension-maximal => NO {q}x{n+1} MATRIX EXISTS ***")
