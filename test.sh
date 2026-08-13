#!/bin/sh
# Run both verifiers on every certificate + a negative control.
set -e
cd "$(dirname "$0")"
verify_bin=$(mktemp "${TMPDIR:-/tmp}/crack-verify.XXXXXX")
broken_m14=$(mktemp "${TMPDIR:-/tmp}/crack-broken-m14.XXXXXX")
broken_27=$(mktemp "${TMPDIR:-/tmp}/crack-broken-27.XXXXXX")
empty_matrix=$(mktemp "${TMPDIR:-/tmp}/crack-empty.XXXXXX")
enum_bin=$(mktemp "${TMPDIR:-/tmp}/crack-enum.XXXXXX")
sample_log=$(mktemp "${TMPDIR:-/tmp}/crack-sample.XXXXXX")
sa_bin=$(mktemp "${TMPDIR:-/tmp}/crack-sa.XXXXXX")
frontier_dir=$(mktemp -d "${TMPDIR:-/tmp}/crack-frontier.XXXXXX")
trap 'rm -f "$verify_bin" "$broken_m14" "$broken_27" "$empty_matrix" "$enum_bin" "$sample_log" "$sa_bin"; rm -rf "$frontier_dir"' EXIT HUP INT TERM
cc -O2 -o "$verify_bin" verify.c
JS="bun"; command -v bun >/dev/null || JS="node"

for m in matrices/beta_Q15_le_9.txt matrices/beta_Q24_le_13.txt \
         matrices/beta_Q26_le_14.txt matrices/beta_Q29_le_15.txt; do
  echo "== $m"
  "$verify_bin" "$m" | tail -2
  "$JS" verify.js "$m" | tail -1
done

echo "== matrices/M14_le_8.txt (weighing certificate for M(14) <= 8)"
python3 verify_weighing.py matrices/M14_le_8.txt
echo "== negative control (duplicated coin => two subsets must share a sum)"
awk '{ print $0 substr($0,1,1) }' matrices/M14_le_8.txt > "$broken_m14"
if python3 verify_weighing.py "$broken_m14" >/dev/null 2>&1; then echo "FAIL: weighing verifier accepted a broken certificate"; exit 1; fi
echo "weighing verifier correctly rejects it"

echo "== negative control (duplicated column => kernel vector must be found)"
awk '{ print substr($0,1,1) $0 }' matrices/beta_Q26_le_14.txt > "$broken_27"
if "$verify_bin" "$broken_27" >/dev/null 2>&1; then echo "FAIL: C verifier accepted a broken matrix"; exit 1; fi
if "$JS" verify.js "$broken_27" >/dev/null 2>&1; then echo "FAIL: JS verifier accepted a broken matrix"; exit 1; fi
echo "both verifiers correctly reject it"
echo "== negative control (empty matrix must be rejected)"
if "$verify_bin" "$empty_matrix" >/dev/null 2>&1; then echo "FAIL: C verifier accepted an empty matrix"; exit 1; fi
if "$JS" verify.js "$empty_matrix" >/dev/null 2>&1; then echo "FAIL: JS verifier accepted an empty matrix"; exit 1; fi
echo "both verifiers correctly reject it"
echo "== enumerator controls and fail-closed partition validation"
cc -O2 -o "$enum_bin" enumerate/enum.c
"$enum_bin" 3 4 --maxsol 1 --report 99999 | grep -q '^solutions found: 0$'
"$enum_bin" 4 4 --maxsol 1 --report 99999 | grep -q '^solutions found: 1$'
if "$enum_bin" 8 13 --split 10 --part 10 --splitdepth 6 --maxsol 1 >/dev/null 2>&1; then
  echo "FAIL: enumerator accepted an out-of-range partition"; exit 1
fi
"$enum_bin" 8 13 --maxsol 1 --report 99999 >"$sample_log"
python3 enumerate/verify_extensions.py "$sample_log" 8 13 | grep -q '^SAMPLE PASS:'
if python3 enumerate/verify_extensions.py "$sample_log" 8 13 --expect-complete 2 >/dev/null 2>&1; then
  echo "FAIL: extension checker accepted an incomplete classification"; exit 1
fi
echo "enumerator and extension checker controls passed"
echo "== q=9 packing, known-positive prefix, and frontier-driver controls"
q9_control=$(python3 enumerate/q9_positive_control.py matrices/beta_Q15_le_9.txt)
q9_prefix=${q9_control#CANONICAL Q9 CONTROL: }
"$enum_bin" 9 15 --maxsol 1 --report 99999 \
  --prefix "$q9_prefix" \
  | grep -q '^solutions found: 1$'
q9_pivot=$(python3 enumerate/q9_pivot_control.py matrices/beta_Q15_le_9.txt)
q9_pivot_prefix=${q9_pivot#PIVOT CANONICAL Q9 CONTROL: }
"$enum_bin" 9 15 --maxsol 1 --report 99999 --canondepth 15 --pivots \
  --prefix "$q9_pivot_prefix" \
  | grep -q '^solutions found: 1$'
if "$enum_bin" 9 15 --maxsol 1 --report 99999 --canondepth 15 --pivots \
    --prefix "$q9_prefix" | grep -q '^solutions found: 1$'; then
  echo "FAIL: --pivots did not reject the baseline-canonical q9 prefix (pivot group inert at q=9)"; exit 1
fi
echo "q=9 --pivots positive control passed (accepts the O(q,Z)-canonical solution, rejects the baseline-canonical prefix)"
if "$enum_bin" 9 16 --prefix 0,2,1 >/dev/null 2>&1; then
  echo "FAIL: enumerator accepted a non-increasing prefix"; exit 1
fi
python3 enumerate/frontier_run.py "$enum_bin" 4 6 --frontier-depth 3 \
  --workers 2 --source enumerate/enum.c --output "$frontier_dir/run" >/dev/null
python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); assert s["estimate_available"] and s["estimated_total_nodes"] == 6' \
  "$frontier_dir/run/summary.json"
echo "q=9 and frontier-driver controls passed"
echo "== independent small-instance enumeration, symmetry, and partition controls"
python3 enumerate/reference_check.py "$enum_bin"
echo "== search-tool input validation"
cc -O2 -o "$sa_bin" search/sa.c -lm
if "$sa_bin" count "$empty_matrix" 4 >/dev/null 2>&1; then
  echo "FAIL: search counter accepted an empty matrix"; exit 1
fi
if "$sa_bin" unknown 4 >/dev/null 2>&1; then
  echo "FAIL: search tool accepted an unknown mode"; exit 1
fi
echo "search-tool input validation passed"
if command -v rustc >/dev/null 2>&1; then
  echo "== independent safe-Rust enumerator controls"
  (cd enumerate && ./rust_controls.sh)
else
  echo "SKIP: rustc not found; run enumerate/rust_controls.sh when Rust is available"
fi
echo "ALL CHECKS PASSED"
