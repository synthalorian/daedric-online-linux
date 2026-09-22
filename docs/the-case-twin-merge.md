# The case-twin merge: red placeholders from split-case mesh dirs

Phase 6 of the mesh wars: the fix that finally put out the red diamonds.

## The symptom

Red diamond placeholder on a male NPC (hold-guard armor). No console click
possible (server-side NPC), no complaint in EngineFixes.log — missing MESHES
don't log there, only textures do.

## The mechanism: two real dirs, one coin flip

Case-normalize and the phase-4/5 mirrors left **pairs of real directories
differing only in case** — `1_Nordwar` next to `1_NordWar`, `whiterun` next
to `Whiterun`. Wine's lookup rule is *exact case first, then CI scan*: an ESP
that references `Armor_Replacer\1_NordWar\ScaleSteel\ArmorM_1.nif` exact-matches
the `1_NordWar` dir — and if that dir only holds the female files while the
male files live in `1_Nordwar`, the mesh is missing. Red diamond.

Same file, one tree apart. 503 ESP-referenced meshes were invisible this way.

## Diagnosing without a console click

1. Harvest mesh refs from the Sentinel esps (`scripts/mesh-case-deploy.py
   --dry-run` — but its gap logic lowercases the WHOLE path, so post-move
   trees report false gaps).
2. The real test is a **Wine-semantics resolver**: walk each path component,
   exact-case match first, CI fallback; then check BSA contents for the rest
   (`scripts/bsa-check.py`'s parser lists every mesh in every BSA).
3. Refs that survive both = true red-diamond candidates.

## The fix: merge, don't mirror

`scripts/merge-mesh-case-twins.py` (dry-run default, `--apply` to execute):

- **`--merge SRC DST`** — fold a case-twin dir into its canonical sibling.
  Moves unique files, dedupes identical content (inode/md5), and on real
  content conflicts **keeps the NEWER file** — the skew was raw Nexus archive
  (2023) vs Bodyslide/HIMBO-built output (2026), and the built mesh is what
  the load order renders.
- **`--import STAGE_ROOT`** — import an extracted mod archive, resolving each
  path component case-insensitively into existing dirs so no NEW twins get
  created. Filled the 273 meshes that existed nowhere loose (male NordWar
  Chainmail etc. were only ever inside `Sentinel - Required Resources`).

Merged pairs: `1_Nordwar`→`1_NordWar`, `2_Nord/fur`→`Fur`, and the nine
`nordwar/sonsofskyrim` hold dirs (armors, dawnstar, falkreath, markarth,
morthal, oficerssc, riften, solitude, whiterun). Result: **503 → 2** missing
refs. The two survivors (`DynamicLoweredHoods/LoweredMonkHood_[FM]_1.nif`)
are dead references for a hood mod that isn't installed — benign.

## Rules this phase added

- **Two real dirs that differ only in case are a loaded gun.** Wine exact-case
  matching makes the split deterministic, not random — whichever dir the ESP's
  spelling matches wins, and the other dir's unique files are dead.
- **After a merge, one dir serves every spelling.** The surviving dir's own
  case doesn't matter; Wine CI resolves it either way.
- **MESHES: move, never symlink** (double-load crash). Hardlink mirrors are
  fine ONLY as deliberate ref-driven twins (phase 4/5) — not as accidental
  split-content dirs.
- **Content conflicts skew by version.** Newer mtime = Bodyslide build output
  = what the game should render. Archive originals are superseded.
- **Re-run the merge after every launcher sync / Vortex deploy** — both can
  re-create lowercase twins. The script is idempotent.

## Postscript: the launch crash that wasn't the merge

Right after the merge, two launches died at ~3 s uptime in
`OpenAnimationReplacer.dll` `Hooks::UIHooks::CreateD3D11` — renderer/UI hook
init, with DXVK config strings (`dxvk.hideIntegratedGraphics`, `"True"`,
`"False"`) on the stack and an ASCII fragment (`"Ture"`) sitting in a pointer
register. Looked scary, pointed at D3D11 device creation — not at meshes.

The tell: **armor meshes don't load at 3.3 s.** The main menu never touches
`Armor_Replacer`. A mesh merge cannot crash a UI hook.

The bisect that proved it — **standalone boot smoke test**, same env the
launcher uses, no launcher:

```bash
cd "$GAME"   # the prefix's Skyrim Special Edition dir
GAMEID=umu-489830 UMU_ID=umu-489830 UMU_USE_STEAM=1 \
PROTONPATH="$HOME/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64" \
STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.local/share/Steam" \
SteamAppId=489830 SteamGameId=489830 \
WINEDLLOVERRIDES="winemenubuilder.exe=d;d3dcompiler_47=n,b" \
timeout 75 umu-run skse64_loader.exe
```

Booted clean: `init complete` in skse64.log, no new crash log, process alive
past the crash window. Next launcher launch worked too. Root cause of the two
17:25 crashes: they **raced the merge mid-flight** — files moving under a
starting wineserver. Lesson: don't launch while the merge script is running,
and when a crash's stack doesn't touch the subsystem you just changed, test
standalone before reverting.
