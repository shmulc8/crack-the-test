# Reproduced result

Date: 2026-08-09

Command:

```sh
./run.sh /path/to/diff7_12.g6
```

The input was McKay's `diff7_12.g6` with SHA-256
`169a623bb40189ad9bf5655f9906ba057a7fa489130fd323a2ec74865812f309`.
The runner decoded 118,485 records and required the complete ten-part 8×13
enumeration to emit exactly 108,865 solutions before invoking the checkers.

```text
McKay 12-sets tested : 118485
  S u {0} is a valid 8x13 detecting matrix : 118485
  FAILED                                   : 0

PASS: every McKay dissociated 12-set yields an 8x13 detecting matrix after adjoining 0

McKay   : 118485 sets -> 118485 distinct canonical forms
ours    : 108865 solutions -> 1415245 derived 12-sets -> 195086 distinct canonical forms
in both : 118485
McKay only: 0
ours only : 76601

COVERAGE PASS: all McKay orbits occur; the expected 76601 weaker detecting-set orbits remain

derived 12-sets            : 1415245
not in McKay (with mult.)  : 551396
  distinct canonical forms : 76601
  unexpectedly dissociated : 0
  verified non-dissociated : 76601
PASS: every extra orbit is non-dissociated
```
