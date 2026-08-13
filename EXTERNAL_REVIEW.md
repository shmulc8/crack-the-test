# External mathematical review handoff

No message has been sent. This is a copy-ready brief for a mathematician who
may be willing to review the result before journal submission.

## Short note

Subject: Could you sanity-check a computer-assisted hypercube result?

I have an exhaustive computation indicating that the metric dimensions of the
14- and 15-dimensional hypercubes are both 9. The public repository contains a
self-contained manuscript, two implementations of the decisive enumeration,
small complete controls, explicit upper-bound certificates, and a detailed
proof of every pruning step.

The review I need most is mathematical rather than editorial:

1. Is the reduction from resolving sets to normalized detecting matrices fully
   correct?
2. Is the lexicographically minimal prefix argument in Proposition 4 sound for
   the affine symmetry group used by the program?
3. Does the ten-way partition argument cover every branch exactly once?
4. Have I missed prior work that already proves either exact value or uses this
   same exhaustive canonical-prefix method?

If you have time to run code, `./test.sh` is the short check. The complete C or
Rust run takes about six minutes with ten workers on the machine used for the
recorded experiment. I would be grateful for blunt feedback, especially any
counterexample to an argument or any missing citation.

Repository: https://github.com/shmulc8/crack-the-test

## Reviewer map

- Main theorem and reduction: `paper/main.tex`, Sections 2 and 6.
- Implementation-tied proof: `enumerate/ENUMERATION_PROOF.md`.
- Recorded decisive totals: `enumerate/RESULT.md`.
- Fast controls: `./test.sh`.
- Complete C bundle: `enumerate/run_8x14_audit.sh NEW_DIRECTORY`.
- Complete Rust bundle: `enumerate/run_8x14_rust_audit.sh NEW_DIRECTORY`.
- Certificates: `matrices/`.

## Claims to keep separate

- The explicit upper bounds are certified directly by the matrix files.
- The exact values additionally rely on exhaustive nonexistence of an 8 by 14
  detecting matrix.
- C/Rust agreement reduces implementation risk but is not a distinct
  mathematical argument.
- No durable public archive DOI for the raw decisive bundles is claimed yet.
