# Submitted OEIS update for A269706

Status: proposed for editorial review on September 14, 2026 (edit #24, submission #25).
Receipt: https://oeis.org/history/view?seq=A269706&v=25
Not yet approved.

## FORMULA

90 <= a(8) <= 94. - Shmulik Cohen, Sep 14 2026

## LINKS

Shmulik Cohen, Verified bounds for the 8 × 8 × 8 grid: construction,
exact-integer checkers, and lower-bound certificates.

Submitted evidence URL:
https://github.com/shmulc8/crack-the-test/tree/a0641c912a018d43b92720cb6ddd8b62ab86f8ed/oeis-extensions/A269706

The versioned proof release is linked from the package.

## Editorial explanation

The upper bound is an explicit 94-vertex dominating set. The lower bound
excludes all sets of at most 89 vertices through a complete partition into
1,474 corner-choice symmetry classes and exact-integer branching certificates.
Verification uses Python's standard library. The exact value is unresolved;
please leave DATA unchanged. We do not claim first-publication priority.
