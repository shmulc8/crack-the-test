#!/usr/bin/env python3
"""Independent row-splitting experiment; exact arithmetic, bounded search.

No code is imported from the existing enumerator or Victor's implementation.
An exhausted budget produces UNKNOWN, never a nonexistence verdict.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
from itertools import combinations, combinations_with_replacement, product
import json
import gzip
from math import comb, prod
from pathlib import Path
import time


@lru_cache(None)
def entropy_product(n, d, s):
    """For N equally likely inputs, return product of fiber_size**fiber_size."""
    counts = [comb(d, k) * comb(n-d, s-k)
              for k in range(max(0, s-(n-d)), min(d, s)+1)]
    assert sum(counts) == comb(n, s)
    return prod(pow(a, a) for a in counts if a)


def entropy_obstruction(n, weights):
    """Return a failed layer, or None. Strict comparison is essential."""
    m = len(weights)
    if m == 0:
        return 1 if n > 1 else None
    for s in range(1, n//2+1):
        N = comb(n, s)
        left = prod(entropy_product(n, d, s) for d in weights)
        if left > pow(N, (m-1)*N):
            return s
    return None


def capacity(q, supplied):
    # Distinct normalized sign columns: at most 2**(q-1).
    return min(1 << (q-1), supplied.get(q, 1 << (q-1)))


def weight_prefixes(q, n, supplied):
    """All sorted row-weight prefixes surviving exact necessary conditions."""
    low = max(1, n-capacity(q-1, supplied))
    patterns = list(combinations_with_replacement(range(low, n//2+1), q-1))
    feasible = [w for w in patterns if entropy_obstruction(n, w) is None]
    prefixes = {w[:k] for w in feasible for k in range(q)}
    return prefixes, {"weight_patterns": len(patterns),
                      "entropy_survivors": len(feasible), "minimum_weight": low}


def weights_of(profile):
    r = len(profile).bit_length()-1
    return tuple(sum(count for t, count in enumerate(profile) if t & (1 << j))
                 for j in range(r))


def pair_obstruction(profile, q, supplied):
    """Any two rows split into agreeing/disagreeing lower-row subproblems."""
    r = len(profile).bit_length()-1
    cap = capacity(q-1, supplied)
    for i in range(r):
        for j in range(i+1, r):
            distance = sum(c for t, c in enumerate(profile) if ((t >> i) ^ (t >> j)) & 1)
            if max(distance, sum(profile)-distance) > cap:
                return [i, j]
    return None


@lru_cache(None)
def linear_tests(r):
    """Four-row signed relations involving the newly added row.

    Indices refer to sign rows, including row 0 (all +1). The checker accepts
    arbitrary integer coefficients; discovery currently searches support four.
    """
    tests = []
    for earlier in combinations(range(r), 3):
        rows = earlier + (r,)
        for signs in product((-1, 1), repeat=3):
            coeff = [0]*(r+1)
            for j, a in zip(rows, (1,)+signs):
                coeff[j] = a
            zeros = tuple(t for t in range(1 << r)
                          if coeff[0] + sum(coeff[j]*(1-2*((t >> (j-1)) & 1))
                                             for j in range(1, r+1)) == 0)
            tests.append((tuple(coeff), zeros))
    return tuple(tests)


def linear_obstruction(profile, q, supplied):
    cap = capacity(q-1, supplied)
    if sum(profile) <= cap:
        return None
    for coeff, zeros in linear_tests(len(profile).bit_length()-1):
        if sum(profile[t] for t in zeros) > cap:
            return list(coeff)
    return None


def splits(profile, q, supplied, allowed):
    """Split each column-signature cell; its two children use one fewer row."""
    r = len(profile).bit_length()-1
    cap = capacity(q-r-1, supplied)
    weights = weights_of(profile)
    ranges = [range(max(0, count-cap), min(count, cap)+1) for count in profile]
    for selected in product(*ranges):
        new_weight = sum(selected)
        if weights + (new_weight,) not in allowed:
            continue
        # Complementing only the new row swaps all children. At equal weight
        # either orientation is equivalent and neither changes previous rows.
        remaining = tuple(c-a for c, a in zip(profile, selected))
        if new_weight*2 == sum(profile) and selected > remaining:
            continue
        yield remaining + selected


def collision(profile):
    """Return a balanced ternary relation, or None; exact integer subset sums.

    Base n+1 encodes cardinality and binary row sums injectively: every digit
    stays in 0..n. Python integers are unbounded; there is no float or overflow.
    """
    r = len(profile).bit_length()-1
    types = [t for t, count in enumerate(profile) for _ in range(count)]
    base = len(types)+1
    digits = [base**(j+1) for j in range(r)]
    sums = {0: 0}
    for i, t in enumerate(types):
        col = 1 + sum(digits[j] for j in range(r) if (t >> j) & 1)
        shifted = {}
        for value, mask in sums.items():
            target = value+col
            other = mask | (1 << i)
            if target in sums:
                old = sums[target]
                return [((other >> k) & 1)-((old >> k) & 1)
                        for k in range(len(types))]
            shifted[target] = other
        sums.update(shifted)
    return None


def sign_matrix(profile):
    r = len(profile).bit_length()-1
    types = [t for t, count in enumerate(profile) for _ in range(count)]
    return ['+'*len(types)] + [''.join('-' if t & (1 << j) else '+' for t in types)
                              for j in range(r)]


class BudgetExceeded(Exception):
    pass


def solve(q, n, bounds=None, max_nodes=100000, seconds=30, keep_proof=True, linear=False):
    if not 2 <= q <= 8 or not 2 <= n <= 16:
        raise ValueError('experiment supports 2<=q<=8, 2<=n<=16')
    supplied = dict(bounds or {})
    if any(not isinstance(k, int) or not 1 <= k < q or
           not isinstance(v, int) or v < 1 for k, v in supplied.items()):
        raise ValueError('capacity premises must be positive bounds at fewer rows')
    started = time.monotonic()
    allowed, stats = weight_prefixes(q, n, supplied)
    dead = {}
    calls = 0
    reasons = Counter()

    def visit(profile):
        nonlocal calls
        if profile in dead:
            return None
        calls += 1
        if calls > max_nodes or time.monotonic()-started > seconds:
            raise BudgetExceeded
        r = len(profile).bit_length()-1
        if max(profile) > capacity(q-r, supplied):
            reason = {'kind': 'capacity'}
        elif weights_of(profile) not in allowed:
            reason = {'kind': 'entropy'}
        elif (pair := pair_obstruction(profile, q, supplied)) is not None:
            reason = {'kind': 'row_pair', 'rows': pair}
        elif linear and r < q-1 and (coeff := linear_obstruction(profile, q, supplied)) is not None:
            reason = {'kind': 'linear', 'coefficients': coeff}
        elif r == q-1:
            z = collision(profile)
            if z is None:
                return profile
            reason = {'kind': 'collision', 'z': z}
        else:
            for child in splits(profile, q, supplied, allowed):
                result = visit(child)
                if result is not None:
                    return result
            reason = {'kind': 'branch'}
        dead[profile] = reason
        reasons[reason['kind']] += 1
        return None

    try:
        witness = visit((n,))
        verdict = 'SAT' if witness is not None else 'UNSAT'
    except BudgetExceeded:
        witness = None
        verdict = 'UNKNOWN'
    result = {'format': 1, 'q': q, 'n': n, 'verdict': verdict,
              'linear_reduction': linear,
              'capacity_premises': {str(k): v for k, v in sorted(supplied.items())},
              'stats': dict(stats, nodes=calls, closed_states=len(dead),
                            leaves=dict(reasons), seconds=round(time.monotonic()-started, 6))}
    if witness is not None:
        result['matrix'] = sign_matrix(witness)
    if verdict == 'UNSAT' and keep_proof:
        result['proof'] = [{'profile': list(p), **why} for p, why in dead.items()]
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('q', type=int)
    ap.add_argument('n', type=int)
    ap.add_argument('--bounds', default='{}', help='JSON capacity premises, e.g. {"7":10}')
    ap.add_argument('--nodes', type=int, default=100000)
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--linear', action='store_true', help='test four-row linear dependencies')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = solve(args.q, args.n, {int(k): v for k, v in json.loads(args.bounds).items()},
                   args.nodes, args.seconds, linear=args.linear)
    opener = gzip.open if args.output.suffix == '.gz' else open
    with opener(args.output, 'wt') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('proof', 'matrix')}))
    return 2 if result['verdict'] == 'UNKNOWN' else 0


if __name__ == '__main__':
    raise SystemExit(main())
