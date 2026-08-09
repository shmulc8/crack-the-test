# RESULT: beta(Q_14) = 9
date: 2026-08-07

## Primary computation
The archived run used the `enum.c` implementation at commit `43d14d1` (then
built as `enum3`). The current source adds fail-closed argument, allocation and
capacity checks without changing the valid-run search. Command: `enum 8 14
--split 10 --splitdepth 6 --canondepth 8`, all 10 parts:
  DONE in 569.07s  nodes/depth: [0,1,6,18,143,1082,11364,12734,132789,1491018,10192494,20933585,1883143,3188,0]  total=34661565  rate=60909 nodes/s  canon=298295 skipped=909985
  DONE in 559.84s  nodes/depth: [0,1,6,18,143,1082,11364,12759,133408,1479521,9951393,20165300,1920265,1784,0]  total=33677044  rate=60155 nodes/s  canon=298556 skipped=917714
  DONE in 551.10s  nodes/depth: [0,1,6,18,143,1082,11364,12651,132536,1460334,9733262,19343246,1731305,2081,0]  total=32428029  rate=58842 nodes/s  canon=296648 skipped=909518
  DONE in 564.58s  nodes/depth: [0,1,6,18,143,1082,11364,12690,134013,1488809,10042661,20400110,1867516,3524,0]  total=33961937  rate=60154 nodes/s  canon=299074 skipped=917429
  DONE in 553.29s  nodes/depth: [0,1,6,18,143,1082,11364,12689,134517,1495359,10058303,20259100,1819633,6813,0]  total=33799028  rate=61087 nodes/s  canon=300649 skipped=920284
  DONE in 567.13s  nodes/depth: [0,1,6,18,143,1082,11364,12751,135554,1490436,9965989,20279614,1874277,3431,0]  total=33774666  rate=59553 nodes/s  canon=302447 skipped=925773
  DONE in 564.19s  nodes/depth: [0,1,6,18,143,1082,11364,12665,133583,1489231,10097928,20530712,1821635,2046,0]  total=34100414  rate=60442 nodes/s  canon=298818 skipped=915731
  DONE in 564.51s  nodes/depth: [0,1,6,18,143,1082,11364,12614,133150,1490242,10189064,20848271,1885229,3723,0]  total=34574907  rate=61248 nodes/s  canon=298709 skipped=908857
  DONE in 571.71s  nodes/depth: [0,1,6,18,143,1082,11364,12673,132025,1481572,10189480,21157557,2007961,6082,0]  total=34999964  rate=61220 nodes/s  canon=295300 skipped=902676
  DONE in 563.59s  nodes/depth: [0,1,6,18,143,1082,11364,12818,134569,1503467,10169974,20438209,1838879,4535,0]  total=34115065  rate=60531 nodes/s  canon=301800 skipped=917787
  => 10/10 parts: solutions found: 0
  => distinct partitioned search-tree nodes: 339,979,093
     The ten part totals add up to 340,092,619, but --splitdepth 6 means every
     part walks the whole frontier down to depth 6 before it skips anything, so
     those 12,614 nodes (0+1+6+18+143+1082+11364) are counted ten times over.
     Subtracting the nine duplicate copies leaves 339,979,093.

## Fresh fail-closed rerun

The complete ten-part computation was rerun on 2026-08-09 with the hardened
source at commit `6167a0f` and `enum.c` SHA-256
`23745a5cb5679f1d2c5b28383787d526782c5b293fefe2e8324b8aa98ddf9437`.
All ten node vectors exactly reproduced the primary computation above, all ten
processes exited successfully, and all ten reported zero solutions. The run
took 350.60--372.36 seconds per partition on Apple clang 21.0.0 / arm64 Darwin.

The rerun used `run_8x14_audit.sh`, which preserves the exact source and binary,
environment, complete logs, structural validation, and SHA-256 manifest in a
new non-overwritten output directory. `check_partition_logs.py` required
exactly partitions 0--9, the common depth-6 frontier
`[0,1,6,18,143,1082,11364]`, one complete verdict per file, and no emitted
solution.

## Independent safe-Rust rerun

A standalone safe-Rust implementation, `enum.rs`, reproduced the complete
ten-part 8×14 computation on 2026-08-09. Its source SHA-256 was
`418fe199dbb8475e5d7a6859e538907d22507a82967da29542815feeab7574a3`.
All ten processes exited successfully, all ten found zero solutions, and every
full node vector matched the corresponding C partition exactly—not just the
common frontier or final verdict.

Built with rustc 1.94.0 / LLVM 21.1.8 using native CPU tuning, LTO, one codegen
unit and abort-on-panic, Rust averaged 358.93 seconds per partition against
365.10 seconds for the fresh C run on the same machine. Its slowest partition
took 365.57 seconds versus C's 372.36 seconds. Thus the second implementation
meets the same-runtime requirement while using no `unsafe` Rust and no external
crate dependencies. `run_8x14_rust_audit.sh` preserves the source, binary,
environment, ten logs, structural check, and hashes.

## Ladder reproduced from scratch (matches OEIS A303735 exactly)
  no 7x11, 7x12, 7x13, 7x14   (each ~1s)
  8x11, 8x12, 8x13 all exist  (found instantly)
  => beta(Q_11)=beta(Q_12)=beta(Q_13)=8  [A303735 a(11..13)=8,8,8 by V.S.Miller 2023]
  => beta(Q_14) >= 8 from no 7x14; = 9 from no 8x14

## Independent checks
  direct Python control: exact raw solution sets on 3x4, 4x4 and 5x6
  canonical control: all 13 independently computed 5x6 orbit representatives match
  partition control: three 5x6 parts are disjoint and union to the complete reference set
  sanitizer control: the same checks pass under AddressSanitizer and UBSan
  Rust control: full ten-part 8x14 run, exact C node-vector match in every part
  split control: identical settings find solutions on 8x11/8x12/8x13 in all 10 parts
  frontier coherence: all parts identical to depth 6 (0,1,6,18,143,1082,11364)
  extension check (Python, separate codebase): 40/40 sampled 8x13 detecting, 0 extendable

## Corollaries
  beta(Q_15) = 9   (no 8x15 since no 8x14 by column deletion; upper bound 9 is exhibited)
  M(14) = 8        (beta(Q_14)=9 gives M >= 8 via beta-1 <= M <= beta;
                    M <= 8 is the weighing certificate matrices/M14_le_8.txt)
  D(7) = 12        (largest dissociated set in {0,1}^7: E(8)=13 gives D(7) <= 12
                    via E(q) >= D(q-1)+1; McKay's 2014 sets give D(7) >= 12)

## Cross-validation against McKay (2014)
  thm_check : 118485/118485 McKay 12-sets, adjoined with 0, are valid 8x13 matrices
  reconcile : all 118485 of his S_7 orbits occur among our 195086; 0 missing
  checkdiff : all 76601 extra orbits re-tested by brute force; none dissociated
  independently reproduced 2026-08-09; see enumerate/crossvalidate/RESULT.md
