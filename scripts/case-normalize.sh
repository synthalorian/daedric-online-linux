#!/usr/bin/env bash
# case-normalize.sh — mirror Windows-case mod files to lowercase paths so the
# game can actually load them on Linux.
#
# Why: Skyrim's meshes reference loose textures with lowercase paths
# ("textures\0cce\dress_diffuse.dds") and its BSA lookups are
# case-insensitive — but mod archives frequently ship the loose files under
# capitalized roots ("Textures/", "Meshes/", "Interface/", "Scripts/").
# Windows ignores case and works; Linux filesystems are case-sensitive, so the
# file is never found: the mesh loads, the texture fails, and you get
# invisible gear and the red/green error-shader triangles. The engine logs
# nothing — this is a filesystem miss, not a BSA corruption.
#
# What it does: for every loose file under a loadable Data/ root whose path
# contains any uppercase character, create a hardlinked twin at the
# fully-lowercased path (target dirs created as needed). Purely additive:
# nothing is moved or overwritten. Idempotent — re-running is a no-op.
#
#   Meshes/actors/foo/bar_0.nif   ->  meshes/actors/foo/bar_0.nif
#   Textures/0CCE/Dress.dds       ->  textures/0cce/dress.dds
#
# Collisions: if the lowercase target already exists, the existing file wins
# (that is the path the engine would load anyway) and the pair is logged as a
# conflict, not overwritten.
#
# Fully portable — auto-discovers the Steam root (native or Flatpak), library
# folders and game install. Linux-only by design; on Windows this is a no-op
# concept (the filesystem ignores case).
#
# Options:
#   --dry-run            report what would be mirrored, change nothing
#   --restore LOGFILE    delete the mirror files recorded in a previous
#                        mirror log (reverts a run; conflicts are untouched)
#   --log LOGFILE        write per-file results (default: stdout only)
#   --data DIR           skip discovery, operate on this Data dir directly
#
# Overrides (env) — everything auto-detects; set these only to correct a guess:
#   STEAM_ROOT     Steam client install dir (default: ~/.local/share/Steam,
#                  flatpak path, or ~/.steam/steam — whichever exists)
#   STEAM_LIBRARY  a library folder containing the game (default: found by
#                  searching appmanifest_489830.acf across libraryfolders.vdf)
#   GAME           the game install dir (default: <library>/steamapps/common/Skyrim Special Edition)
#   ACF            the appmanifest path     (default: <library>/steamapps/appmanifest_489830.acf)
#   APP_ID         Steam app id             (default: 489830)
#   GAME_NAME      folder name in steamapps/common (default: "Skyrim Special Edition")
set -euo pipefail

APP_ID="${APP_ID:-489830}"
GAME_NAME="${GAME_NAME:-Skyrim Special Edition}"

# Loadable roots only — a file whose lowercased path does not start with one of
# these can never be resolved by the engine from that location, so mirroring it
# would just duplicate junk (installer-option folders, CalienteTools, fomod
# metadata, MeshPayload, ShaderCache, ...).
LOADABLE=(meshes textures scripts interface strings sound seq skse source music
          video fonts materials shaders)

DRY_RUN=0; RESTORE=""; LOGFILE=""; DATA_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --restore) RESTORE="${2:-}"; shift ;;
    --log)     LOGFILE="${2:-}"; shift ;;
    --data)    DATA_DIR="${2:-}"; shift ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
  shift
done

