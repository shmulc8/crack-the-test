#!/usr/bin/env bash
# Controls for the fast search (enum_fast.c and fast/): the naive orbit oracle on
# both engines, the mutation test, canonicity agreement with brute force,
# membership with and without meet-in-the-middle, identical C/Rust node vectors,
# the known-value ladder, and positive controls that must find matrices.
# Set CARGO_TARGET_DIR to build the Rust engine somewhere other than fast/target.
set -euo pipefail
cd "$(dirname "$0")"

cc -O3 -Wall -Wextra -o enum_fast enum_fast.c
cargo build --release --quiet --manifest-path fast/Cargo.toml
R="${CARGO_TARGET_DIR:-fast/target}/release/detect-fast"
work=$(mktemp -d "${TMPDIR:-/tmp}/fast-controls.XXXXXX")
trap 'rm -rf "$work"' EXIT
C_FLAGS=(--clique 6 --exact-clique --fast-canon)

echo "== naive oracle: exactly one representative per orbit (q = 4, 5, 6) =="
python3 fast_oracle_check.py ./enum_fast --clique 1 --exact-clique --fast-canon --mitm 1 | tail -1
python3 fast_oracle_check.py "$R" --clique 1 --mitm 1 | tail -1
python3 fast_oracle_check.py "$R" --clique 3 --mitm 4 --pardepth 20 | tail -1

echo "== mutation test: every broken variant fails the oracle =="
python3 fast_mutants.py "$work/mutants" | tail -1

echo "== random sets: minimal image = brute force = independent lex-min, q = 6..9 =="
cc -O3 -o "$work/canon_random_check" canon_random_check.c
for q in 6 7 8 9; do "$work/canon_random_check" "$q" 300 "$q"; done

echo "== minimal-image canonicity agrees with the brute-force lex-min test at every node =="
for qn in "6 9" "7 11" "7 12"; do
  ./enum_fast $qn --maxsol 1000000 --canondepth "${qn#* }" --check-canon >/dev/null
  echo "$qn: agree"
done
./enum_fast 6 9 --maxsol 1000000 --canondepth 9 --pivots --check-canon >/dev/null
echo "6 9 (pivots): agree"
./enum_fast 9 16 --maxsol 1 --report 99999 --prefix 0,3,5,56,90,188 --mitm 7 --canondepth 16 \
  --clique 6 --exact-clique --check-canon >/dev/null
echo "9x16 subtree 0,3,5,56,90,188: agree"

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
  m0=$(./enum_fast 9 16 --maxsol 1 --report 99999 --prefix "$p" --mitm 0 --canondepth 16 "${C_FLAGS[@]}" | vec)
  [[ "$m0" == "$r" ]] || { echo "9x16 $p: subset-sum membership [$m0] != MITM [$r]" >&2; exit 1; }
  echo "9x16 prefix $p: identical (C, Rust, and C without MITM)"
done

echo "== known values: beta(Q_n) for n = 3..14 =="
expect=(0 0 0 3 4 4 5 6 6 7 7 8 8 8 9)
for n in $(seq 3 14); do
  b=${expect[$n]}
  a=$(( n - 1 < 7 ? n - 1 : 7 ))
  out=$($R $((b - 1)) "$n" --mitm "$a" --report 99999)
  grep -q "NO $((b - 1))x$n DETECTING MATRIX EXISTS" <<<"$out" \
    || { echo "expected no $((b - 1))x$n matrix" >&2; exit 1; }
  out=$($R "$b" "$n" --mitm "$a" --report 99999)
  grep -q "^SOLUTION #1" <<<"$out" || { echo "expected a ${b}x$n matrix" >&2; exit 1; }
  echo "n=$n: no $((b - 1))x$n, ${b}x$n exists"
done

echo "== positive control: the 9x15 certificate's canonical prefix is found =="
out=$($R 9 15 --report 99999 --prefix 0,3,12,23,45,84,99,120,127,153,174,180,197,214,218)
grep -q "^SOLUTION #1" <<<"$out" || { echo "9x15 control failed" >&2; exit 1; }
echo "9x15: found"

echo "FAST CONTROLS PASSED"
