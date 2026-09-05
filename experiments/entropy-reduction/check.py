#!/usr/bin/env python3
"""Small certificate checker. Deliberately does not import the search program.

Capacity assumptions require previously checked lower-row certificates.
Certificate statistics and claimed search timings are ignored.
"""
from collections import Counter
from functools import lru_cache
from itertools import combinations, combinations_with_replacement, product
import argparse
import json
import gzip
from math import prod
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


@lru_cache(None)
def fiber_product(n, d, s):
    # Count actual subsets instead of using the generator's hypergeometric
    # formula. The problem sizes for this experimental checker are small.
    counts = Counter(sum(i < d for i in subset)
                     for subset in combinations(range(n), s))
    N = sum(counts.values())
    return N, prod(a**a for a in counts.values())


def check_certificate(cert, established=None):
    established = established or {}
    require(cert.get('format') == 1 and cert.get('verdict') == 'UNSAT',
            'only complete format-1 UNSAT certificates are accepted')
    q, n = cert['q'], cert['n']
    require(type(q) is int and type(n) is int and 2 <= q <= 8 and 2 <= n <= 16,
            'unsupported parameters')
    premises = {int(k): v for k, v in cert['capacity_premises'].items()}
    for k, upper in premises.items():
        known = min(2**(k-1), established.get(k, 2**(k-1))) if k >= 1 else 0
        require(1 <= k < q and type(upper) is int and upper >= known,
                f'unproved capacity premise E({k}) <= {upper}')

    def upper(k):
        return min(2**(k-1), premises.get(k, 2**(k-1)))

    low = max(1, n-upper(q-1))

    @lru_cache(None)
    def viable(weights):
        if tuple(sorted(weights)) != weights or any(d < low or d > n//2 for d in weights):
            return False
        slots = q-1-len(weights)
        for suffix in combinations_with_replacement(range(weights[-1] if weights else low, n//2+1), slots):
            full = weights + suffix
            failed = False
            for s in range(1, n//2+1):
                factors = [fiber_product(n, d, s) for d in full]
                N = factors[0][0]
                if prod(v for _, v in factors) > N**((q-2)*N):
                    failed = True
                    break
            if not failed:
                return True
        return False

    nodes = {}
    for entry in cert['proof']:
        profile = tuple(entry['profile'])
        require(profile not in nodes, 'duplicate proof state')
        require(profile and len(profile) & (len(profile)-1) == 0 and
                len(profile) <= 2**(q-1) and sum(profile) == n and
                all(type(c) is int and c >= 0 for c in profile), 'malformed profile')
        nodes[profile] = entry
    seen = set()

    def visit(profile):
        if profile in seen:
            return
        require(profile in nodes, f'missing proof state {profile}')
        entry = nodes[profile]
        r = len(profile).bit_length()-1
        weights = tuple(sum(c for t, c in enumerate(profile) if (t >> j) & 1)
                        for j in range(r))
        kind = entry.get('kind')
        if kind == 'capacity':
            require(max(profile) > upper(q-r), 'false capacity obstruction')
        elif kind == 'entropy':
            require(not viable(weights), 'false entropy obstruction')
        elif kind == 'row_pair':
            i, j = entry['rows']
            require(type(i) is int and type(j) is int and 0 <= i < j < r,
                    'invalid row-pair indices')
            counts = [0, 0]
            for t, c in enumerate(profile):
                equal = ((t // (2**i)) % 2) == ((t // (2**j)) % 2)
                counts[int(equal)] += c
            require(max(counts) > upper(q-1), 'false row-pair obstruction')
        elif kind == 'collision':
            require(r == q-1, 'collision before all rows are chosen')
            types = [t for t, count in enumerate(profile) for _ in range(count)]
            z = entry['z']
            require(len(z) == n and all(type(a) is int and a in (-1, 0, 1) for a in z)
                    and any(z) and sum(z) == 0, 'invalid balanced relation')
            require(all(sum(a*((t >> j) & 1) for a, t in zip(z, types)) == 0
                        for j in range(r)), 'relation is not in the kernel')
        elif kind == 'linear':
            coefficients = entry['coefficients']
            require(len(coefficients) == r+1 and
                    all(type(a) is int for a in coefficients) and any(coefficients),
                    'invalid row dependence')
            block_size = 0
            for t, count in enumerate(profile):
                column = [1]+[-1 if (t // (2**j)) % 2 else 1 for j in range(r)]
                if sum(a*b for a, b in zip(coefficients, column)) == 0:
                    block_size += count
            # On this block, delete any row with a nonzero coefficient: its
            # measurements are determined by the others. Remaining rows are
            # still sign rows, so the established E(q-1) bound applies.
            require(block_size > upper(q-1), 'false linear obstruction')
        elif kind == 'branch':
            require(r < q-1, 'branch at terminal depth')
            bound = upper(q-r-1)
            # Enumerate the full Cartesian product. Exclusions are checked
            # here independently, rather than trusting emitted child lists.
            for chosen in product(*(range(c+1) for c in profile)):
                other = tuple(c-a for c, a in zip(profile, chosen))
                if max(chosen+other) > bound:
                    continue
                weight = sum(chosen)
                if weight*2 > n or (weight*2 == n and chosen > other):
                    continue
                if not viable(weights+(weight,)):
                    continue
                visit(other+chosen)
        else:
            raise ValueError('unknown proof rule')
        seen.add(profile)

    visit((n,))
    require(len(seen) == len(nodes), 'unreachable extra proof states')
    return {'q': q, 'n': n, 'checked_states': len(seen), 'derived_capacity': n-1}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('certificates', type=Path, nargs='+', help='lower-row premises first')
    args = ap.parse_args()
    established = {}
    for path in args.certificates:
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as stream:
            result = check_certificate(json.load(stream), established)
        k, e = result['q'], result['derived_capacity']
        established[k] = min(e, established.get(k, e))
        print(json.dumps(dict(result, certificate=str(path))))
    print('CERTIFICATE CHAIN VERIFIED')


if __name__ == '__main__':
    main()
