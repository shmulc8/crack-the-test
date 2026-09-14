#!/usr/bin/env python3
"""Independent exact checks for corner LP output."""
import argparse
import json
import hashlib
from pathlib import Path
from itertools import permutations, product

N = 8
V = list(product(range(N), repeat=3))
INDEX = {p: i for i, p in enumerate(V)}
HOODS = []
for p in V:
    q = [INDEX[p]]
    for axis in range(3):
        for step in (-1, 1):
            a = list(p); a[axis] += step
            if 0 <= a[axis] < N: q.append(INDEX[tuple(a)])
    HOODS.append(q)

GROUP = []
for perm in permutations(range(3)):
    for flips in product((0, 1), repeat=3):
        mapping = []
        for p in V:
            out = [((N - 1 - p[perm[i]]) if flips[i] else p[perm[i]]) for i in range(3)]
            mapping.append(INDEX[tuple(out)])
        GROUP.append(mapping)


def verify(result_path):
    result_path = Path(result_path)
    result = json.loads(result_path.read_text())
    records_path = result_path.with_suffix('.jsonl')
    records = ([json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
               if records_path.exists() else [])
    if len(records) != result['completed_representatives']:
        raise AssertionError('record count mismatch')
    if result.get('n') != 8 or result.get('sequence') != 'A269706':
        raise AssertionError('wrong graph metadata')
    if hashlib.sha256(records_path.read_bytes()).hexdigest() != result['records_sha256']:
        raise AssertionError('records hash mismatch')
    for rec in records:
        den = rec['denominator']
        if type(den) is not int or den <= 0:
            raise AssertionError('invalid denominator')
        if any(type(i) is not int or not 0 <= i < 512 for i in rec['fixed']):
            raise AssertionError('invalid fixed index')
        weights = {}
        for k, value in rec['weights'].items():
            if not k.isdecimal() or str(int(k)) != k or not 0 <= int(k) < 512:
                raise AssertionError('invalid weight index')
            if type(value) is not int or value < 0:
                raise AssertionError('invalid nonnegative integer weight')
            weights[int(k)] = value
        already_covered = set().union(*(HOODS[i] for i in rec['fixed']))
        if any(weights.get(i, 0) != 0 for i in already_covered):
            raise AssertionError('weight lies outside the residual problem')
        sums = [sum(weights.get(i, 0) for i in hood) for hood in HOODS]
        if max(sums) > den: raise AssertionError('hood inequality failed')
        if sum(weights.values()) != rec['total_weight']: raise AssertionError('total mismatch')
        expected = 8 + (sum(weights.values()) + den - 1) // den
        if expected != rec['combined_lower_bound']: raise AssertionError('bound mismatch')
        fixed = set(rec['fixed'])
        if len(fixed) != 8: raise AssertionError('fixed set is not eight distinct centers')
        corner_hits = []
        for p in product((0, 7), repeat=3):
            hits = [center for center in rec['fixed'] if sum(abs(a-b) for a,b in zip(V[center], p)) <= 1]
            if len(hits) != 1: raise AssertionError('corner does not have exactly one fixed dominator')
            corner_hits.extend(hits)
        if set(corner_hits) != fixed: raise AssertionError('fixed center does not belong to a corner hood')
    # Expand the stored orbit representatives independently. This checks that
    # the 1,474 representatives cover all 4^8 choices without overlap.
    expanded = set()
    for rec in records:
        fixed = tuple(rec['fixed'])
        for mapping in GROUP:
            expanded.add(tuple(sorted(mapping[i] for i in fixed)))
    if result['complete'] and len(expanded) != 4 ** 8:
        raise AssertionError(f'orbit expansion has {len(expanded)} cases, expected {4 ** 8}')
    minimum = min((r['combined_lower_bound'] for r in records), default=None)
    if minimum != result['minimum_combined_lower_bound']:
        raise AssertionError('minimum metadata mismatch')
    if result['complete'] and result['global_lower_bound_claim'] != minimum:
        raise AssertionError('global bound metadata mismatch')
    return {'status': 'PASS', 'records': len(records), 'complete': bool(result['complete']),
            'minimum_combined_lower_bound': min((r['combined_lower_bound'] for r in records), default=None),
            'expanded_corner_cases': len(expanded)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('result', type=Path)
    print(json.dumps(verify(ap.parse_args().result), indent=2))