log() {  # printf to logfile AND stdout; dry-run prepends [DRY]
  local prefix=""; [ "$DRY_RUN" = 1 ] && prefix="[DRY] "
  printf '%s%s\n' "$prefix" "$1"
  # Only a real run writes the machine-log line ($2) — a dry-run log must
  # never be handed to --restore (it would delete nothing, but it would lie).
  if [ "$DRY_RUN" = 0 ] && [ -n "$LOGFILE" ] && [ $# -ge 2 ]; then
    printf '%s\n' "$2" >> "$LOGFILE"
  fi
}

# --- 0. target directory ---
if [ -z "$DATA_DIR" ]; then
  if [ -z "${STEAM_ROOT:-}" ]; then
    for cand in "$HOME/.local/share/Steam" \
                "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam" \
                "$HOME/.steam/steam" "$HOME/.steam/root"; do
      if [ -f "$cand/steamapps/libraryfolders.vdf" ]; then
        STEAM_ROOT="$cand"; break
      fi
    done
  fi
  [ -n "${STEAM_ROOT:-}" ] || { echo "Steam root not found. Set STEAM_ROOT or --data." >&2; exit 1; }

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
    echo "appmanifest_$APP_ID.acf not found — install the game, or set ACF/--data." >&2
    exit 1
  fi
  LIB="${ACF%/appmanifest_$APP_ID.acf}"; LIB="${LIB%/steamapps}"
  GAME="${GAME:-$LIB/steamapps/common/$GAME_NAME}"
  [ -d "$GAME" ] || { echo "game dir not found: $GAME — set GAME or --data." >&2; exit 1; }
  DATA_DIR="$GAME/Data"
fi
[ -d "$DATA_DIR" ] || { echo "data dir not found: $DATA_DIR" >&2; exit 1; }
echo "data dir   : $DATA_DIR"

# --- 1. restore mode ---
if [ -n "$RESTORE" ]; then
  [ -f "$RESTORE" ] || { echo "restore log not found: $RESTORE" >&2; exit 1; }
  removed=0
  while IFS= read -r line; do
    case "$line" in
      MIRROR\ *) rel="${line#MIRROR }" ;;
      MIRROR-COPY\ *) rel="${line#MIRROR-COPY }" ;;
      *) continue ;;
    esac
    # Safety: restore may only ever delete lowercase mirror paths — never a
    # capital-cased file (those are Vortex-managed mod files).
    case "$rel" in
      *[A-Z]*) echo "refusing to delete (not a lowercase mirror path): $rel" >&2; continue ;;
    esac
    tgt="$DATA_DIR/$rel"
    [ -f "$tgt" ] || continue
    rm -f "$tgt"
    # prune empty lowercase dirs we created (best effort, depth-first)
    d="$(dirname "$tgt")"
    while [ "$d" != "$DATA_DIR" ] && [ -d "$d" ] && rmdir "$d" 2>/dev/null; do
      d="$(dirname "$d")"
    done
    removed=$((removed+1))
  done < "$RESTORE"
  echo "restored: $removed mirror files removed (conflicts untouched)"
  exit 0
fi

[ -n "$LOGFILE" ] && : > "$LOGFILE"

# --- 2. mirror ---
added=0; skipped=0; conflicted=0
while IFS= read -r f; do
  rel="${f#$DATA_DIR/}"
  low=$(printf '%s' "$rel" | tr 'A-Z' 'a-z')
  [ "$rel" = "$low" ] && continue
  first=$(printf '%s' "$low" | cut -d/ -f1)
  ok=0
  for r in "${LOADABLE[@]}"; do
    if [ "$first" = "$r" ]; then ok=1; break; fi
  done
  [ "$ok" = 1 ] || continue
  tgt="$DATA_DIR/$low"
  if [ -e "$tgt" ]; then
    if [ "$(stat -c%s "$f")" = "$(stat -c%s "$tgt")" ] && cmp -s "$f" "$tgt"; then
      skipped=$((skipped+1))
    else
      conflicted=$((conflicted+1))
      log "CONFLICT kept existing: $rel" "CONFLICT $rel"
    fi
    continue
  fi
  if [ "$DRY_RUN" = 1 ]; then
    added=$((added+1))
    log "would mirror: $rel" "MIRROR $low"
    continue
  fi
  mkdir -p "$(dirname "$tgt")"
  if cp -al "$f" "$tgt" 2>/dev/null; then
    added=$((added+1))
    log "mirrored: $rel" "MIRROR $low"
  else
    cp -a "$f" "$tgt" && added=$((added+1)) && log "mirrored (copy fallback): $rel" "MIRROR-COPY $low"
  fi
done < <(find "$DATA_DIR" -type f)

echo
echo "== result =="
echo "mirrored=$added  already-lowercase/identical=$skipped  conflicts-kept-existing=$conflicted"
echo "(conflicts keep the existing lowercase file — it is the path the engine loads anyway)"
if [ "$DRY_RUN" = 1 ]; then
  echo "dry run — nothing was written. Re-run without --dry-run to apply."
else
  echo "re-run any time: idempotent, and Vortex re-deploys land at the lowercase paths automatically."
fi