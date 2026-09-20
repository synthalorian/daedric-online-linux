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
# Run AFTER the launcher's client sync (README Step 6): that sync is what
# downgrades the game data (its internal downloader is pinned to the 1.6.1170
# manifests) but it corrupts LZ4 DDS blocks in the textures BSAs and never
# touches the exe. This script replaces the data with pristine depot files and
# pins the exe — the resulting build is the one with working textures.
#
# Fully portable — auto-discovers the Steam root, library folders, game
# install, appmanifest and console depot downloads. No hardcoded machine
# paths.
#
# Prereq — download the three 1.6.1170 depots via the Steam console (one at a
# time, wait for each; the manifest IDs pin the exact 1.6.1170 build):
#
#   download_depot 489830 489831 8442952117333549665
#   download_depot 489830 489832 8042843504692938467
#   download_depot 489830 489833 1914580699073641964
#
# On Linux they land under <steam_root>/ubuntu12_32/steamapps/content/app_489830/
# Keep that folder around — it is the eternal stock 1.6.1170 source.
#
# Overrides (env) — everything auto-detects; set these only to correct a guess:
#   STEAM_ROOT     Steam client install dir (default: ~/.local/share/Steam,
#                  flatpak path, or ~/.steam/steam — whichever exists)
#   STEAM_LIBRARY  a library folder containing the game (default: found by
#                  searching appmanifest_489830.acf across libraryfolders.vdf)
#   GAME           the game install dir (default: <library>/steamapps/common/Skyrim Special Edition)
#   ACF            the appmanifest path     (default: <library>/steamapps/appmanifest_489830.acf)
#   C              the depot downloads dir  (default: <steam_root>/ubuntu12_32/steamapps/content/app_489830)
#   APP_ID         Steam app id             (default: 489830)
#   GAME_NAME      folder name in steamapps/common (default: "Skyrim Special Edition")
set -euo pipefail

APP_ID="${APP_ID:-489830}"
GAME_NAME="${GAME_NAME:-Skyrim Special Edition}"
DEPOT_DATA=489831   # Data/: CC, Animations, Meshes, Misc, Sounds, Voices, Video
DEPOT_ROOT=489832   # root files + Textures/Interface/Shaders BSAs + ESMs
DEPOT_EXE=489833    # SkyrimSE.exe 1.6.1170 (37,157,144 B)

# --- 1. Steam root ---
if [ -z "${STEAM_ROOT:-}" ]; then
  for cand in "$HOME/.local/share/Steam" \
              "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam" \
              "$HOME/.steam/steam" "$HOME/.steam/root"; do
    if [ -f "$cand/steamapps/libraryfolders.vdf" ]; then
      STEAM_ROOT="$cand"; break
    fi
  done
fi
if [ -z "${STEAM_ROOT:-}" ]; then
  echo "Steam root not found. Install Steam, or set STEAM_ROOT explicitly." >&2
  exit 1
fi
echo "steam root : $STEAM_ROOT"

# --- 2. appmanifest (game's library folder) ---
ACF="${ACF:-}"
if [ -z "$ACF" ]; then
  if [ -f "$STEAM_ROOT/steamapps/appmanifest_$APP_ID.acf" ]; then
    ACF="$STEAM_ROOT/steamapps/appmanifest_$APP_ID.acf"
  else
    if [ -n "${STEAM_LIBRARY:-}" ] && [ -f "$STEAM_LIBRARY/steamapps/appmanifest_$APP_ID.acf" ]; then
      ACF="$STEAM_LIBRARY/steamapps/appmanifest_$APP_ID.acf"
    elif [ -f "$STEAM_ROOT/steamapps/libraryfolders.vdf" ]; then
      while IFS= read -r lib; do
        [ -z "$lib" ] && continue
        if [ -f "$lib/steamapps/appmanifest_$APP_ID.acf" ]; then
          ACF="$lib/steamapps/appmanifest_$APP_ID.acf"; break
        fi
      done < <(grep -oE '"path"[[:space:]]+"[^"]+"' "$STEAM_ROOT/steamapps/libraryfolders.vdf" \
               | sed -E 's/"path"[[:space:]]+"//; s/"$//')
    fi
  fi
fi
if [ -z "$ACF" ] || [ ! -f "$ACF" ]; then
  echo "appmanifest_$APP_ID.acf not found in any steamapps dir under $STEAM_ROOT." >&2
  echo "Install the game first, or set ACF/STEAM_LIBRARY explicitly." >&2
  exit 1
