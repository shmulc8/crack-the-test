#!/bin/bash
# Extend-first sibling pipeline over W28 bases. usage: pairhunt2.sh <worker> <nworkers>
set -u
D="$(cd "$(dirname "$0")" && pwd)"
W=$1
NW=$2
i=-1
for f in "$D"/pairbases/*.txt; do
  i=$((i + 1))
  [ $((i % NW)) -eq "$W" ] || continue
  tag=$(basename "$f" .txt)
  out="$D/pairlogs/ext_${tag}.log"
  [ -e "$out" ] && continue
  "$D/sa3" extend 28 "$f" 0 32768 0 > "$out.part" 2>&1 && mv "$out.part" "$out"
  python3 "$D/process_base.py" "$f" "$out" >> "$D/pairhunt2.log" 2>&1
done
echo "pairhunt2 worker $W done" >> "$D/pairhunt2.log"
