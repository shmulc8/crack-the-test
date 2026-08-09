#!/bin/bash
# Run all ten Rust partitions and preserve a fail-closed evidence bundle.
set -euo pipefail
cd "$(dirname "$0")"

if [[ $# != 1 || -z $1 || $1 == -* ]]; then
  echo "usage: $0 NEW_OUTPUT_DIRECTORY" >&2
  exit 1
fi

out=$1
if [[ -e $out ]]; then
  echo "refusing to overwrite existing path: $out" >&2
  exit 1
fi
mkdir "$out"

rust_bin="$out/enum-rust"
rustc --edition=2021 -C opt-level=3 -C target-cpu=native -C lto=fat \
  -C codegen-units=1 -C panic=abort -o "$rust_bin" enum.rs
cp enum.rs "$out/enum.rs"

{
  echo "source_commit=$(git rev-parse HEAD 2>/dev/null || echo unavailable)"
  echo "source_rust_sha256=$(shasum -a 256 enum.rs | awk '{print $1}')"
  echo "started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "command=enum-rust 8 14 --maxsol 1 --split 10 --part PART --splitdepth 6 --canondepth 8 --report 99999"
  rustc --version --verbose
  uname -a
  echo "git_status_begin"
  git status --short 2>/dev/null || true
  echo "git_status_end"
} >"$out/environment.txt"

pids=()
stop_workers() {
  trap - HUP INT TERM
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "interrupted; preserving partial bundle at $out" >&2
  exit 130
}
trap stop_workers HUP INT TERM

for part in {0..9}; do
  "$rust_bin" 8 14 --maxsol 1 --split 10 --part "$part" \
    --splitdepth 6 --canondepth 8 --report 99999 >"$out/part-$part.log" 2>&1 &
  pids+=("$!")
done
run_status=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    run_status=1
  fi
done
trap - HUP INT TERM
if [[ $run_status != 0 ]]; then
  echo "one or more Rust partitions failed; preserving partial bundle at $out" >&2
  exit 1
fi

python3 check_partition_logs.py --engine rust "$out"/part-*.log >"$out/CHECK.txt"
date -u +finished_utc=%Y-%m-%dT%H:%M:%SZ >>"$out/environment.txt"
shasum -a 256 "$out"/enum-rust "$out"/enum.rs "$out"/part-*.log \
  "$out/environment.txt" "$out/CHECK.txt" >"$out/SHA256SUMS"
sed -n '$p' "$out/CHECK.txt"
echo "Rust audit bundle written to $out"
