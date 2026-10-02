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
enabled. Without that env var, the game dies silently at the
`steamclient64.dll` load.

That env var is the fix when `$HOME` is `/home/<user>`. On Fedora Atomic
(Bazzite, Silverblue, Kinoite) `umu-run` still leaves the Steam install path
empty — the launcher opens and Skyrim never spawns. Do not keep retrying
Step 4 if the log says `path /var/home`. The working launch is the non-Steam
shortcut in **Fedora Atomic / Bazzite** below.

**The build question — the game must end at 1.6.1170.** The launcher's client
sync (Step 6) *is* the downgrade: its internal downloader is pinned to the
1.6.1170 manifests and writes that build's data into the game folder. That
same downloader has one known bug (it corrupts LZ4 blocks in the textures
BSAs) and it never touches the exe — so a Steam-console depot install (Step
7) follows to complete the pin with pristine files. **The Step 7 build is the
one with the working textures.** Don't settle for the launcher-synced data
alone.

---

## Distro portability

Yes — every step here is distro-agnostic in principle. The whole flow is
Steam client + Proton + game-folder mechanics: no kernel features, no init
systems, no distro packaging. Verified live on **CachyOS (Arch, KDE Plasma 6,
Wayland)**; any mainstream Linux with Steam + Proton support should follow
the same path, except the launch step on Fedora Atomic (caveat below). The
only distro-dependent choices are *install
methods*:

| Component | Install on any distro |
|---|---|
| Steam | official client (native or Flatpak) — must be running for the Steam bridge (Step 5) and the console (Step 7) |
| GE-Proton11-7 | manual download to `~/.local/share/Steam/compatibilitytools.d/` — no packaging involved, identical on every distro |
| umu-launcher | Flathub, or the distro's package where available (AUR on Arch) |
| Vortex or Amethyst | see **Mod manager lanes** — Vortex is the verified path; Amethyst is the native-Linux alternative |

Caveats:

- **Flatpak Steam**: paths shift under `~/.var/app/com.valvesoftware.Steam/.local/share/Steam` and the console command becomes
  `flatpak run com.valvesoftware.Steam steam://open/console`. That's the one
  place paths differ — `scripts/downgrade-1.6.1170.sh` auto-discovers both
  native and Flatpak Steam roots, so the Step 7 script needs zero edits either
  way.
- **Base tools**: the flow needs `rsync`, `python3` (present on every
  mainstream distro) and GNU `strings` (`binutils`) for the version check —
  the script degrades to md5-only verification if `strings` is missing.
- **Case-sensitive filesystems**: Skyrim meshes reference loose textures with
  lowercase paths and BSA lookups are case-insensitive, but mod archives often
  ship `Textures/`/`Meshes/` capitalized — Windows ignores that, Linux does
  not. If modded armor is invisible or shows red/green error triangles while
  vanilla is fine, run `scripts/case-normalize.sh` (mirrors every loose file
  to its lowercase path; idempotent). Full forensics:
  `docs/the-linux-case-war.md`.
- **Desktop environment**: the Step 9 shortcut uses `.desktop` paths that work
  on any DE; the values shown are just this machine's example.
- **Linux-only by design**: macOS and Windows use different Steam depot
  layouts and client paths — this is the Linux path, full stop.
- **Fedora Atomic (Bazzite, Silverblue, Kinoite)**: `$HOME` is
  `/var/home/<user>`, not `/home/<user>`. `umu-run` opens the launcher and
  never spawns Skyrim (`steam_install_path ""`). Add the launcher exe as a
  non-Steam game under GE-Proton11-7 instead. Native Steam was the reported
  case. The downgrade and the mod-manager steps do not change. Section:
  **Fedora Atomic / Bazzite**, after Step 5.

---

## Mod manager lanes

The collection comes in through a mod manager that **writes real files into
the Steam Skyrim `Data/`**. The launcher hash-checks that tree (then the umu
prefix copy of it). Two things fail that test permanently:

- **Mod Organizer 2.** Its VFS keeps the real `Data/` clean, so the launcher
  reports every mod missing.
- **Amethyst's VFS deploy**, for the same reason. Amethyst is allowed (Lane D).
  Its VFS mode is not.

Nexus ships **Windows Vortex binaries only**. Lanes A–C are Vortex. Lane D
is the native-Linux alternative. Use one manager. Do not point Vortex and
Amethyst at the same Skyrim.

### Lane A — Arch / CachyOS (native package)

```bash
paru -S vortex    # or: yay -S vortex
```

Wayland users launch it with `GDK_BACKEND=x11 vortex` — Vortex is an X11 app.

### Lane B — any distro incl. immutable (Bazzite, SteamOS, Silverblue): the AppImage

Grab the **linux-vortex AppImage** from its GitHub releases. It compiles the
*official* `Nexus-Mods/Vortex` source — Nexus just doesn't publish Linux
builds, so "unofficial" describes the packaging, not the code. Judge it by
the upstream, not the repo.

- Make it executable, run it, done — no package manager, survives atomic
  updates, lives happily in `/var/home` on Bazzite.
