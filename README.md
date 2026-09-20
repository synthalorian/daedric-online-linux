# Daedric Online on Linux — GE Proton / umu guide

**Get the Daedric Online launcher running Skyrim Special Edition 1.6.1170 on
Linux (CachyOS / Arch), with the launcher → `skse64_loader.exe` →
`SkyrimSE.exe` chain working end-to-end under GE Proton.**

Every step here was verified live on 2026-09-19. This is the battle-tested
path, not a theory.

---

## The setup in one paragraph

Daedric Online is a Skyrim SE roleplay-server launcher (Electron/CEF app). It
must be the only entry point — it handles login, server selection, and then
spawns `skse64_loader.exe` → `SkyrimSE.exe`. To get that chain working on
Linux you need the **launcher and the game it spawns to share one wineserver
and one Steam bridge**. The way to do that: migrate the launcher into a **umu
prefix** (`umu-489830`), run it under **GE-Proton11-7**, and — the critical
bit — launch with **`UMU_USE_STEAM=1`** so GE keeps its `lsteamclient` bridge
enabled. Without that env var, the game dies silently at
`SteamAPI_Init(): Failed to load module 'C:\Program Files (x86)\Steam\steamclient64.dll'`.

---

## Prerequisites

| Thing | Version / Path |
|---|---|
| OS | CachyOS (Arch-based), KDE Plasma 6, Wayland + XWayland |
| Steam | installed at `~/.local/share/Steam`, running |
| umu-launcher | 1.4.3 (`umu-run`) |
| GE-Proton | **GE-Proton11-7** at `~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64` |
| Skyrim SE | 1.6.1170, `SkyrimSE.exe` size must stay **37157144** |
| Mods | Vortex-installed collection (115 mods) in the game `Data/` folder |
| Daedric launcher | the server launcher exe + its `AppData` config |

> **NEVER modify the game folder.** The launcher gates on a foreign-file list
> (see its `dist/main.js`) and on the exact `SkyrimSE.exe` size. Touch either
> and the launcher flags your install. Your mods go in via Vortex, not by hand.

---

## Step 1 — Install GE-Proton11-7

GE-Proton11-6 is **dead** for this app: wine-11.0 Staging aborts on
`win32u.NtGdiCreateColorSpace` (unimplemented). GE-Proton11-7 (released
2026-09-16) runs it.

```
mkdir -p ~/.local/share/Steam/compatibilitytools.d
cd ~/.local/share/Steam/compatibilitytools.d
# Download the x86_64 build (NOT aarch64 — easy to grab the wrong one)
# ~563 MB compressed; extract so you get:
#   ~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64/
#   .../GE-Proton11-7-x86_64/version   -> "1789520217 GE-Proton11-7"
```

The `version` file must exist — umu reads it to pick the Proton base.

## Step 2 — Create the umu prefix and migrate the launcher

The launcher originally ran from a plain-wine prefix. Plain wine can run the
launcher, but the game it spawns can't reach Steam (`S_API` wall) and the
whole stack is outside the Steam runtime. Migrate:

```
PREFIX=~/.local/share/Steam/steamapps/common   # the game
U=~/Games/umu/umu-489830                       # umu prefix, GAMEID=umu-489830

mkdir -p "$U/drive_c"
# Copy from your existing launcher prefix (or a fresh wine install):
#   drive_c/Program Files/DaedricOnline/           (launcher, 319 MB, 671 files)
#   drive_c/users/<user>/AppData/Roaming/Daedric Online/   (config, 2.6 MB)
#   drive_c/users/<user>/AppData/Local/daedric-launcher-updater/  (85 MB)
```

Key detail: in the umu prefix the user is `steamuser`, and `Z:\` maps to `/`
the same way it did in the plain-wine prefix. That means `settings.json`
(`gamePath: 'Z:\home\synth\.local\share\Steam\steamapps\common\Skyrim Special
Edition'`) needs **no rewrite**.

Keep `settings.json` intact from the old prefix — it holds `sessionToken`,
`accountToken`, `profileId` (4158 here), `gamePath`. Don't paste those tokens
into any repo or log.

## Step 3 — The launcher state: DISABLE DAEDRIC CLIENT (on purpose)

