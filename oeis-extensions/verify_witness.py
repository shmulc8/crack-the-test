"""Independent, standard-library-only geometry checks; no solver imports.

Usage: python3 verify_witness.py A350547 witness.json
JSON requires points, n for finite boards, and metric_sign for A350547.
This verifies a construction, never optimality.
"""
import itertools
import json
import sys

if not __debug__:
    raise RuntimeError('Run this verifier without Python -O or -OO.')


def verify(sequence, data):
    points = [tuple(p) for p in data['points']]
    assert points and all(all(type(c) is int for c in p) for p in points)
    assert len(points) == len(set(points)), 'Repeated point'
    if 'cardinality' in data:
        assert data['cardinality'] == len(points)
    n = data.get('n')
    if sequence == 'A350547':
        sign = data['metric_sign']
        assert sign in (-1, 1)
        assert all(len(p) == 2 and max(abs(p[0]), abs(p[1]), abs(p[0] + sign*p[1])) <= n for p in points)
        def distance(p, q):
            x, y = p[0]-q[0], p[1]-q[1]
            return x*x + y*y + sign*x*y
        for a, b, c in itertools.combinations(points, 3):
            assert not distance(a,b) == distance(a,c) == distance(b,c), ('Equilateral triangle', a,b,c)
    elif sequence == 'A386493':
        assert all(len(p) == 2 for p in points)
        if n is not None:
            assert len(points) == n, 'Wrong number of points'
        def distance(p, q):
            return sum((x-y)**2 for x,y in zip(p,q))
        diameter = max((distance(a,b) for a,b in itertools.combinations(points,2)), default=0)
        assert diameter <= data['squared_diameter']
        for a in points:
            distances = [distance(a,b) for b in points if b != a]
            assert len(distances) == len(set(distances)), ('Repeated distance at apex', a)
        return {'sequence': sequence, 'points': len(points), 'actual_squared_diameter': diameter, 'status': 'valid construction only'}
    elif sequence == 'A234349':
        assert all(len(p)==2 and p[0]>=0 and p[1]>=0 and sum(p)<n for p in points)
        for a,b,c in itertools.combinations(points,3):
            assert (b[0]-a[0])*(c[1]-a[1]) != (b[1]-a[1])*(c[0]-a[0]), ('Collinear',a,b,c)
    elif sequence == 'A279404':
        assert all(len(p)==2 and all(0<=c<n for c in p) for p in points)
        families = [{p[0] for p in points}, {p[1] for p in points}, {(p[0]+p[1])%n for p in points}, {(p[0]-p[1])%n for p in points}]
        assert all(len(f)==len(points) for f in families), 'Attacking queens'
        for x,y in itertools.product(range(n),repeat=2):
            assert x in families[0] or y in families[1] or (x+y)%n in families[2] or (x-y)%n in families[3], ('Uncovered',x,y)
    elif sequence == 'A356649':
        assert all(len(p)==3 and all(0<=c<n for c in p) for p in points)
        covered = set(points)
        for p in points:
            for axis in range(3):
                for step in (-1,1):
                    q=list(p)
                    q[axis]=(q[axis]+step)%n
                    covered.add(tuple(q))
        assert len(covered)==n**3, ('Uncovered count',n**3-len(covered))
    else:
        raise ValueError(sequence)
    return {'sequence':sequence,'n':n,'points':len(points),'status':'valid construction only'}


if __name__ == '__main__':
    with open(sys.argv[2]) as source:
        data=json.load(source)
    print(json.dumps(verify(sys.argv[1],data),sort_keys=True))
