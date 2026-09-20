#!/bin/bash
# Build the case-exact set of texture paths servable from every BSA in Data/.
# Output: one path per line, backslash form, original case preserved.
# Used by true-missing.py as the BSA coverage input.
#
# Usage: DATA=/path/to/Data ./bsa-names.sh [outfile]
# Defaults: DATA=$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data

set -euo pipefail
DATA="${DATA:-$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data}"
OUT="${1:-/tmp/bsa_name_index.txt}"

: > "$OUT"
for b in "$DATA"/*.bsa; do
  echo "scanning $(basename "$b") ..." >&2
  grep -a -o -i -E 'textures\\[A-Za-z0-9_ .'"'"'\-\\/{}()!@#$%^&+=\[\]~`"]+\.(dds|DDS)' "$b" >> "$OUT" 2>/dev/null || true
done
sort -u "$OUT" -o "$OUT"
echo "unique BSA-servable texture paths: $(wc -l < "$OUT")"