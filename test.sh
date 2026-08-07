#!/bin/sh
# Run both verifiers on every certificate + a negative control.
set -e
cd "$(dirname "$0")"
cc -O2 -o verify verify.c
JS="bun"; command -v bun >/dev/null || JS="node"

for m in matrices/beta_Q15_le_9.txt matrices/beta_Q24_le_13.txt \
         matrices/beta_Q26_le_14.txt matrices/beta_Q29_le_15.txt; do
  echo "== $m"
  ./verify "$m" | tail -2
  "$JS" verify.js "$m" | tail -1
done

echo "== negative control (duplicated column => kernel vector must be found)"
awk '{ print substr($0,1,1) $0 }' matrices/beta_Q26_le_14.txt > /tmp/broken_27.txt
if ./verify /tmp/broken_27.txt >/dev/null 2>&1; then echo "FAIL: C verifier accepted a broken matrix"; exit 1; fi
if "$JS" verify.js /tmp/broken_27.txt >/dev/null 2>&1; then echo "FAIL: JS verifier accepted a broken matrix"; exit 1; fi
echo "both verifiers correctly reject it"
echo "ALL CHECKS PASSED"
