#!/usr/bin/env python3
"""Native PySAT feasibility search for a fixed cardinality."""
import argparse, json, time
from pathlib import Path
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver


def classes(n, r, c):
    return (r, c, (r + c) % n, (r - c) % n)


def run(n, k, timeout=None, solver_name="cadical195"):
    if timeout is None:
        timeout = 300
    N = n * n
    vid = lambda r, c: 1 + r * n + c
    groups = {}
    for r in range(n):
        for c in range(n):
            for kind, value in enumerate(classes(n, r, c)):
                groups.setdefault((kind, value), []).append(vid(r, c))
    clauses = [[vid(0, 0)]]
    for values in groups.values():
        for i in range(len(values)):
            for j in range(i):
                clauses.append([-values[i], -values[j]])
    for r in range(n):
        for c in range(n):
            clauses.append([vid(rr, cc) for rr in range(n) for cc in range(n)
                            if any(a == b for a, b in zip(classes(n, rr, cc),
                                                          classes(n, r, c)))])
    enc = CardEnc.atmost(list(range(1, N + 1)), bound=k,
                         top_id=N, encoding=EncType.seqcounter)
    clauses.extend(enc.clauses)
    started = time.monotonic()
    with Solver(name=solver_name, bootstrap_with=clauses) as solver:
        status = solver.solve_limited(expect_interrupt=True)
        elapsed = time.monotonic() - started
        points = []
        if status:
            model = set(x for x in solver.get_model() if x > 0)
            points = [[r, c] for r in range(n) for c in range(n)
                      if vid(r, c) in model]
    outcome = "sat" if status is True else "unsat" if status is False else "unknown"
    return {"n": n, "target": k, "sat": status, "status": outcome,
            "elapsed_s": round(elapsed, 3), "points": points,
            "clauses": len(clauses)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int); ap.add_argument("k", type=int)
    ap.add_argument("--solver", default="cadical195"); ap.add_argument("--out", type=Path)
    a = ap.parse_args(); result = run(a.n, a.k, solver_name=a.solver)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if a.out: a.out.write_text(text)
    else: print(text, end="")
    print(f"n={a.n} k={a.k} sat={result['sat']} elapsed_s={result['elapsed_s']}")


if __name__ == "__main__": main()
