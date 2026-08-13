# Reproducibility guide

This repository has two evidence levels: fast checks suitable for every clone,
and the complete lower-bound computation.

## Fast verification

From the repository root, run `./test.sh`. It verifies every certificate with
independent checkers, requires broken controls to fail, compares the enumerator
with direct Python combinations on complete small instances, tests canonical
representatives and split unions, and runs safe-Rust controls when available.
The expected terminal line is `ALL CHECKS PASSED`.

## Complete decisive computation

The C and Rust runs each create a new directory that they refuse to overwrite:

```sh
cd enumerate
./run_8x14_audit.sh /absolute/path/to/audit-c-8x14-YYYYMMDD
./run_8x14_rust_audit.sh /absolute/path/to/audit-rust-8x14-YYYYMMDD
```

Each bundle contains the exact source and binary, environment and commit data,
ten complete partition logs, `CHECK.txt`, and `SHA256SUMS`. Validation requires
partitions 0 through 9, zero solutions in every partition, and the common
depth-0-through-6 vector `[0,1,6,18,143,1082,11364]`. For the published
comparison, every full Rust node vector must equal its C counterpart.

On the recorded arm64 Mac, ten concurrent workers completed each language's
run in roughly six minutes. Hardware affects timing, not node vectors.

## Bounded experiment for the next case

The C enumerator also has a portable q = 9 path and a dynamic frontier driver.
This supports reproducible feasibility measurements for 9×16, but no complete
9×16 nonexistence computation is claimed.

```sh
cd enumerate
cc -O2 -Wall -Wextra -Wpedantic -o enum enum.c
./enum 9 15 --maxsol 1 --report 99999 \
  --prefix 0,3,12,23,45,84,99,120,127,153,174,180,197,214,218
python3 frontier_run.py ./enum 9 16 \
  --frontier-depth 6 --sample 24 --seed 20260811 --workers 10 \
  --source enum.c --output /absolute/path/to/q9-sample-YYYYMMDD
```

The first command is a known-positive control derived from the published 9×15
certificate. The second uniformly samples canonical depth-six prefixes and
retains the frontier, selected units, complete logs, progress, environment,
and summary. The driver refuses to estimate total work unless every selected
unit completes; this prevents timeouts in unusually expensive branches from
silently biasing the estimate downward. Omit `--sample` only when intentionally
running the complete frontier.

## Archive before submission

The full audit directories are not committed because they include platform
binaries and large logs. The repository records results and hashes, but that
does not provide durable access to the raw evidence.

Before submission:

1. Create a clean release commit and tag.
2. Run both audit scripts from that tag into new directories.
3. Verify each manifest with `shasum -a 256 -c SHA256SUMS`.
4. Compare all ten complete node vectors between C and Rust.
5. Deposit both unmodified bundles in Zenodo or another durable archive.
6. Add the resulting DOI to the manuscript and release notes.

Do not describe the bundles as publicly archived until the DOI resolves.

## Remaining independence limitation

The C and Rust programs are separate implementations, but they deliberately
share the same enumeration strategy and proof. A third-party implementation
using a different formulation, preferably emitting a mechanically checkable
UNSAT proof, would be the strongest next validation.