- Wayland: `GDK_BACKEND=x11 ./Vortex-*.AppImage`.
- **Drive-probe bug**: the staging-folder picker can throw
  *"OS is unsupported"* on a **perfectly healthy ext4 drive** if its
  mountpoint is non-standard (hand-rolled fstab mounts like `/var/mnt/HDD`;
  normal automounts live under `/run/media`). It's the AppImage's
  `/proc/mounts` parser failing, not your filesystem. Workaround:
  ```bash
  sudo mount --bind /var/mnt/HDD/SteamLibrary ~/SteamHDD
  ```
  Point Vortex staging under the home-relative bind path and persist the
  bind in fstab (`none bind`). First update the AppImage — fixes land.
  Capture the real exception with `./Vortex-*.AppImage 2>&1 | tee ~/vortex.log`.

### Lane C — fallback: Windows Vortex via Lutris

If the AppImage still refuses (staging + game on the same healthy ext4
partition and it won't deploy), install the **Windows Vortex through
Lutris** — the community installer wires Wine + .NET for you. This lane has
two traps, both avoidable:

1. **Do NOT install Skyrim inside the Lutris/Wine prefix.** Wine maps
   `Z:` → `/`, so point Vortex's game path at the *native Linux* Skyrim
   install, e.g. `Z:\home\<you>\.local\share\Steam\steamapps\common\Skyrim
   Special Edition` (or wherever your library is).
2. **Set Vortex's mod-staging folder explicitly to a `Z:` path on the same
   partition as the game** — e.g. `Z:\home\<you>\VortexStaging`. The default
   lands *inside the Wine prefix* (its system drive), which is a different
   "partition" as far as hardlinks are concerned and puts you right back at
   the deployment wall.

Wine hardlinks map to the native `link()` syscall, so once staging and game
share a partition, Vortex deploys normally and the rest of this guide is
identical.

### Lane D — Amethyst (native Linux alternative, including Bazzite)

[Amethyst](https://github.com/ChrisDKN/Amethyst-Mod-Manager) is a Linux-native
manager. MO2-shaped window, not MO2. It can install and revision-update the
Nexus collection
[`ptmvzi`](https://www.nexusmods.com/games/skyrimspecialedition/collections/ptmvzi).
Use it when Vortex cannot deploy, or on a fresh install. Do not migrate a
working Vortex tree onto it in the middle of a revision bump.

This lane is **not** the path the rest of this guide was verified on. The
launcher's "mod files don't match" gate is the verifier, not Amethyst's
install-complete dialog.

**Install on Bazzite / any immutable distro: AppImage, not Flatpak.** A
Flatpak cannot see the Steam library without a filesystem override — same
trap as Flatpak Vortex. The installer only downloads the GitHub-release
AppImage into `~/Applications` and writes a desktop file. No sudo. Read it
before running it:

```bash
curl -fsSL -o /tmp/Amethyst-MM-installer.sh \
  https://raw.githubusercontent.com/ChrisDKN/Amethyst-Mod-Manager/main/src/appimage/Amethyst-MM-installer.sh
bash /tmp/Amethyst-MM-installer.sh
```

Or download the AppImage from the
[releases page](https://github.com/ChrisDKN/Amethyst-Mod-Manager/releases)
and install it with Gear Lever (already on Bazzite). Config and the default
staging folder land in `~/.config/AmethystModManager`.

**Rules. All of them.**

1. Game path = the **Steam** Skyrim, never the umu prefix. Staging must be
   on the same filesystem as that Skyrim. Hardlinks cannot cross drives, and
   on Bazzite they cannot cross btrfs subvolumes either — home and a second
   Steam library often are different subvolumes.
2. Deploy method = **hardlink**. Symlink only when hardlink is impossible.
   **Never VFS.**
3. Turn **case-alias symlinks off** (quick configure) before deploy. Those
   are extra `data` / `textures` / `TEXTURES` directory symlinks. This
   guide's mesh fixes assume one path per file. Aliases that get copied
   into the prefix are the double-load crash.
4. After deploy, `skse64_loader.exe` must still exist under that name next
   to `SkyrimSE.exe`. Amethyst renames the script extender onto the Bethesda
   launcher so Steam's Play button launches SKSE. The Daedric launcher
   spawns `skse64_loader.exe`. If the name is gone, copy it back. Do not
   launch Skyrim from Steam or from Amethyst.
5. Do not run LOOT. The server wants the collection's load order. If you
   sorted, Nexus → Collections → Reset Load Order.
6. Amethyst's automatic DLL overrides apply only when **it** launches the
   game. They do nothing for the umu launch. Community Shaders still needs
   the native `d3dcompiler_47.dll` in the prefix (troubleshooting table).
7. Collection: paste the `ptmvzi` URL, install or update to the revision the
   launcher banner names. Premium downloads in-app. A free account downloads
   one mod at a time in the browser; Amethyst watches the downloads folder.
   Do not click **INSTALL THE COLLECTION** / **GET MODS** in the Daedric
   launcher — that overwrites this install.
8. Amethyst applies the collection's FOMOD choices itself. That has not been
   verified against this collection's pins. If the launcher then says an esp
   is "wrong version/edited", that file or choice is wrong. Reinstall that
   mod from the pinned file. Do not clean it in xEdit.
9. `Data_core` next to `Data/` is Amethyst's vanilla backup. The bridge
   rsync below is `Data/` only. Do not copy `Data_core` into the prefix.

### Vortex "No deployment method available" (red banner, fixes greyed out)

Vortex can write **nothing** into the game dir. The exact reason lives in the
notification bell — read it first. Then triage in order:

1. `df -T <game path>` — `exfat`/`vfat` = dead end (no links possible at all;
   move the game to ext4 via Steam → Settings → Storage); `ntfs` = hardlinks
   impossible and `chown` is ignored unless mounted with `permissions`.
2. `ls -ld` shows root ownership → `sudo chown -R $USER:$USER <steam
   library>`, then **fully restart Vortex** (it caches the deployment check;
   closing the window is not enough).
3. `mount` shows `ro` → remount `rw`.
4. Still grey → how is Vortex installed: Flatpak = sandbox can't see the
   drive (`flatpak override --filesystem=<path>` or switch to the AppImage);
   AppImage on a non-standard mountpoint = the drive-probe bug above.
5. Verify writability directly: `touch <Data>/testwrite && rm <Data>/testwrite`.

### After any deploy: bridge the mods into the prefix

Whichever lane you use, the manager deploys to the **Steam** Skyrim `Data/`.
The launcher runs from the **umu prefix** and needs the same files there:

```bash
rsync -a "<steam Skyrim>/Data/" "<prefix game dir>/Data/"
```

Trailing slash on the source. No `--delete` — the prefix holds server-pushed
files the Steam tree does not. Re-run after every deploy.

`-a` copies hardlinked files as real files. It does **not** follow
symlinks; it reproduces them. A hardlink deploy is what you want. If the
deploy had to be symlinks, use `rsync -aL` instead, and only after
case-alias symlinks are off — `-L` follows directory symlinks and will
duplicate the tree if those aliases exist. Never symlink-deploy into the
prefix itself. That is the mesh double-load crash.

Enable every plugin the new revision added in the **umu**
`AppData/Local/Skyrim Special Edition/Plugins.txt`, as `*Name.esp`. Neither
Vortex nor Amethyst writes that file when its game path is the Steam
library.

If you can't find the paths:

```bash
find ~ /run/media -maxdepth 8 -type d -iname "Skyrim Special Edition" 2>/dev/null
find ~ -maxdepth 6 -type d -name umu-489830 2>/dev/null
```

Flatpak Steam nests under `~/.var/app/com.valvesoftware.Steam/...`; Bazzite
home is `/var/home/<user>` — `$HOME` handles it, `~` inside quotes does not.

---

## Prerequisites

| Thing | Version / Path |
|---|---|
| OS | any Linux with Steam — verified live on CachyOS (Arch, KDE Plasma 6, Wayland); see Distro portability above |
| Steam | installed at `~/.local/share/Steam`, running |
| umu-launcher | 1.4.3 (`umu-run`; Flathub or distro package — see Distro portability) |
| GE-Proton | **GE-Proton11-7** at `~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64` |
| Skyrim SE | ends at **1.6.1170** (exe FileVersion `1.6.1170.0`, size **37157144**). Start from any build — the launcher sync (Step 6) pulls the 1.6.1170 data and the Steam-console install (Step 7) completes the pin with pristine files: the build with the working textures. Steam's Aug-2026 auto-update (1.7.104) is handled by the same flow |
| Mods | collection in the game `Data/` folder, via Vortex (verified) or Amethyst (Lane D) |
| Daedric launcher | the server launcher exe + its `AppData` config |

> **Never hand-modify the game folder.** The launcher gates on a foreign-file
> list (see its `dist/main.js`) and on the exact `SkyrimSE.exe` size. Your
> mods go in via the mod manager, not by hand. The one sanctioned exception: the Step 7
> console install, which re-arms the exact vanilla 1.6.1170 files (including
> the exe) the launcher checks for.

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
# Copy from your existing launcher prefix, or extract a fresh one.
# Do not run DaedricOnline-Setup.exe — see
# docs/the-launcher-website-update.md
#   drive_c/Program Files/DaedricOnline/           (launcher app tree)
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

Launcher **1.3.79** (2026-10-01) narrowed one slice of that panel: mods that
ship with the client files (Immersive Armors Retexture and the same class)
no longer show as missing before those files finish downloading. Press Play.
That does not retire the parked-client message on older builds.

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

## Fedora Atomic / Bazzite — when `umu-run` never spawns the game

Step 4 is the verified path when `$HOME` is `/home/<user>`. It is not the
path on Fedora Atomic.

Field report, not reproduced on the CachyOS machine this guide was written
from: **Bazzite (Fedora Atomic, KDE), native Steam, Nvidia 2080 Super, umu
1.4.4, GE-Proton11-7.** The launcher opened. Skyrim never spawned. The full
Step 4 env, including `UMU_USE_STEAM=1`, was already set. Every attempt
logged:

```
Proton: Error: unable to use parent for game drive, path /var/home
setup_steam_files steam_install_path ""
[S_API] SteamAPI_Init(): Failed to load module 'steamclient64.dll'
```

Bazzite's real home is `/var/home/<user>` (`/home` is a symlink). Proton's
game-drive check only accepts a directory named `steamapps` whose parent is
writable and on the same device. `/var/home` fails that check. Proton then
hands the bridge an empty Steam install path (`steam_install_path ""`).
`UMU_USE_STEAM=1` does not fill that path. That variable only stops GE from
disabling `lsteamclient` (this step). Empty install path, no
`steamclient64.dll`, no game. Retuning the umu env will not fix it — this
report already had the full Step 4 env.

A lone `unable to use parent for game drive, path /home` is normal umu noise.
The signature here is `path /var/home` plus `steam_install_path ""`.

**What worked:** add the launcher exe to Steam as a non-Steam game and let
Steam's own Proton build the bridge.

1. GE-Proton11-7 must already be in
   `~/.local/share/Steam/compatibilitytools.d/`. Restart Steam if it is not
   in the compatibility-tool list.
2. Steam → **Games → Add a Non-Steam Game to My Library** → Browse to
   `Daedric Online.exe`. That is the extracted launcher
   (`Program Files/DaedricOnline/Daedric Online.exe`), not
   `DaedricOnline-Setup.exe`, and not `SkyrimSE.exe`.
3. Right-click the shortcut → **Properties** → **Compatibility** → check
   **Force the use of a specific Steam Play compatibility tool** →
   **GE-Proton11-7**.
4. Launch options: `%command% --no-sandbox`
5. Press Play on that shortcut.

Steam fills the compat paths before Proton starts, so the install path is
no longer empty. Reported result: the game spawned and connected.

This replaces Step 4 and the Step 9 `umu-run` script. It does not replace
the downgrade, the mod manager, or the case fixes — those still land in the
Steam Skyrim the launcher points at. Steam creates its own `compatdata/`
prefix for the shortcut. Leave it. Log in again if the umu prefix's
`settings.json` does not come along, and point the launcher at the **Steam**
Skyrim.

**Do not press Play on Skyrim Special Edition in the library.** That is the
Steam app. It will update off 1.6.1170. The non-Steam shortcut is the
launcher exe only. Rule 7 still applies to the Skyrim app.

Silverblue, Kinoite, and other ostree spins with home at `/var/home` hit the
same wall. A normal `/home/<user>` distro stays on Step 4.

Mechanism: `docs/the-atomic-steam-bridge.md`.

## Step 6 — In the launcher: Play → sync → Launch

1. Click **Play** (bottom-left of the window, text "Play singleplayer or
   another server").
2. If it shows a verify panel, ignore the "missing" list — its own detail
   line says `"Missing because the client-file sync above didn't finish."`
3. The launcher downloads **Client files 4.99.596** (grab a coffee). This sync
   *is* the downgrade — the launcher's internal downloader is pinned to the
   1.6.1170 manifests (its download sizes match the 1.6.1170 depots exactly)
   and writes that build's data into the game folder. Status column goes
   `WORKING` → `READY`.
4. When the status shows `CLIENT READY / BUILD 4.99.596`, the bottom-right
   button becomes **LAUNCH**. Click it.
5. `skse64_loader.exe` spawns, hooks `SkyrimSE.exe`, and the game opens — if
   the version gate is still red instead, that's expected at this point: run
   Step 7 first, then return here.

Keep the launcher open while you play — the launcher's own screen says so.

**Texture integrity (read once):** the same sync that downgrades is also
this launcher's one known bug — its downloader mangles LZ4 DDS blocks inside
the vanilla `Skyrim - Textures*.bsa` files it writes, and its "repair" path
re-copies the corruption. Grey/black textures right after the sync are
**expected**, not a surprise. The Step 7 console install replaces those BSAs
with pristine depot files — **the Step 7 build is the one with the working
textures**. Verify after Step 7:

```bash
python3 scripts/bsa-check.py "$GAME/Data/Skyrim - Textures"*.bsa   # zero 'garbage' = clean
```

Full forensics: `docs/the-texture-corruption-war.md`.

## Step 7 — Install clean 1.6.1170 via the Steam console

Do this right after the sync. The sync downgraded the game's data but
(a) corrupted LZ4 blocks in the textures BSAs and (b) never touched the exe —
which is why the launcher can still show the version gate red at this point:
the exe and the BSAs are not yet the pristine 1.6.1170 build. The console
install completes the pin:

1. Open the Steam console: `steam steam://open/console` (or relaunch with
   `steam -console`).
2. Download the three 1.6.1170 depots — one at a time, wait for each to
   finish. The manifest IDs pin the exact 1.6.1170 build; without them you
   get the current/latest build (1.7.104 — useless):

   ```
   download_depot 489830 489831 8442952117333549665
   download_depot 489830 489832 8042843504692938467
   download_depot 489830 489833 1914580699073641964
   ```

3. Merge + hold with the repo script. It is fully portable — auto-discovers
   the Steam root, library folders, game install and depot downloads (override
   with `STEAM_ROOT`/`STEAM_LIBRARY`/`GAME`/`C`/`ACF` if it guesses wrong):

   ```bash
   bash scripts/downgrade-1.6.1170.sh
   ```

The script re-installs every vanilla file from the pinned depots (healing the
corrupted BSAs), installs the 1.6.1170 exe (37,157,144 B), and sets
`AutoUpdateBehavior=2` so Steam can't re-update. **This is the build with the
working textures.** Confirm:

```bash
python3 scripts/bsa-check.py "$GAME/Data/Skyrim - Textures"*.bsa   # zero 'garbage'
strings -el "$GAME/SkyrimSE.exe" | grep -A1 '^FileVersion$'         # 1.6.1170.0
```

Two permanent rules from here: **never** launch the game via the Steam
client, **never** click Verify Integrity — both re-pull 1.7.104 and slam the
gate shut. The launcher is the only entry point. Mechanisms + depot breakdown:
`docs/the-1.6.1170-version-gate.md`.

## Step 8 — Resolution (ultrawide / your desktop)

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

## Step 9 — The launch script (KDE shortcut)

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

Fedora Atomic: do not use this script. It hits the empty `steam_install_path`
failure. Use the non-Steam shortcut in **Fedora Atomic / Bazzite**.

## Updating the launcher from the website

Discord will sometimes say grab the launcher from the website instead of
waiting on the in-app updater. On Linux that is a 7z extract into
`Program Files/DaedricOnline`, not a double-click of
`DaedricOnline-Setup.exe`.

The site file is
`https://daedriconline.com/download/DaedricOnline-Setup.exe`. It is done
only when its size and base64 sha512 match
`GET http://play.daedriconline.com:3000/launcher/latest.yml`. If
`AppData/Local/daedric-launcher-updater/pending/temp-DaedricOnline-Setup-*.exe`
has stopped short of that size, do not close the launcher — a normal quit
installs the partial. SIGKILL by PID, delete the partial, extract, relaunch.
Full procedure, the 2026-10-01 1.3.60 → 1.3.79 check, and what not to touch:
`docs/the-launcher-website-update.md`.

---

## Troubleshooting table

| Symptom | Cause | Fix |
|---|---|---|
| Game won't launch at all (launcher does nothing / instant exit) | **Steam client not running** — the launcher's Steam bridge needs the live client, even with `UMU_USE_STEAM=1` | Start Steam first, then launch Daedric |
| Wine aborts `NtGdiCreateColorSpace` at startup | GE-Proton11-6 (and older) missing the export | Use GE-Proton11-7 |
| `[S_API] Failed to load module ...steamclient64.dll` then silent exit | `lsteamclient` disabled by GE on umu launches | Export `UMU_USE_STEAM=1` |
| Launcher opens, Skyrim never spawns; log has `path /var/home` and `steam_install_path ""` | Fedora Atomic home. Proton will not derive a Steam install path from `/var/home`. `UMU_USE_STEAM=1` is already set and does not fill it | Add `Daedric Online.exe` as a non-Steam game, force GE-Proton11-7, launch option `%command% --no-sandbox`. Do not Play the Skyrim library entry. See **Fedora Atomic / Bazzite** |
| umu `WARNING: Executable not found` | full `C:\...` path passed | `cd` into launcher dir, pass bare `Daedric Online.exe` |
| Game dies pre-SKSE with no crash log | almost always the bridge (see above) | `WINEDEBUG=+seh` to see the S_API verdict |
| "8 required mods missing" panel | client-file sync never completed | let the sync finish; panel says so itself |
| Launcher races / EBADF / updater relaunch | SIGTERM to Electron fires quitAndInstall | SIGKILL-only, chunked kill lists; single-instance guard |
| Launcher window blank or CEF crash | sandbox under wine | always pass `--no-sandbox` |
| Version gate red / "game version not supported" | the exe is still a Steam build (1.7.x) — the launcher sync never replaces it | Step 7: `download_depot` the three manifests, then `scripts/downgrade-1.6.1170.sh` |
| Textures grey/black; `N textures failed to load` in EngineFixes.log | launcher's own download corrupted LZ4 DDS blocks in the textures BSAs | run Step 7 (`scripts/downgrade-1.6.1170.sh`) — or Steam Verify if the build is already correct — then `scripts/bsa-check.py` to confirm (never the launcher's repair) |
| Modded armor invisible / red-green triangles, vanilla clean, `EngineFixes.log` silent | case war — mod archives ship `Textures/`/`Meshes/` capital, NIFs request lowercase, Linux filesystems are case-sensitive | `bash scripts/case-normalize.sh` (mirrors loose files to lowercase paths; idempotent, reversible). See `docs/the-linux-case-war.md` |
| Red triangle + white `!` (missing diffuse) or green triangle (missing envmap) after the case fix | the texture exists nowhere — not loose, not in any BSA (the missing-texture board) | `bash scripts/bsa-names.sh` + `python3 scripts/true-missing.py` to list the board; clear entries only from real owned archives (extract-only where the base mod must not install). See `docs/the-missing-texture-board.md` |
| Armor renders as a placeholder (bare body / error mesh) but every texture on its meshes exists | mesh-side case war — Sentinel esps reference cap roots (`NordWar\SonsOfSkyrim\...`), the deploy pipeline lowercased every loose file, and loose lookups are case-EXACT | `python3 scripts/mesh-case-deploy.py` (ref-driven reverse mirror: hardlinks each esp-referenced `.nif` at the exact case from its lowercase twin; idempotent). See Phase 4 in `docs/the-missing-texture-board.md` |
| Hard crash ~30 s after load, CrashLogger shows `Marker_error:0` BSTriShapes + `Marker_error` BSFadeNodes, `mov r12,[rbp+0x20]` with `rbp=0` | failed loose mesh load at exact case → error substitute; the engine's update pass null-derefs walking the substitute. Vanilla monster: `Skyrim.esm` refs were never audited (starter Iron cuirass both-gender refs shadowed by lowercase loose files) | re-run `python3 scripts/mesh-case-deploy.py` against the five vanilla masters (`--esp Skyrim.esm --esp Update.esm --esp Dawnguard.esm --esp HearthFires.esm --esp Dragonborn.esm`) — deploys the 1,200 lowercase-twin refs at exact case. See Phase 5 in `docs/the-missing-texture-board.md` |
| Hard crash during load-in (~21 s uptime, before the world spawns), CrashLogger shows `MaleHeadIMF` + `BSFaceGenBaseMorphExtraData` + `QueuedHead`/`BSTaskManagerThread`, crash `mov r12d,[rbp+0x40]` with `rbp=0x10`, `skee64.dll` (RaceMenu) mid-chain | over-broad exact-case twins in the **actor tree** (`meshes/Actors/Character/Character Assets/` head/eyes/faceparts/hair/body/skeleton): they flipped BSA-vanilla fallback → modded-loose content for the FaceGen head build, and RaceMenu's morph walk null-derefs | do **not** re-deploy twins under `meshes/Actors/` — the deploy tool excludes the actor tree by default. Rollback = unlink the exact-case actor twins (366 did it, Phase 5.1). See Phase 5.1 in `docs/the-missing-texture-board.md` |
| Whole mods absent (armor mod just doesn't exist in game) | installer-option folders deployed raw into `Data/` (Vortex never ran the mod's installer) | reinstall those mods in Vortex and pick the options — launcher closed; see `docs/the-linux-case-war.md` |
| Game back on 1.7.x after a successful downgrade | launched via Steam client, or Verify clicked | re-run the Step 7 script; keep AutoUpdateBehavior=2, launcher-only entry point |
| "N mod files don't match the server" (e.g. CBBE 3BA `3BBB.esp` / `RaceMenuMorphsCBBE.esp`, "was edited", "different version") | launcher verifies tracked esp files against its bundled asar manifest (per-file sha256, canonical archive by md5); a Vortex reinstall with different installer options changed the bytes | extract the manifest-pinned archive entries, hash-verify, patch `Data/` **and** Vortex staging; see `docs/the-mod-verification-gate.md` |
| Community Shaders: `N shaders failed to compile` / `E5000: unexpected KW_NAMESPACE` (the compile dialog stuck near 0% with hundreds already failed) | Wine's builtin `d3dcompiler_47.dll` (~370 KB stub) can't parse HLSL `namespace`. Failures are instant, not a slow compile. DXVK is innocent | Press Escape to leave the dialog. Deploy the native ~4.9 MB `d3dcompiler_47.dll` from `Data/Platform/Distribution/RuntimeDependencies/` to the prefix game dir **and** `windows/system32/`, add `d3dcompiler_47=n,b` to `WINEDLLOVERRIDES`. Leave the launcher's CS toggle off until both copies are ~4.9 MB. See `docs/the-community-shaders-compiler-war.md` |
| Launcher: "N mod files don't match" **and** "Revision N required · you have M" at the same time | two gates. The revision number is the running launcher asar. The named esps are bytes ≠ the server pin, usually because the installed collection is the old revision | Restart the launcher once so the pending updater can install (only when the banner says the update is ready — a mid-download restart installs a partial setup). Then update the collection to that revision in the manager that already owns it. Do not install a second manager on the same Data folder. Do not Play Anyway |
| Red diamond placeholder on NPCs (esp. male hold guards), EngineFixes.log silent | case-twin mesh dirs — `1_Nordwar` vs `1_NordWar`-style pairs where Wine exact-matches one variant and the other's unique files (male meshes) are invisible; some male meshes only ever existed inside the mod archive | `python3 scripts/merge-mesh-case-twins.py --data <Data> --merge SRC DST ...` folds the pairs; `--import <7z-extract>` fills never-deployed meshes. 503 → 2 missing refs (the 2 = dead refs for uninstalled hood mod). See `docs/the-case-twin-merge.md` |
| Crash ~3 s after launch in `OpenAnimationReplacer.dll` `UIHooks::CreateD3D11`, DXVK config strings on stack, right after running mesh fixes | launching raced the merge mid-flight (files moving under a starting wineserver) — NOT the merge itself; meshes don't load at 3 s | relaunch after the merge finishes; to exonerate any data change, boot standalone: `timeout 75 umu-run skse64_loader.exe` with the launcher env (recipe in `docs/the-case-twin-merge.md` postscript) |
| Vortex red banner: "No deployment method available", fixes greyed out | Vortex can write nothing into the game dir — exfat/ntfs mount, root-owned library, read-only mount, Flatpak sandbox, or the linux-vortex AppImage drive-probe bug on non-standard mountpoints | triage tree in **Mod manager lanes** above; reason text lives in Vortex's notification bell |
| Launcher: "N required mods missing" after the manager says all deployed | manager deployed to the **Steam** Skyrim Data, not the umu prefix's copy — or Amethyst was on **VFS** deploy, which never writes Data | hardlink/symlink deploy (never VFS), then the rsync bridge. Re-run after every deploy |
| Amethyst deployed, then red diamonds / a crash a few seconds in, or `skse64_loader.exe` missing | case-alias symlinks copied into the prefix, or Amethyst renamed SKSE onto the Bethesda launcher | case-alias off, hardlink deploy, rsync `Data/` only, copy `skse64_loader.exe` back if the name is gone. See Lane D |
| Launcher: "Revision N required · you have M" | Nexus collection `ptmvzi` moved. The number you "have" is the revision baked into the running launcher asar, not Vortex. New work is the `(modId, fileId)` delta between the two collection packs | Diff the packs, download only the new pins (slow-download + nxm if not Premium), honour `choices`, Deploy, rsync, enable the new plugins. The banner clears when the launcher updater finishes and the launcher is closed. See `docs/the-collection-revision-bump.md` |
| Discord: update the launcher from the website, or the in-app update never finishes | the site installer is the announced build; a stalled `pending/temp-DaedricOnline-Setup-*.exe` (size short of `latest.yml`, not growing) will install as a partial if the window closes normally | Do not run the NSIS setup. Verify the site exe against `latest.yml`, SIGKILL by PID, delete the partial, 7z-extract `app-64.7z` over `Program Files/DaedricOnline`, relaunch. See `docs/the-launcher-website-update.md` |

## Operational safety rules (learned the hard way)

1. **Never hand-modify the game folder.** The launcher gates on a foreign-file
   list and on `SkyrimSE.exe` size 37157144. The mod manager handles the mods. The two
   sanctioned exceptions: the Step 7 console install (re-arms the exact
   vanilla 1.6.1170 files the launcher checks for), and the mod-verification
   gate (hash-verified replacement of canonically-pinned esp files — read
   `docs/the-mod-verification-gate.md` first).
2. **Never run distro wine against a umu prefix.** On a normal `/home` distro,
   always `umu-run` with the same `PROTONPATH`/env the prefix was created
   under. On Fedora Atomic the working launch is Steam's Proton via the
   non-Steam shortcut (**Fedora Atomic / Bazzite**), still GE-Proton11-7 —
   not distro wine.
3. **Never `pkill -f` a string that appears in your own command line.** Use
   chunked kill lists with explicit PIDs.
4. **Never click "INSTALL THE COLLECTION" / "GET MODS"** in the launcher — it
   overwrites the mod-manager install (Vortex or Amethyst).
5. **Never click "RESTART" while the launcher update is still downloading.**
   That installs a partial setup. When the banner says the update is **ready**,
   quit fully and start the launcher once. Do not leave the old process up
   and launch a second copy. If Discord says update from the website, or the
   pending exe has stopped short of the `latest.yml` size, do not close
   normally either — SIGKILL, delete the partial, and extract the site
   installer (`docs/the-launcher-website-update.md`).
6. **Never let the launcher "repair" or re-download vanilla data** — its own
   depot downloader corrupts LZ4 DDS blocks (`~/Downloads/daedric-dl/`); the
   "repair" re-copies the corruption. The Step 7 console install (or Steam
   Verify if the build is already correct) is the only sanctioned
   vanilla-data repair.
7. **Never launch Skyrim via its Steam library entry, never click Verify
   Integrity, after a downgrade** — both re-pull 1.7.104 and slam the version
   gate shut. The Fedora Atomic exception is a non-Steam shortcut pointed at
   `Daedric Online.exe`, not at `SkyrimSE.exe`. Playing the Skyrim app from
   Steam is still forbidden.

## File map

| Path | What it is |
|---|---|
| `~/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64` | the working Proton |
| `~/Games/umu/umu-489830` | umu prefix holding the launcher |
| `.../drive_c/Program Files/DaedricOnline/` | the launcher (launch cwd); `resources/app.asar` inside it holds the server's mod manifest — the verification gate's contract |
| `.../users/steamuser/Documents/My Games/Skyrim Special Edition/SkyrimPrefs.ini` | resolution INI |
| `.../users/steamuser/Documents/My Games/Skyrim Special Edition/SKSE/` | SKSE + plugin logs, crash logs |
| `~/.local/bin/daedric-online` | the KDE-shortcut launch script (v4) |
| `~/.local/share/Steam/ubuntu12_32/steamapps/content/app_489830/` | the 1.6.1170 console depot downloads — merge source for Step 7; keep forever |
| `~/.local/share/Steam/steamapps/appmanifest_489830.acf` | `AutoUpdateBehavior=2` — the version-hold that stops Steam re-updating |
| `docs/the-missing-texture-board.md` | the layer-3 board: staged-never-deployed rescue, mask rescue, `metalic_e` cubemap chain of custody, phase-4 mesh-side case war, phase-5 vanilla-master front (crash fix), phase-5.1 actor-tree rollback (head-build regression), sealed-gap families |
| `docs/the-option-reinstall-list.md` | installer-option mods to reinstall via Vortex + field log of the rescue rounds |
| `docs/the-collection-revision-bump.md` | "Revision N required · you have M": diff the collection packs, free-account download, FOMOD pins, rsync, and what not to delete |
| `docs/the-launcher-website-update.md` | Discord "update from the website": verify the site exe against `latest.yml`, never run the NSIS setup, SIGKILL a stalled partial, 7z-extract the app tree |
| `docs/the-atomic-steam-bridge.md` | Fedora Atomic / Bazzite: `umu-run` leaves `steam_install_path` empty when home is `/var/home`; non-Steam shortcut under GE-Proton11-7 |
| `docs/the-community-shaders-compiler-war.md` | the KW_NAMESPACE massacre: Wine's stub `d3dcompiler_47.dll` vs CS runtime shader compilation — native DLL deploy + override fix |
| `docs/the-case-twin-merge.md` | phase 6: split-case mesh dirs (`1_Nordwar`/`1_NordWar`) hide files from Wine's exact-match lookup → red diamonds; the merge tool, archive import, newer-wins conflict rule |
| `scripts/merge-mesh-case-twins.py` | merge case-twin mesh dirs + import extracted archives with CI dir resolution; dry-run default, idempotent, re-run after any sync/deploy |
| `scripts/true-missing.py`, `scripts/bsa-names.sh` | the board audit: NIF refs vs loose+BSA coverage → true-missing/risky reports |
| `scripts/deploy-staged-textures.py` | hardlink/copy deployer for staging-present textures (case-exact, idempotent) |
| `scripts/mesh-case-deploy.py` | ref-driven reverse case mirror: materializes every esp-referenced `.nif` at exact case from its lowercase twin; reports true gaps |

## Credits / war history

- GE-Proton11-6 diagnosed dead (`win32u.NtGdiCreateColorSpace`), GE-Proton11-7
  validated live.
- Launcher migrated plain-wine → umu prefix so the spawned game inherits the
  GE wineserver + Steam bridge.
- Website launcher update (2026-10-01): 1.3.60 → 1.3.79 by extracting the
  site NSIS payload after the in-app pending file stalled at 41 MB of 88 MB.
  A normal close would have installed the partial. Procedure:
  `docs/the-launcher-website-update.md`.
- `UMU_USE_STEAM=1` identified as the bridge fix after `+seh` tracing showed
  the exact S_API load failure. On Fedora Atomic that variable is not enough:
  home at `/var/home` leaves `steam_install_path` empty (field report, umu
  1.4.4, GE-Proton11-7, native Steam). Non-Steam shortcut workaround:
  `docs/the-atomic-steam-bridge.md`.
- Resolution forced to native ultrawide 2560x1080 fullscreen.
- 1.6.1170 version gate: Steam's Aug-2026 auto-update (1.7.104) broke the
  launcher's `REQUIRED_RUNTIME = "1.6.1170"` check. The launcher's own client
  sync pulls the 1.6.1170 data (the downgrade); the Steam-console depot
  install completes the pin pristinely — exe + BSAs + `AutoUpdateBehavior`
  hold (`docs/the-1.6.1170-version-gate.md`).
- Texture corruption war: the launcher's built-in downloader corrupts LZ4 DDS
  blocks in the textures BSAs; the Step 7 console-depot install heals them
  with CDN-clean data the launcher overlay never tracks (Steam Verify is the
  build-agnostic equivalent — `docs/the-texture-corruption-war.md`).
- Linux case war: once the BSAs were pristine, the remaining broken mod
  textures turned out to be case sensitivity — capitalized `Textures/`/
  `Meshes/` roots from Windows-packaged mods that Linux filesystems can't
  answer with lowercase NIF requests. Fixed with `scripts/case-normalize.sh`
  (lowercase hardlink mirrors; idempotent) plus reinstalling mods whose
  installer-option folders had been deployed raw (`docs/the-linux-case-war.md`).
- Mod verification gate: the launcher verifies tracked esp files against a
  server manifest bundled in its `app.asar` (per-file sha256 + `entry` paths
  inside a canonically-md5'd archive). A CBBE 3BA reinstall with non-default
  installer options tripped it ("2 mod files don't match the server" —
  `3BBB.esp` + `RaceMenuMorphsCBBE.esp`, fileId 600100). Fixed by extracting
  the manifest-pinned archive entries, hash-verifying, and patching `Data/`
  plus Vortex staging (`docs/the-mod-verification-gate.md`).
- Missing-texture board (layer 3): after the BSA heal + case mirror, a
  residual class stayed broken — textures that exist nowhere (no loose, no
  BSA, any case). 215 staged-but-never-deployed textures rescued from Vortex
  staging; 27 dragon-priest masks extracted from their owned source archive;
  Northern Iron's green triangles traced to one absent cubemap
  (`metalic_e.dds`) sourced extract-only from Scale Nord Armor (the Sentinel
  base mod that must not be installed alongside). Board: 128 → 127 refs.
  Tooling + full chain of custody: `scripts/true-missing.py`,
  `scripts/bsa-names.sh`, `scripts/deploy-staged-textures.py`,
  `docs/the-missing-texture-board.md`, `docs/the-option-reinstall-list.md`.
- Mesh-side case war (phase 4): textures were clean, but the worn armor still
  rendered as a placeholder — Sentinel's esps reference capital mesh roots
  (`NordWar\SonsOfSkyrim\...`) while this setup lowercases every deployed
  loose file, and loose lookups are case-EXACT. Cross-scanned the six
  Sentinel esps (1,399 `.nif` refs): 1,175 deployable hardlink twins
  materialized at exact case (`scripts/mesh-case-deploy.py`), 83 real gaps
  (vanilla-root elven/glass/ebony replacer meshes that exist in no owned
  archive). Worn Windhelm guard set (Sentinel - City Guards.esp forms
  FE00C816–C81B) now resolves end-to-end.