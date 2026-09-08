# A279404: 11-queen constructions at n=19 and n=20

The [19x19 construction](logs/n19-k11.json) and
[20x20 construction](logs/n20-k11.json) each have 11 queens.
Coordinates are zero-based, modulo n. No two queens share a row, column,
sum diagonal, or difference diagonal. Every board cell shares at least
one of these four classes with a selected queen, so the placements are
independent dominating sets.

Therefore A279404(19)<=11 and A279404(20)<=11. The existing ordinary
domination lower bounds [A279402(19)=A279402(20)=10](https://oeis.org/A279402/b279402.txt)
also apply to independent domination. Both values are consequently in
[10,11]. This contribution supplies the upper-bound constructions; it
does not supply new lower-bound certificates or determine either exact term.

From the repository root, check these constructions with:

```sh
python3 oeis-extensions/validate_results.py
```
