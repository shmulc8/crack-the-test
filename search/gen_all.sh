#!/bin/bash
# Historical demo generator for n=1..29. Requires campaign seed matrices that
# are intentionally not distributed in this compact verification repository.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
for required in best29_a.txt won_14x26_s16.txt; do
  [ -s "$required" ] || { echo "missing campaign input: $D/$required" >&2; exit 2; }
done

slice() { # slice <cols> <src> <out>
  [ -s "$3" ] && return 0
  grep -v '^#' "$2" | cut -c1-"$1" > "$3"
  echo "SLICE $3 from $2"
}

gen() { # gen <q> <n> [sec]
  local q=$1 n=$2 sec=${3:-60}
  local out="demo_${q}x${n}.txt"
  [ -s "$out" ] && return 0
  if [ ! -x "./sa_q$q" ]; then
    cc -O3 -DQ="$q" -o "sa_q$q" sa.c 2>> genlog.txt || { echo "COMPILE FAIL q=$q"; return 1; }
  fi
  for seed in 1 2 3 4 5; do
    if "./sa_q$q" anneal "$n" "$sec" RAND $((7000 + q * 37 + n * 11 + seed)) "$out" 0 >> genlog.txt 2>&1; then
      grep -v '^#' "$out" > "$out.tmp" && mv "$out.tmp" "$out"
      echo "GEN ${q}x${n} ok (seed $seed)"
      return 0
    fi
  done
  echo "GEN ${q}x${n} FAILED"
  return 1
}

# copies + free column-slices of verified record matrices
slice 29 best29_a.txt        demo_15x29.txt
slice 28 best29_a.txt        demo_15x28.txt
slice 27 best29_a.txt        demo_15x27.txt
slice 26 won_14x26_s16.txt   demo_14x26.txt
slice 25 won_14x26_s16.txt   demo_14x25.txt
slice 24 won_14x26_s16.txt   demo_14x24.txt

# exact-beta sizes (n<=13) and published-bound sizes (n=14..23)
gen 1 1 10;  gen 2 2 10;  gen 3 3 10;  gen 4 4 10;  gen 4 5 30
gen 5 6 30;  gen 6 7 30;  gen 6 8 60;  gen 7 9 30;  gen 7 10 60
gen 8 11 30; gen 8 12 30; gen 8 13 90
gen 9 14 90; gen 9 15 120
gen 10 16 90; gen 10 17 120
gen 11 18 120
gen 12 19 120; gen 12 20 150
gen 13 21 120; gen 13 22 150; gen 13 23 300

echo "=== verify all ==="
fail=0
for f in demo_*x*.txt; do
  n="${f##*x}"; n="${n%.txt}"
  r=$(bun survivors.js "$f" "$n" 2>&1 | grep -o 'nulls: [0-9]*')
  echo "$f n=$n -> $r"
  [ "$r" = "nulls: 0" ] || fail=1
done
[ $fail -eq 0 ] && echo "ALL VERIFIED" || echo "VERIFY FAILURES PRESENT"
