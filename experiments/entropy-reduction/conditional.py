#!/usr/bin/env python3
"""Measure an exact conditional-entropy bound at a fixed row prefix.

Research probe only: not yet a rule in reduce.py's certificate format.
"""
from collections import Counter
from functools import lru_cache
from itertools import combinations, product
import json
from math import log2, prod
import time

from reduce import capacity, pair_obstruction, weights_of


@lru_cache(None)
def layer_masks(n, s):
    return tuple(sum(1 << i for i in subset) for subset in combinations(range(n), s))


@lru_cache(None)
def power(a):
    return a**a


def conditional_bound(q, profile, bounds, s=None):
    started = time.monotonic()
    n = sum(profile)
    s = n//2 if s is None else s
    r = len(profile).bit_length()-1
    remaining_rows = q-1-r
    if remaining_rows < 1 or not 0 <= s <= n:
        raise ValueError('requires an unfinished prefix and a valid subset layer')
    types = [t for t, c in enumerate(profile) for _ in range(c)]
    old_masks = [sum(1 << i for i, t in enumerate(types) if (t >> j) & 1)
                 for j in range(r)]
    subsets = layer_masks(n, s)
    labels = [tuple((mask & row).bit_count() for row in old_masks) for mask in subsets]
    prefix_counts = Counter(labels)
    prefix_product = prod(power(c) for c in prefix_counts.values())
    weights = weights_of(profile)
    last_weight = weights[-1] if weights else 1
    child_cap = capacity(q-r-1, bounds)
    ranges = [range(max(0, c-child_cap), min(c, child_cap)+1) for c in profile]
    offsets = []
    offset = 0
    for c in profile:
        offsets.append(offset)
        offset += c
    best_product = None
    tested = 0
    for counts in product(*ranges):
        weight = sum(counts)
        if not last_weight <= weight <= n//2:
            continue
        other = tuple(c-a for c, a in zip(profile, counts))
        if weight*2 == n and counts > other:
            continue
        if pair_obstruction(other+counts, q, bounds) is not None:
            continue
        row = sum(((1 << c)-1) << offset for c, offset in zip(counts, offsets))
        bins = Counter((label, (mask & row).bit_count()) for mask, label in zip(subsets, labels))
        candidate = prod(power(c) for c in bins.values())
        best_product = candidate if best_product is None else min(candidate, best_product)
        tested += 1
    # Any future row could have been appended now. The maximum over all such
    # rows therefore bounds every future row's conditional entropy.
    rejected = (best_product is None or
                best_product**remaining_rows > prefix_product**(remaining_rows-1))
    N = len(subsets)
    return {'q': q, 'n': n, 'profile': list(profile), 'layer': s,
            'remaining_rows': remaining_rows, 'candidate_rows': tested,
            'rejects': rejected,
            'residual_bits': log2(prefix_product)/N,
            'upper_bits_per_row': ((log2(prefix_product)-log2(best_product))/N
                                   if best_product is not None else None),
            'seconds': round(time.monotonic()-started, 6)}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('q', type=int)
    ap.add_argument('profile', help='JSON column-type multiplicities')
    ap.add_argument('--bounds', default='{}')
    args = ap.parse_args()
    print(json.dumps(conditional_bound(args.q, tuple(json.loads(args.profile)),
                                      {int(k): v for k,v in json.loads(args.bounds).items()})))