fi
LIB="${ACF%/appmanifest_$APP_ID.acf}"   # -> <library>/steamapps
LIB="${LIB%/steamapps}"                  # -> <library> (library root)
echo "appmanifest: $ACF"

# --- 3. game install dir ---
GAME="${GAME:-$LIB/steamapps/common/$GAME_NAME}"
if [ ! -d "$GAME" ]; then
  echo "game dir not found: $GAME — set GAME (or GAME_NAME) explicitly." >&2
  exit 1
fi
echo "game dir   : $GAME"

# --- 4. depot downloads dir ---
if [ -z "${C:-}" ]; then
  for cand in "$STEAM_ROOT/ubuntu12_32/steamapps/content/app_$APP_ID" \
              "$STEAM_ROOT/steamapps/content/app_$APP_ID"; do
    if [ -d "$cand" ]; then C="$cand"; break; fi
  done
fi
if [ -z "${C:-}" ]; then
  echo "depot downloads not found under $STEAM_ROOT — run the three" >&2
  echo "download_depot console commands first (see header)." >&2
  exit 1
fi
echo "depots     : $C"

for dep in "$DEPOT_DATA" "$DEPOT_ROOT" "$DEPOT_EXE"; do
  [ -d "$C/depot_$dep" ] || { echo "missing depot_$dep in $C — re-download via Steam console"; exit 1; }
done

# --- 5. merge ---
echo "[1/3] merging depot_$DEPOT_DATA (CC, Animations, Meshes, Misc, Sounds, Voices, Video)"
rsync -a "$C/depot_$DEPOT_DATA/Data/" "$GAME/Data/"
[ -f "$C/depot_$DEPOT_DATA/installscript.vdf" ] && rsync -a "$C/depot_$DEPOT_DATA/installscript.vdf" "$GAME/"

echo "[2/3] merging depot_$DEPOT_ROOT (root files + Textures/Interface/Shaders/ESMs)"
rsync -a "$C/depot_$DEPOT_ROOT/" "$GAME/"

echo "[3/3] installing SkyrimSE.exe 1.6.1170 (37,157,144 B)"
cp -a "$C/depot_$DEPOT_EXE/SkyrimSE.exe" "$GAME/SkyrimSE.exe"

# --- 6. hold auto-update (AutoUpdateBehavior -> 2, insert if absent) ---
echo "holding Steam auto-update (AutoUpdateBehavior -> 2)"
python3 - "$ACF" <<'EOF'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8", errors="replace").read()
if re.search(r'"AutoUpdateBehavior"\s*"[0-9]+"', s):
    s = re.sub(r'"AutoUpdateBehavior"\s*"[0-9]+"', '"AutoUpdateBehavior"\t\t"2"', s)
else:
    m = re.search(r'(\t"StateFlags"\s*"[0-9]+"\s*\n)', s)
    if m:
        s = s.replace(m.group(1), m.group(1) + '\t"AutoUpdateBehavior"\t\t"2"\n')
    else:
        s = s.replace('"AppState"\n', '"AppState"\n\t"AutoUpdateBehavior"\t\t"2"\n')
open(p, "w").write(s)
EOF

# --- 7. verify ---
echo
echo "== verification =="
if command -v strings >/dev/null 2>&1; then
  V=$(strings -el "$GAME/SkyrimSE.exe" 2>/dev/null | grep -A1 '^FileVersion$' | tail -1)
  echo "exe FileVersion: ${V:-n/a}   (want 1.6.1170.0)"
else
  echo "exe FileVersion: n/a (binutils 'strings' not installed — md5 covers it)"
fi
if command -v md5sum >/dev/null 2>&1; then
  M1=$(md5sum "$GAME/SkyrimSE.exe" | awk '{print $1}')
  M2=$(md5sum "$C/depot_$DEPOT_EXE/SkyrimSE.exe" | awk '{print $1}')
  if [ "$M1" = "$M2" ]; then
    echo "exe md5  : $M1  OK (matches pristine 1.6.1170 depot)"
  else
    echo "exe md5  : MISMATCH  game=$M1  depot=$M2" >&2
  fi
fi
grep AutoUpdateBehavior "$ACF" || echo "AutoUpdateBehavior key missing from $ACF!"

echo
echo "Done. Two rules from here on:"
echo "  1. Never launch Skyrim via the Steam client (Steam updates on manual launch)."
echo "  2. Never click Verify Integrity in Steam (re-pulls 1.7.104)."
echo "Launcher-only entry point; re-run this script if anything regresses."
echo
echo "Textures re-broken?  python3 scripts/bsa-check.py \"$GAME/Data/Skyrim - Textures\"*.bsa"