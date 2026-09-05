"""Independent controls for the experimental reduction and certificate checker."""
from copy import deepcopy
from itertools import combinations, product
import unittest

from check import check_certificate
from reduce import collision, entropy_obstruction, solve
from conditional import conditional_bound


def detecting(rows):
    """Direct ternary-kernel check, without subset-sum hashing."""
    n = len(rows[0])
    for z in product((-1, 0, 1), repeat=n):
        if any(z) and all(sum(a*b for a, b in zip(row, z)) == 0 for row in rows):
            return False
    return True


def brute_exists(q, n):
    cols = [(1,)+v for v in product((-1, 1), repeat=q-1)]
    if n > len(cols):
        return False
    for selected in combinations(cols, n):
        # An independent ordinary integer-vector subset-sum check.
        values = {tuple(sum(col[j] for col, bit in zip(selected, mask) if bit)
                        for j in range(q)) for mask in product((0, 1), repeat=n)}
        if len(values) == 2**n:
            return True
    return False


class ReductionTests(unittest.TestCase):
    def test_complete_small_instances(self):
        for q in range(2, 5):
            for n in range(2, 8):
                with self.subTest(q=q, n=n):
                    result = solve(q, n, max_nodes=50000, seconds=10)
                    self.assertNotEqual(result['verdict'], 'UNKNOWN')
                    self.assertEqual(result['verdict'] == 'SAT', brute_exists(q, n))
                    if result['verdict'] == 'SAT':
                        rows = [[1 if c == '+' else -1 for c in row] for row in result['matrix']]
                        self.assertTrue(detecting(rows))
                    else:
                        check_certificate(result)

    def test_larger_positive_controls(self):
        bounds = {3: 3, 4: 5, 5: 6}
        for q, n in [(5, 6), (6, 8)]:
            result = solve(q, n, {k: v for k, v in bounds.items() if k < q}, seconds=10)
            self.assertEqual(result['verdict'], 'SAT')
            self.assertTrue(detecting([[1 if c == '+' else -1 for c in row]
                                       for row in result['matrix']]))

    def test_entropy_boundary_and_obstruction(self):
        self.assertIsNone(entropy_obstruction(2, (1,)))  # equality is allowed
        self.assertEqual(entropy_obstruction(4, (2, 2)), 2)
        # This figure's binary columns have a collision of different sizes;
        # full sign columns remain detecting because cardinality is retained.
        self.assertIsNone(collision((0, 1, 1, 1)))

    def test_budget_is_unknown_and_has_no_proof(self):
        result = solve(4, 6, {3: 3}, max_nodes=0)
        self.assertEqual(result['verdict'], 'UNKNOWN')
        self.assertNotIn('proof', result)
        with self.assertRaises(ValueError):
            check_certificate(result)

    def test_missing_state_and_false_collision_rejected(self):
        cert = solve(4, 6)
        check_certificate(cert)
        bad = deepcopy(cert)
        bad['proof'] = bad['proof'][1:]
        with self.assertRaises(ValueError):
            check_certificate(bad)
        bad = deepcopy(cert)
        leaf = next(e for e in bad['proof'] if e['kind'] == 'collision')
        leaf['z'] = [0]*6
        with self.assertRaises(ValueError):
            check_certificate(bad)

    def test_false_pair_obstruction_rejected(self):
        cert = solve(4, 6, {3: 3})
        leaf = next(e for e in cert['proof'] if e['kind'] == 'row_pair')
        leaf['rows'] = [0, 0]
        with self.assertRaises(ValueError):
            check_certificate(cert, {3: 3})

    def test_false_entropy_and_unproved_premise_rejected(self):
        cert = solve(4, 6, {3: 3})
        with self.assertRaises(ValueError):
            check_certificate(cert)
        cert['proof'] = [{'profile': [6], 'kind': 'entropy'}]
        with self.assertRaises(ValueError):
            check_certificate(cert, {3: 3})

    def test_conditional_entropy_preserves_positive_prefixes(self):
        bounds = {3: 3, 4: 5, 5: 6}
        for q, n in [(4, 5), (5, 6), (6, 8)]:
            relevant = {k: v for k,v in bounds.items() if k < q}
            result = solve(q, n, relevant)
            self.assertEqual(result['verdict'], 'SAT')
            for depth in range(1, q-1):
                profile = [0]*(2**depth)
                for i in range(n):
                    t = sum((result['matrix'][j+1][i] == '-')*(2**j) for j in range(depth))
                    profile[t] += 1
                for s in range(1, n//2+1):
                    self.assertFalse(conditional_bound(q, tuple(profile), relevant, s)['rejects'])

    def test_linear_search_matches_complete_small_enumeration(self):
        for q in range(2, 5):
            for n in range(2, 8):
                result = solve(q, n, linear=True)
                self.assertNotEqual(result['verdict'], 'UNKNOWN')
                self.assertEqual(result['verdict'] == 'SAT', brute_exists(q, n))
                if result['verdict'] == 'UNSAT':
                    check_certificate(result)
        for q, n in [(5, 6), (6, 8)]:
            result = solve(q, n, {k:v for k,v in {3:3,4:5,5:6}.items() if k<q}, linear=True)
            self.assertEqual(result['verdict'], 'SAT')
            self.assertTrue(detecting([[1 if c=='+' else -1 for c in row] for row in result['matrix']]))

    def test_linear_witness_and_corruption(self):
        cert = solve(5, 7, {3:3, 4:5}, linear=True)
        check_certificate(cert, {3:3, 4:5})
        leaf = next(e for e in cert['proof'] if e['kind'] == 'linear')
        original = leaf['coefficients'][:]
        # The checker verifies the equation, not the generator's coefficient
        # alphabet or cached zero-type table.
        leaf['coefficients'] = [3*a for a in original]
        check_certificate(cert, {3:3, 4:5})
        for bad in ([0]*len(original), [1]+[0]*(len(original)-1)):
            leaf['coefficients'] = bad
            with self.assertRaises(ValueError):
                check_certificate(cert, {3:3, 4:5})


if __name__ == '__main__':
    unittest.main()