In the launcher UI, **"DISABLE DAEDRIC CLIENT" must be selected**. The status
bar then reads:

```
CLIENT  PARKED / READY
BUILD 4.99.596
"Currently OFF: Skyrim runs your own mods"
```

This is the correct config for a Vortex-managed collection. The launcher parks
its own overlay files and lets *your* mods run. Leave it parked.

Related: the first time you hit Play, the launcher says
**"8 required mods missing / Missing because the client-file sync above
didn't finish"** — that is **not** a real problem. It's the verify panel
complaining the client-file sync hasn't run yet because the client is parked.
Let the sync finish and the panel clears itself.

## Step 4 — Launch the launcher under GE (the exact env)

```
cd "/home/synth/Games/umu/umu-489830/drive_c/Program Files/DaedricOnline"

export GAMEID=umu-489830
export UMU_ID=umu-489830
export UMU_USE_STEAM=1          # <-- THE fix, see Step 5
export PROTONPATH=/home/synth/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64
export STEAM_COMPAT_CLIENT_INSTALL_PATH=/home/synth/.local/share/Steam
export SteamAppId=489830
export SteamGameId=489830

umu-run "Daedric Online.exe" --no-sandbox
```

Rules that matter here:

- **`cd` into the prefix's `Program Files/DaedricOnline` and pass the bare
  exe name.** Passing the full `C:\Program Files\...` path makes umu say
  `WARNING: Executable not found`.
- **`--no-sandbox` is required** for the CEF/Electron layer under wine.
- `WINEDEBUG` is deliberately **not** `-all` — you want the `[S_API]` verdict
  visible on screen while you verify.
- The launcher window appears at 1280x800; the game then launches on the same
  wineserver, inheriting this env.

## Step 5 — `UMU_USE_STEAM=1`: why the game died and this fixes it

Original failure — game dies silently right after:
```
skse64_loader.log:  hook thread complete / launching
```
...with no crash log, 0-byte `skse64.log`, plugin logs untouched. That's not
a game crash, it's a Steam bridge failure. Prove it with:

```
export WINEDEBUG=+seh
# ...launch...
# log shows:
# [S_API] SteamAPI_Init(): Failed to load module 'C:\Program Files (x86)\Steam\steamclient64.dll'
```

