#!/bin/bash
# Differential, known-value, and performance controls for enum.rs.
set -euo pipefail
cd "$(dirname "$0")"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/crack-rust-controls.XXXXXX")
rust_bin="$tmp_dir/enum-rust"
c_bin="$tmp_dir/enum-c"
rust_tests="$tmp_dir/enum-rust-tests"
trap 'rm -f "$rust_bin" "$c_bin" "$rust_tests"; rmdir "$tmp_dir" 2>/dev/null || true' EXIT HUP INT TERM

rustc --edition=2021 --test -C opt-level=2 -o "$rust_tests" enum.rs
"$rust_tests"
rustc --edition=2021 -C opt-level=3 -C target-cpu=native -C lto=fat \
  -C codegen-units=1 -C panic=abort -o "$rust_bin" enum.rs
cc -O3 -Wall -Wextra -Wpedantic -o "$c_bin" enum.c

python3 reference_check.py "$rust_bin"

check() {
  local q=$1 n=$2 expected=$3 output count
  output=$("$rust_bin" "$q" "$n" --maxsol 1 --report 99999)
  count=$(sed -n 's/^solutions found: //p' <<<"$output")
  if [[ $count != "$expected" ]]; then
    echo "FAIL rust ${q}x${n}: got '$count', expected '$expected'" >&2
    exit 1
  fi
  printf 'rust %sx%s: %s\n' "$q" "$n" "$([[ $count == 0 ]] && echo none || echo exists)"
}

for instance in "3 4" "3 5" "4 6" "5 7" "5 8" "6 9" "6 10" \
  "7 11" "7 12" "7 13" "7 14"; do
  check ${instance% *} ${instance#* } 0
done
for instance in "4 4" "5 6" "6 7" "6 8" "7 10" "8 11" "8 12" "8 13"; do
  check ${instance% *} ${instance#* } 1
done

c_output=$("$c_bin" 7 14 --maxsol 1 --report 99999)
rust_output=$("$rust_bin" 7 14 --maxsol 1 --report 99999)
c_nodes=$(sed -n 's/^DONE .* nodes\/depth: \[\([^]]*\)\].*/\1/p' <<<"$c_output")
rust_nodes=$(sed -n 's/^DONE .* nodes\/depth: \[\([^]]*\)\].*/\1/p' <<<"$rust_output")
if [[ -z $c_nodes || $rust_nodes != "$c_nodes" ]]; then
  echo "FAIL: C/Rust 7x14 node vectors differ" >&2
  exit 1
fi
echo "C/Rust 7x14 node vectors match exactly"

if "$rust_bin" 8 13 --split 10 --part 10 --splitdepth 6 >/dev/null 2>&1; then
  echo "FAIL: Rust accepted an invalid partition" >&2
  exit 1
fi
echo "RUST ENUMERATOR CONTROLS PASSED"
