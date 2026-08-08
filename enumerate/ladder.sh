#!/bin/bash
# Reproduce every published term of OEIS A303735 and the new 8x14 result.
set -euo pipefail
cd "$(dirname "$0")"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/crack-ladder.XXXXXX")
enum_bin="$tmp_dir/enum"
trap 'rm -f "$enum_bin" "$tmp_dir"/part-*.log; rmdir "$tmp_dir" 2>/dev/null || true' EXIT HUP INT TERM
cc -O3 -o "$enum_bin" enum.c

say() { printf '%-8s %-28s %s\n' "$1" "$2" "$3"; }
check() {  # q n expect
  local output result got
  output=$("$enum_bin" "$1" "$2" --maxsol 1 --report 99999)
  result=$(sed -n 's/^solutions found: //p' <<<"$output")
  case "$result" in
    0) got=none ;;
    ''|*[!0-9]*) say "${1}x${2}" "invalid output" FAIL; return 1 ;;
    *) got=exists ;;
  esac
  say "${1}x${2}" "$got" "$([[ "$got" == "$3" ]] && echo OK || echo MISMATCH)"
  [[ "$got" == "$3" ]]
}

echo "== instances with no detecting matrix =="
for p in "3 4" "3 5" "4 6" "5 7" "5 8" "6 9" "6 10" "7 11" "7 12" "7 13" "7 14"; do
  check ${p% *} ${p#* } none
done

echo "== instances with a detecting matrix =="
for p in "4 4" "5 6" "6 7" "6 8" "7 10" "8 11" "8 12" "8 13"; do
  check ${p% *} ${p#* } exists
done

echo "== new case: 8x14 split across 10 processes =="
pids=()
for part in {0..9}; do
  "$enum_bin" 8 14 --maxsol 1 --split 10 --part "$part" \
    --splitdepth 6 --canondepth 8 --report 99999 >"$tmp_dir/part-$part.log" &
  pids+=("$!")
done
for pid in "${pids[@]}"; do wait "$pid"; done
for part in {0..9}; do
  [[ $(sed -n 's/^solutions found: //p' "$tmp_dir/part-$part.log") == 0 ]] || {
    say "8x14" "partition $part unexpected" FAIL
    exit 1
  }
done
say "8x14" "none in all 10 partitions" OK
