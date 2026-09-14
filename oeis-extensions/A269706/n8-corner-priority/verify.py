"""Exact, standard-library checker for disjoint cover proof trees."""
import argparse
import json
from itertools import product
from pathlib import Path

GRID = list(product(range(8), repeat=3))
INDEX = {p: i for i, p in enumerate(GRID)}
HOODS = [{j for j, q in enumerate(GRID) if sum(abs(a-b) for a,b in zip(p,q)) <= 1} for p in GRID]
M = 1000000


def indices(values):
    if not isinstance(values, list) or any(type(i) is not int or not 0 <= i < 512 for i in values):
        raise ValueError('invalid center indices')
    if len(set(values)) != len(values):
        raise ValueError('duplicate center')
    return set(values)


def verify(proof, root, target):
    if proof.get('status') != 'UNSAT' or proof.get('target') != target or type(proof.get('target')) is not int:
        raise ValueError('not a proof for the requested target')
    if proof.get('case_index') != root.get('case_index') or proof.get('denominator') != M:
        raise ValueError('root metadata mismatch')
    fixed = {INDEX[tuple(p)] for p in root['fixed_points']}
    excluded = {INDEX[tuple(p)] for p in root.get('excluded_points', [])}
    if len(fixed) != 8 or {INDEX[tuple(p)] for p in proof['fixed_points']} != fixed:
        raise ValueError('root marker mismatch')
    if fixed & excluded:
        raise ValueError('forced and excluded roots overlap')
    if 'excluded_points' in proof and {INDEX[tuple(p)] for p in proof['excluded_points']} != excluded:
        raise ValueError('root exclusion metadata mismatch')
    tree = proof['proof_tree']
    cursor = 0

    def visit(expected_f, expected_e):
        nonlocal cursor
        if cursor >= len(tree):
            raise ValueError('truncated tree')
        node = tree[cursor]; cursor += 1
        f, e = indices(node['fixed']), indices(node['excluded'])
        if f != expected_f or e != expected_e or f & e:
            raise ValueError('incorrect child partition')
        covered = set().union(*(HOODS[i] for i in f))
        support = set(range(512)) - covered
        status = node['status']
        if status == 'EMPTY':
            v = node.get('branch_vertex')
            if type(v) is not int or v not in support or HOODS[v] - e:
                raise ValueError('invalid empty neighborhood leaf')
            return
        weights = {}
        for key, value in node['weights'].items():
            if not isinstance(key, str) or not key.isdigit() or str(int(key)) != key:
                raise ValueError('invalid weight key')
            if type(value) is not int or value < 0 or int(key) not in support:
                raise ValueError('invalid weight support or value')
            weights[int(key)] = value
        for i, hood in enumerate(HOODS):
            if i not in e and sum(weights.get(j, 0) for j in hood) > M:
                raise ValueError('allowed marker exceeds weight capacity')
        total = sum(weights.values())
        lower = len(f) + (total + M - 1) // M
        if node['weight_sum'] != total or node['combined_lower_bound'] != lower:
            raise ValueError('weight or lower-bound metadata mismatch')
        if status == 'BOUND':
            if lower <= target:
                raise ValueError('insufficient lower bound')
            return
        if status == 'SPLIT':
            c = node['branch_center']
            if type(c) is not int or not 0 <= c < 512 or c in f or c in e:
                raise ValueError('invalid binary branch center')
            visit(f | {c}, e)
            visit(f, e | {c})
            return
        if status != 'BRANCH':
            raise ValueError('unresolved node')
        v = node['branch_vertex']
        if type(v) is not int or v not in support:
            raise ValueError('branch vertex already covered')
        points = node['branch_points']
        if indices(points) != HOODS[v] - e or not points:
            raise ValueError('branch does not exhaust allowed neighborhood')
        prefix = set()
        for c in points:
            visit(f | {c}, e | prefix)
            prefix.add(c)

    visit(fixed, excluded)
    if cursor != len(tree):
        raise ValueError('unreachable tree nodes')
    return {'status': 'PASS', 'case_index': root['case_index'], 'target': target, 'nodes': cursor}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('proof', type=Path)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--target', type=int, required=True)
    args = ap.parse_args()
    print(json.dumps(verify(json.loads(args.proof.read_text()), json.loads(args.root.read_text()), args.target)))
