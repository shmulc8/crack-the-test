#!/bin/bash
# Slice fresh q x n children out of the 15x29 parents, extend-scan every newborn.
# A ZERO extension at 14x27 or 13x24 is a NEW RECORD. Checkpointed per batch.
set -u
D="$(cd "$(dirname "$0")" && pwd)"
batch=${1:-0}
while :; do
  batch=$((batch + 1))
  for t in "14 26 27" "13 23 24"; do
    set -- $t; q=$1; n=$2; nx=$3
    bun "$D/sliceaudit.js" "$q" "$n" 400 $((batch * 7919)) > "$D/hunt_${q}x${n}_b${batch}.log" 2>&1
    for w in "$D"/won_${q}x${n}_audit*.txt; do
      [ -e "$w" ] || continue
      s="$D/hx_$(basename "$w")"
      [ -e "$s" ] && continue
      "$D/sa_q$q" extend "$n" "$w" 0 $((1 << q)) 0 > "$s" 2>&1
      if grep -q '^ZERO' "$s"; then
        echo "!!!! RECORD CANDIDATE ${q}x${nx} from $(basename "$w") !!!!" >> "$D/rescue.log"
      fi
    done
  done
  echo "hunt batch $batch done $(date +%H:%M)" >> "$D/hunt.log"
done