Why: GE-Proton's `proton` script, when it thinks it's an "umu without Steam"
launch (`"UMU_ID" in os.environ and os.environ.get("UMU_USE_STEAM") != "1"`),
appends `WINEDLLOVERRIDES=lsteamclient=d`. In wine override syntax **`d` =
disable** (GE's own table: `"winebth.sys": "d", #disable winebth.sys`). With
`lsteamclient` disabled, SteamAPI_Init falls back to `LoadLibrary`-ing the raw
Windows `steamclient64.dll`, whose imports (`tier0_s64.dll`,
`vstdlib_s64.dll`) don't exist in the prefix → load fails → silent exit.

With `UMU_USE_STEAM=1` exported, `umu_without_steam` is False, GE keeps
lsteamclient enabled **and** routes the launch through its builtin
`steam.exe` shim (`c:\windows\system32\steam.exe`), which brokers SteamAPI
against the running Steam client. The verdict flips to:

```
[S_API] SteamAPI_Init(): Loaded 'C:\Program Files (x86)\Steam\steamclient64.dll' OK.
```

Then `SkyrimSE.exe` boots, SKSE 2.2.6 initializes and scans the plugin
directory (ActorLimitFix, AnimationQueueFix, cbp, CommunityShaders,
CraftingCategories, CrashLogger, ...), `skyrim-platform` registers its browser
API, and the main menu comes up.

## Step 6 — In the launcher: Play → sync → Launch

1. Click **Play** (bottom-left of the window, text "Play singleplayer or
   another server").
2. If it shows a verify panel, ignore the "missing" list — its own detail
   line says `"Missing because the client-file sync above didn't finish."`
3. The launcher downloads **Client files 4.99.596** (grab a coffee; the first
   sync pulls textures). Status column goes `WORKING` → `READY`.
4. When the status shows `CLIENT READY / BUILD 4.99.596`, the bottom-right
   button becomes **LAUNCH**. Click it.
5. `skse64_loader.exe` spawns with `steam exe` detected, hooks
   `SkyrimSE.exe` 1.6.1170, and the game opens.

Keep the launcher open while you play — the launcher's own screen says so.

## Step 7 — Resolution (ultrawide / your desktop)

The game's resolution lives in the INI **inside the umu prefix**:

```
$HOME/Games/umu/umu-489830/drive_c/users/steamuser/Documents/My Games/Skyrim Special Edition/SkyrimPrefs.ini
```

```
[Display]
iSize W=2560
iSize H=1080
bFull Screen=1
bBorderless=0
```

Set `iSize W`/`iSize H` to your monitor's resolution and use `bFull Screen=1`
for true exclusive fullscreen (on an ultrawide this fixes the title-bar height
mismatch you get in windowed mode). The game writes this file itself when you
change resolution in Options → Display, so you can also just do it in-game.

## Step 8 — The launch script (KDE shortcut)

The `.desktop` entries at
`~/.local/share/applications/daedric-online.desktop` and
`~/Desktop/daedric-online.desktop` both point at
`~/.local/bin/daedric-online`. That script (in `scripts/daedric-online` of
this repo) is the hardened v4:

- single-instance guard (never kill a healthy launcher)
- **SIGKILL-only** cleanup (SIGTERM = graceful quit to Electron = fires the
  updater force-run → EBADF two-process race; never SIGTERM the launcher)
- stdio → logfile so Electron's stdio wrapping never hits EBADF
- the full proven env from Step 4, including `UMU_USE_STEAM=1`

---

## Troubleshooting table

| Symptom | Cause | Fix |
|---|---|---|
| Wine aborts `NtGdiCreateColorSpace` at startup | GE-Proton11-6 (and older) missing the export | Use GE-Proton11-7 |
| `[S_API] Failed to load module ...steamclient64.dll` then silent exit | `lsteamclient` disabled by GE on umu launches | Export `UMU_USE_STEAM=1` |
| umu `WARNING: Executable not found` | full `C:\...` path passed | `cd` into launcher dir, pass bare `Daedric Online.exe` |
| Game dies pre-SKSE with no crash log | almost always the bridge (see above) | `WINEDEBUG=+seh` to see the S_API verdict |
| "8 required mods missing" panel | client-file sync never completed | let the sync finish; panel says so itself |
| Launcher races / EBADF / updater relaunch | SIGTERM to Electron fires quitAndInstall | SIGKILL-only, chunked kill lists; single-instance guard |
| Launcher window blank or CEF crash | sandbox under wine | always pass `--no-sandbox` |

## Operational safety rules (learned the hard way)

1. **Never modify the game folder.** The launcher gates on a foreign-file list
   and on `SkyrimSE.exe` size 37157144. Vortex handles the mods.
2. **Never run distro wine against a umu prefix.** Always `umu-run` with the
   same `PROTONPATH`/env the prefix was created under.
3. **Never `pkill -f` a string that appears in your own command line.** Use
   chunked kill lists with explicit PIDs.
4. **Never click "INSTALL THE COLLECTION" / "GET MODS"** in the launcher — it
   would overwrite the Vortex install.
5. **Never click "RESTART" (update banner)** — it force-runs the updater and
   can race the running instance.

## File map

| Path | What it is |
|---|---|
| `~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64` | the working Proton |
| `~/Games/umu/umu-489830` | umu prefix holding the launcher |
| `.../drive_c/Program Files/DaedricOnline/` | the launcher (launch cwd) |
| `.../users/steamuser/Documents/My Games/Skyrim Special Edition/SkyrimPrefs.ini` | resolution INI |
| `.../users/steamuser/Documents/My Games/Skyrim Special Edition/SKSE/` | SKSE + plugin logs, crash logs |
| `~/.local/bin/daedric-online` | the KDE-shortcut launch script (v4) |

## Credits / war history

- GE-Proton11-6 diagnosed dead (`win32u.NtGdiCreateColorSpace`), GE-Proton11-7
  validated live.
- Launcher migrated plain-wine → umu prefix so the spawned game inherits the
  GE wineserver + Steam bridge.
- `UMU_USE_STEAM=1` identified as the bridge fix after `+seh` tracing showed
  the exact S_API load failure.
- Resolution forced to native ultrawide 2560x1080 fullscreen.

**The shield holds.** ⚫🦞