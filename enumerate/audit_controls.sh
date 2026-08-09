#!/bin/bash
# Fast differential and sanitizer controls for enum.c.
set -euo pipefail
cd "$(dirname "$0")"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/crack-enum-audit.XXXXXX")
plain_bin="$tmp_dir/enum"
sanitized_bin="$tmp_dir/enum-sanitized"
trap 'rm -f "$plain_bin" "$sanitized_bin"; rmdir "$tmp_dir" 2>/dev/null || true' EXIT HUP INT TERM

cc -O2 -Wall -Wextra -Wpedantic -o "$plain_bin" enum.c
python3 reference_check.py "$plain_bin"

cc -O1 -Wall -Wextra -Wpedantic -fsanitize=address,undefined \
  -fno-omit-frame-pointer -o "$sanitized_bin" enum.c
ASAN_OPTIONS=detect_leaks=0 python3 reference_check.py "$sanitized_bin"

echo "ENUMERATOR AUDIT CONTROLS PASSED"
