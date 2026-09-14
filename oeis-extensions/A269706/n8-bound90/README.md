# A269706(8): independently verified bounds 90–94

The final checker returned **PASS** for all 1,474 cases and 1,237,096 proof
nodes. The independently verified interval is **90 <= A269706(8) <= 94**.
The exact value remains unresolved.

The graph is the bounded 8 by 8 by 8 grid. A marker covers its own vertex
and its immediate axis neighbors. The saved 94-marker construction is the
upper bound; this directory concerns the lower bound only.

## Complete corner cases

Every corner has four possible dominators. If a dominating set contains a
corner, choose that corner as its forced dominator; otherwise choose one of
its selected inward neighbors. This gives eight distinct forced markers F.
Every unselected corner belongs to E = C minus F, where C is the set of eight
corners. The dominating set contains F and avoids E.

There are 4^8 = 65,536 possible choices of F. The cube's 48 rotations and
reflections group them into 1,474 representatives. The rule E = C minus F
is preserved by those symmetries, so the refined cases remain complete.
The dominating set itself may be asymmetric.

Some saved proofs use no initial exclusions. These prove a stronger
statement and also exclude the required refined case. The global checker
allows initial E only when E is a subset of C minus the canonical F.

## Checkable weighted bounds and branches

At every node, nonnegative integer weights are assigned only to vertices
not covered by F. Every allowed marker covers weight at most 1,000,000.
Total residual weight W therefore requires at least
`|F| + ceil(W / 1,000,000)` markers. If this exceeds 89, the node closes.

Otherwise the proof splits on an undecided marker c: one child selects c,
and the other forbids c. The children cover all possibilities. An uncovered
vertex with no allowed dominator also closes a node. The checker validates
every integer inequality, every exact child state, and the complete tree.

The proof search uses floating-point LPs to propose weights. Verification
uses only exact integers and does not require an optimization solver.

From the A269706 directory, run:

```sh
python3 n8-bound90/verify_upper.py
python3 n8-bound90/verify_global.py --workers 4
```

Only Python's standard library is required. This checks the complete corner
partition and every saved proof under `n8-binary-branch/global90/`. Any missing,
unfinished, or invalid case prevents a global PASS. The proof establishes a lower bound, not an exact value or publication priority.
The saved proof trees occupy approximately 10.98 GB.
