#!/bin/bash
# Extend-first sibling pipeline over W28 bases. usage: pairhunt2.sh <worker> <nworkers>
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -ne 2 ] || ! [[ "$1" =~ ^[0-9]+$ && "$2" =~ ^[1-9][0-9]*$ ]] || [ "$1" -ge "$2" ]; then
  echo "usage: $0 <worker: 0..nworkers-1> <nworkers>" >&2
  exit 2
fi
W=$1
NW=$2
for required in sa3 process_base.py; do
  [ -e "$D/$required" ] || { echo "missing campaign tool: $D/$required" >&2; exit 2; }
done
[ -d "$D/pairbases" ] || { echo "missing campaign directory: $D/pairbases" >&2; exit 2; }
[ -d "$D/pairlogs" ] || { echo "missing campaign directory: $D/pairlogs" >&2; exit 2; }
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
