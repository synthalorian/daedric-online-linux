#!/usr/bin/env bash
# downgrade-1.6.1170.sh — restore Skyrim SE to build 1.6.1170 and hold Steam's
# auto-update so it stays there. Idempotent; safe to re-run any time the
# version regresses or textures re-break after a launcher pass.
#
# Why: the Daedric launcher hard-requires exe FileVersion 1.6.1170.0
# (REQUIRED_RUNTIME = "1.6.1170" in its main.js). Steam's Aug-2026 update
# re-pulls build 1.7.104 and the version gate slams shut. This script merges
# the pinned depots back over the install and flips AutoUpdateBehavior so
# Steam can't quietly upgrade you again.
#
# Prereq — download the three 1.6.1170 depots via the Steam console (one at a
# time, wait for each; the manifest IDs pin the exact 1.6.1170 build):
#
#   download_depot 489830 489831 8442952117333549665
#   download_depot 489830 489832 8042843504692938467
#   download_depot 489830 489833 1914580699073641964
#
# On Linux they land under:
#   ~/.local/share/Steam/ubuntu12_32/steamapps/content/app_489830/depot_*
# Keep that folder around — it is the eternal stock 1.6.1170 source.
#
# Overrides (env): GAME, C, ACF. Defaults match this machine (CachyOS/KDE).
set -euo pipefail

GAME="${GAME:-$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition}"
C="${C:-$HOME/.local/share/Steam/ubuntu12_32/steamapps/content/app_489830}"
ACF="${ACF:-$HOME/.local/share/Steam/steamapps/appmanifest_489830.acf}"
VCHECK="${VCHECK:-strings}"

for dep in 489831 489832 489833; do
  [ -d "$C/depot_$dep" ] || { echo "missing depot_$dep at $C — re-download via Steam console first"; exit 1; }
done

echo "[1/4] merging depot_489831 (CC, Animations, Meshes, Misc, Sounds, Voices, Video)"
rsync -a "$C/depot_489831/Data/" "$GAME/Data/"
rsync -a "$C/depot_489831/installscript.vdf" "$GAME/"

echo "[2/4] merging depot_489832 (root files + Textures/Interface/Shaders ESMs)"
rsync -a "$C/depot_489832/" "$GAME/"

echo "[3/4] installing SkyrimSE.exe 1.6.1170 (37,157,144 B)"
cp -a "$C/depot_489833/SkyrimSE.exe" "$GAME/SkyrimSE.exe"

echo "[4/4] holding Steam auto-update (only update on manual launch)"
python3 - "$ACF" <<'EOF'
import sys
p = sys.argv[1]
s = open(p).read()
s2 = s.replace('"AutoUpdateBehavior"\t\t"1"', '"AutoUpdateBehavior"\t\t"2"')
open(p, "w").write(s2)
EOF

echo "== exe version: $($VCHECK -el "$GAME/SkyrimSE.exe" | grep -A1 '^FileVersion$' | tail -1) (want 1.6.1170.0) =="
grep AutoUpdateBehavior "$ACF"
echo
echo "Done. Two rules from here on:"
echo "  1. Never launch Skyrim via the Steam client (Steam updates on manual launch)."
echo "  2. Never click Verify Integrity in Steam (re-pulls 1.7.104)."
echo "Launcher-only entry point, and re-run this script if anything regresses."
echo
echo "Textures re-broken? python3 scripts/bsa-check.py \"$GAME/Data/Skyrim - Textures\"*.bsa"