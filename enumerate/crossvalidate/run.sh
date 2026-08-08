#!/bin/bash
# Reproduce the complete comparison with McKay's diff7_12.g6 dataset.
set -euo pipefail

if [[ $# != 1 || ! -f $1 ]]; then
  echo "usage: $0 /path/to/diff7_12.g6" >&2
  exit 2
fi
dataset_dir=$(cd "$(dirname "$1")" && pwd)
dataset="$dataset_dir/$(basename "$1")"
script_dir=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/crack-crossvalidate.XXXXXX")
generated=()
cleanup() {
  local file
  for file in "${generated[@]}"; do rm -f -- "$file"; done
  rmdir "$work" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

mckay="$work/mckay7.txt"; generated+=("$mckay")
echo "== decode McKay dataset =="
python3 "$script_dir/decode2.py" "$dataset" 12 7 >"$mckay"
(( $(wc -l <"$mckay") == 118485 )) || { echo "decoded record count is not 118485" >&2; exit 1; }

enum_bin="$work/enum"; generated+=("$enum_bin")
echo "== enumerate all 8x13 solutions in 10 partitions =="
cc -O3 -o "$enum_bin" "$script_dir/../enum.c"
pids=()
for part in {0..9}; do
  log="$work/s813_$part.txt"; generated+=("$log")
  "$enum_bin" 8 13 --maxsol 1000000000 --canondepth 8 \
    --split 10 --part "$part" --splitdepth 5 --report 99999 >"$log" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
all="$work/all813.txt"; generated+=("$all")
for part in {0..9}; do cat "$work/s813_$part.txt"; done >"$all"
(( $(grep -c '^SOLUTION #' "$all") == 108865 )) || { echo "enumerated solution count is not 108865" >&2; exit 1; }

for program in thm_check reconcile checkdiff; do
  binary="$work/$program"; generated+=("$binary")
  cc -O2 -Wall -Wextra -Wpedantic -o "$binary" "$script_dir/$program.c"
done
echo "== validate implication, coverage, and extra orbits =="
"$work/thm_check" "$mckay"
"$work/reconcile" "$mckay" "$all"
"$work/checkdiff" "$mckay" "$all"
