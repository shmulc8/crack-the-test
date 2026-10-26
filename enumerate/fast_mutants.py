#!/usr/bin/env python3
"""Mutation test for fast_oracle_check.py: each deliberately broken copy of
enum_fast.c must fail the oracle. A mutant that passes would mean the oracle
cannot see that class of bug.

Usage: fast_mutants.py WORKDIR
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLAGS = ["--clique", "1", "--exact-clique", "--fast-canon"]

# (name, original text, replacement, mitm anchor used for the oracle run[, extra oracle args])
MUTANTS = [
    ("clique bound asks for one column too many",
     "if (!has_clique(A, all, n - depth))", "if (!has_clique(A, all, n - depth + 1))", 1),
    ("colour bound off by one",
     "if (colour[i] < k) return 0;", "if (colour[i] <= k) return 0;", 1),
    ("T(R) list loses its minus branch",
     "dst[3 * i + 2] = src[i] - c;", "dst[3 * i + 2] = src[i] + c;", 1),
    ("T(P) hash loses its minus branch",
     "t_add(d, x); t_add(d, x + c); t_add(d, x - c);", "t_add(d, x); t_add(d, x + c); t_add(d, x + c);", 3),
    ("adjacency skips the a + b test",
     "if (in_T(depth, dj - di) || in_T(depth, dj + di)) continue;", "if (in_T(depth, dj - di)) continue;", 1),
    ("child list ignores the graph",
     "if (A[ci].w[cj >> 6] >> (cj & 63) & 1) cand[depth + 1][m++] = L[cj];", "cand[depth + 1][m++] = L[cj];", 1),
    ("minimal image follows only the first tying element",
     "if (min_image_less(X, k, cur, i + 1, A2, B2, n2, used | 1u << x)) return 1;",
     "return min_image_less(X, k, cur, i + 1, A2, B2, n2, used | 1u << x);", 1),
    ("minimal image never explores ties",
     "if (p > cur[i]) return 0;", "if (p >= cur[i]) return 0;", 1),
    ("lowbits takes the highest bits",
     "for (int i = 0; i < 8 && got < j; i++) if (b >> i & 1) { out |= 1 << i; got++; }",
     "for (int i = 7; i >= 0 && got < j; i--) if (b >> i & 1) { out |= 1 << i; got++; }", 1),
    ("lookahead break off by one",
     "if (nlive - ci < n - depth) break;", "if (nlive - ci <= n - depth) break;", 1),
    ("pivot table loses the column renormalisation",
     "if (b_R ^ b_other) new_t |= (1 << out_bit);", "if (b_other) new_t |= (1 << out_bit);", 1, ["--pivots"]),
    ("minimal image skips the last pivot",
     "for (int piv = 0; piv < max_pivots; piv++) {\n        int transformed[MAXN], X[MAXN];",
     "for (int piv = 0; piv < max_pivots - 1; piv++) {\n        int transformed[MAXN], X[MAXN];", 1, ["--pivots"]),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    source = (HERE / "enum_fast.c").read_text()
    survivors = []
    for i, (name, old, new, anchor, *more) in enumerate(MUTANTS):
        oracle_args = more[0] if more else []
        if source.count(old) != 1:
            raise AssertionError(f"mutant '{name}': pattern found {source.count(old)} times")
        src = work / f"mutant{i}.c"
        binary = work / f"mutant{i}"
        src.write_text(source.replace(old, new))
        subprocess.run(["cc", "-O2", "-o", str(binary), str(src)], check=True)
        result = subprocess.run(
            [sys.executable, str(HERE / "fast_oracle_check.py"), *oracle_args, str(binary), *FLAGS, "--mitm", str(anchor)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            survivors.append(name)
            print(f"SURVIVED: {name}")
        else:
            last = (result.stderr.strip().splitlines() or ["?"])[-1]
            print(f"killed:   {name}  ({last[:110]})")
    if survivors:
        print(f"{len(survivors)} mutant(s) survived")
        return 1
    print(f"ALL {len(MUTANTS)} MUTANTS KILLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
