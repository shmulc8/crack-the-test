#!/usr/bin/env python3
"""Incremental-SAT CEGAR for a q x n {+-1} detecting matrix (CaDiCaL backend).

Same problem, state-file format, and symmetry class as cegar.py, but the SAT
solver lives across iterations: each new banned null is added as clauses to
the running solver, so learned conflict clauses accumulate instead of being
discarded on every counterexample round-trip.

Ban constraint per null z (support S, signs sigma, |S|=s even, t=s/2):
  OR_j d_j,  d_j -> (row_j sum over signed support != t)
via a bidirectional totalizer per (z, row): outputs o_k <=> (sum >= k), and
clause (~d_j | o_{t+1} | ~o_t).

usage: cegar2.py <q> <n> [--state F] [--preban W] [--iters I] [--dimacs F]
"""
import sys, time, itertools, os
from pysat.solvers import Cadical195

q = int(sys.argv[1]); n = int(sys.argv[2])
args = dict(zip(sys.argv[3::2], sys.argv[4::2]))
STATE = args.get("--state")
PREBAN = int(args.get("--preban", 4))
ITERS = int(args.get("--iters", 10 ** 6))
DIMACS = args.get("--dimacs")

def count_nulls(W, cap=100000):
    nl = n // 2; nr = n - nl
    left = {}
    for zl in itertools.product((-1, 0, 1), repeat=nl):
        key = tuple(sum(W[j][i] * zl[i] for i in range(nl)) for j in range(q))
        left.setdefault(key, []).append(zl)
    nulls = []
    for zr in itertools.product((-1, 0, 1), repeat=nr):
        key = tuple(-sum(W[j][nl + i] * zr[i] for i in range(nr)) for j in range(q))
        for zl in left.get(key, ()):
            z = zl + zr
            if any(z):
                if next(v for v in z if v) > 0:
                    nulls.append(z)
                    if len(nulls) >= cap: return nulls
    return nulls

nvars = 0
def newvar():
    global nvars; nvars += 1; return nvars
allcl = []
solver = Cadical195()
def clause(c):
    allcl.append(c); solver.add_clause(c)

v = [[newvar() for _ in range(n)] for _ in range(q)]  # true = +1

for i in range(n): clause([v[0][i]])
for j in range(q): clause([v[j][0]])

def lex_le(A, B, strict=False):
    """A <=_lex B for equal-length literal vectors (MSB first)."""
    p = newvar(); clause([p])  # prefix-equal so far
    for k in range(len(A)):
        clause([-p, -A[k], B[k]])
        if k < len(A) - 1 or strict:
            p2 = newvar()
            clause([-p, -A[k], -B[k], p2])
            clause([-p, A[k], B[k], p2])
            p = p2
    if strict: clause([-p])

for j in range(1, q - 1):
    lex_le([v[j][i] for i in range(n - 1, -1, -1)], [v[j + 1][i] for i in range(n - 1, -1, -1)])
for i in range(1, n - 1):
    lex_le([v[j][i] for j in range(q - 1, -1, -1)], [v[j][i + 1] for j in range(q - 1, -1, -1)], strict=True)

def totalizer(lits):
    """Bidirectional totalizer: returns outputs o (1-indexed conceptually),
    o[k-1] <=> at least k of lits are true."""
    if len(lits) == 1: return [lits[0]]
    mid = len(lits) // 2
    A = totalizer(lits[:mid]); B = totalizer(lits[mid:])
    p, r = len(A), len(B)
    R = [newvar() for _ in range(p + r)]
    for a in range(p + 1):
        for b in range(r + 1):
            if a + b >= 1:  # sum >= a+b  =>  R[a+b-1]
                c = [R[a + b - 1]]
                if a: c.append(-A[a - 1])
                if b: c.append(-B[b - 1])
                clause(c)
            if a + b < p + r:  # R[a+b]  =>  sum >= a+b+1
                c = [-R[a + b]]
                if a < p: c.append(A[a])
                if b < r: c.append(B[b])
                clause(c)
    return R

banned = set()
statef = None
def ban(z, persist=True):
    if z in banned or tuple(-x for x in z) in banned: return
    banned.add(z)
    sup = [(i, z[i]) for i in range(n) if z[i]]
    if sum(s for _, s in sup) % 2: return
    t = len(sup) // 2
    ds = []
    for j in range(q):
        u = [v[j][i] if sg > 0 else -v[j][i] for i, sg in sup]
        o = totalizer(u)
        d = newvar()
        clause([-d, o[t], -o[t - 1]])  # d -> (sum >= t+1 or sum <= t-1)
        ds.append(d)
    clause(ds)
    if statef and persist:
        statef.write("".join("+" if x > 0 else "-" if x < 0 else "." for x in z) + "\n")
        statef.flush()

if PREBAN >= 2:
    for s in range(2, PREBAN + 1, 2):
        for sup in itertools.combinations(range(n), s):
            for signs in itertools.product((-1, 1), repeat=s - 1):
                sg = (1,) + signs
                if sum(sg): continue
                z = [0] * n
                for i, x in zip(sup, sg): z[i] = x
                ban(tuple(z), persist=False)
    print(f"pre-banned {len(banned)} nulls of weight <= {PREBAN}", flush=True)

if STATE:
    if os.path.exists(STATE):
        with open(STATE) as fh:
            for line in fh:
                line = line.strip()
                if len(line) == n:
                    ban(tuple(1 if c == "+" else -1 if c == "-" else 0 for c in line), persist=False)
        print(f"state loaded, total bans {len(banned)}", flush=True)
    statef = open(STATE, "a")

if "--dump-only" in sys.argv:
    with open(DIMACS, "w") as fh:
        fh.write(f"p cnf {nvars} {len(allcl)}\n")
        for c in allcl: fh.write(" ".join(map(str, c)) + " 0\n")
    print(f"dumped {len(allcl)} clauses / {nvars} vars to {DIMACS}", flush=True)
    sys.exit(0)

t0 = time.time()
for it in range(ITERS):
    if not solver.solve():
        print(f"UNSAT PROVED at iter={it} bans={len(banned)} vars={nvars} t={time.time()-t0:.0f}s", flush=True)
        if DIMACS:
            with open(DIMACS, "w") as fh:
                fh.write(f"p cnf {nvars} {len(allcl)}\n")
                for c in allcl: fh.write(" ".join(map(str, c)) + " 0\n")
            print(f"dimacs written to {DIMACS} for certificate rerun", flush=True)
        sys.exit(3)
    model = set(l for l in solver.get_model() if l > 0)
    W = [[1 if v[j][i] in model else -1 for i in range(n)] for j in range(q)]
    nulls = count_nulls(W)
    print(f"iter={it} bans={len(banned)} nulls={len(nulls)} vars={nvars} t={time.time()-t0:.0f}s", flush=True)
    if not nulls:
        print("SAT: detecting matrix found")
        for j in range(q): print("".join("+" if x > 0 else "-" for x in W[j]))
        sys.exit(0)
    nulls.sort(key=lambda z: sum(x != 0 for x in z))
    for z in nulls[:300]: ban(z)
print("iteration cap reached"); sys.exit(5)
