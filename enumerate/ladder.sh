#!/bin/bash
# Reproduce every published term of OEIS A303735 and the new one.
# beta(Q_n) = min q such that a q x n detecting matrix exists.
set -u
cc -O3 -o /tmp/enum enum.c || exit 1
say() { printf '%-8s %-28s %s\n' "$1" "$2" "$3"; }
check() {  # q n expect
  r=$(/tmp/enum "$1" "$2" --maxsol 1 --report 99999 | grep -oE 'solutions found: [0-9]+' | grep -oE '[0-9]+$')
  got=$([ "$r" = 0 ] && echo none || echo exists)
  say "${1}x${2}" "$got" "$([ "$got" = "$3" ] && echo OK || echo MISMATCH)"
}
echo "== instances with no detecting matrix =="
for p in "3 4" "3 5" "4 6" "5 7" "5 8" "6 9" "6 10" "7 11" "7 12" "7 13" "7 14"; do
  check ${p% *} ${p#* } none
done
echo "== instances with a detecting matrix =="
for p in "4 4" "5 6" "6 7" "6 8" "7 10" "8 11" "8 12" "8 13"; do
  check ${p% *} ${p#* } exists
done
echo "== the open case: 8x14 (run split across cores for speed) =="
check 8 14 none
