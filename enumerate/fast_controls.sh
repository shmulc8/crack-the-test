#!/usr/bin/env bash
# Controls for the fast search (enum_fast.c and fast/): canonicity agreement with
# the brute-force test, identical C/Rust node vectors, the known-value ladder,
# and positive controls that must find matrices.
set -euo pipefail
cd "$(dirname "$0")"

cc -O3 -Wall -Wextra -o enum_fast enum_fast.c
cargo build --release --quiet --manifest-path fast/Cargo.toml
R=fast/target/release/detect-fast
C_FLAGS=(--clique 6 --exact-clique --fast-canon)

echo "== minimal-image canonicity agrees with the brute-force lex-min test at every node =="
for qn in "6 9" "7 11" "7 12"; do
  ./enum_fast $qn --maxsol 1000000 --canondepth "${qn#* }" --check-canon >/dev/null
  echo "$qn: agree"
done
./enum_fast 6 9 --maxsol 1000000 --canondepth 9 --pivots --check-canon >/dev/null
echo "6 9 (pivots): agree"

vec() { sed -n 's/.*nodes\/depth: \[\([^]]*\)\].*/\1/p'; }

echo "== C and Rust node vectors are identical =="
for qn in "6 9" "7 11" "7 12" "7 13" "7 14" "8 14"; do
  c=$(./enum_fast $qn --maxsol 1 --report 99999 --mitm 5 --canondepth "${qn#* }" "${C_FLAGS[@]}" | vec)
  r=$($R $qn --mitm 5 --report 99999 | vec)
  [[ "$c" == "$r" ]] || { echo "$qn: C [$c] != Rust [$r]" >&2; exit 1; }
  echo "$qn: [$r]"
done
for p in 0,3,28,45,94,102 0,3,5,56,90,188; do
  c=$(./enum_fast 9 16 --maxsol 1 --report 99999 --prefix "$p" --mitm 7 --canondepth 16 "${C_FLAGS[@]}" | vec)
  r=$($R 9 16 --prefix "$p" --report 99999 | vec)
  [[ "$c" == "$r" ]] || { echo "9x16 $p: C [$c] != Rust [$r]" >&2; exit 1; }
  echo "9x16 prefix $p: identical"
done

echo "== known values: beta(Q_n) for n = 3..14 =="
expect=(0 0 0 3 4 4 5 6 6 7 7 8 8 8 9)
for n in $(seq 3 14); do
  b=${expect[$n]}
  $R $((b - 1)) "$n" --mitm 1 --report 99999 | grep -q "NO $((b - 1))x$n DETECTING MATRIX EXISTS" \
    || { echo "expected no $((b - 1))x$n matrix" >&2; exit 1; }
  if (( b <= 9 && n <= 15 )); then
    $R "$b" "$n" --mitm 1 --report 99999 | grep -q "^SOLUTION #1" \
      || { echo "expected a ${b}x$n matrix" >&2; exit 1; }
  fi
  echo "n=$n: no $((b - 1))x$n, ${b}x$n exists"
done

echo "== positive control: the 9x15 certificate's canonical prefix is found =="
$R 9 15 --report 99999 --prefix 0,3,12,23,45,84,99,120,127,153,174,180,197,214,218 | grep -q "^SOLUTION #1" \
  || { echo "9x15 control failed" >&2; exit 1; }
echo "9x15: found"

echo "FAST CONTROLS PASSED"
