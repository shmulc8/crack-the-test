#!/usr/bin/env python3
"""Verify the construction upper bound A269706(8) <= 94.
Contributed by Shmulik Cohen, Sep 09 2026; developed with AI assistance.
This program checks the construction upper bound only.
"""
from itertools import product
from pathlib import Path
import json

def verify(data):
    if data.get('sequence') != 'A269706' or data.get('n') != 8:
        raise ValueError('Expected A269706 at n=8')
    points = data['points']
    if data.get('cardinality') != 94 or len(points) != 94:
        raise ValueError('Expected 94 points')
    if any(len(p) != 3 or any(type(x) is not int or not 0 <= x < 8 for x in p) for p in points):
        raise ValueError('Coordinates must be integers in [0,7]^3')
    if len(set(map(tuple, points))) != 94:
        raise ValueError('Repeated point')
    uncovered = [v for v in product(range(8), repeat=3)
                 if not any(sum(abs(x-y) for x,y in zip(v,p)) <= 1 for p in points)]
    if uncovered:
        raise ValueError(f'{len(uncovered)} uncovered vertices')
    return {'status':'PASS', 'sequence':'A269706', 'n':8,
            'selected':94, 'covered':512, 'upper_bound':94}

if __name__ == '__main__':
    data = json.loads((Path(__file__).resolve().parent.parent / 'witness-94.json').read_text())
    print(json.dumps(verify(data), sort_keys=True))
