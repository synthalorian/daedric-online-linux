#!/usr/bin/env bash
# Daedric Online session memory watcher.
# Samples the Wine/Skyrim process tree RSS + system memory/swap every 30s.
# Output: CSV at $1 (default ~/daedric-memwatch.csv). Leak = RSS climbs
# steadily without plateau across the session; appetite = climbs to a
# working set and holds.
OUT="${1:-$HOME/daedric-memwatch.csv}"
[ -f "$OUT" ] || echo "ts,game_tree_rss_mb,mem_available_mb,swap_used_mb" >> "$OUT"

while true; do
  # match the whole wine tree for the prefix
  mapfile -t pids < <(pgrep -f "SkyrimSE|Daedric Online|wineserver|services.exe|svchost.exe|explorer.exe|rpcss.exe|plugplay|winedevice|conhost|winedbg" 2>/dev/null)
  if [ ${#pids[@]} -gt 0 ]; then
    rss=$(ps -o rss= -p "$(IFS=,; echo "${pids[*]}")" 2>/dev/null | awk '{s+=$1} END {print int(s/1024)}')
    avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    swap=$(awk '/SwapTotal/ {t=$2} /SwapFree/ {f=$2} END {print int((t-f)/1024)}' /proc/meminfo)
    echo "$(date +%Y-%m-%dT%H:%M:%S),${rss:-0},$avail,$swap" >> "$OUT"
  fi
  sleep 30
done
