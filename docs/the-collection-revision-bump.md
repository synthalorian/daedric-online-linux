# Collection revision bump — "Revision N required · you have M"

**Symptom:** the launcher shows **Mod collection is out of date**,
**Revision N required · you have M**, and an **OPEN COLLECTION** button.
Play can still light. This is not the vanilla 1.6.1170 gate and not the
"mod files don't match the server" hash gate.

The banner is the Nexus collection (`ptmvzi`). The number after "you have"
is the revision baked into the **running launcher's** `app.asar`
(`collectionRevision`), not the revision Vortex thinks it installed.
Updating Vortex does not clear the banner. The launcher's own update does,
and only after that download finishes and the launcher is closed so the
updater can install.

## What to read first

| Source | What it actually is |
|---|---|
| `GET http://play.daedriconline.com:3000/launcher/collection.json` | Summary only: `revision`, counts, sha256. No mod names. |
| `GET http://play.daedriconline.com:3000/launcher/latest.yml` | Launcher installer URL, size, sha512. |
| `POST :3000/rpc/daedricWaitUpdate` | `{change, overlayVersion, launcherVersion}` — overlay and launcher, not the collection. |
| `~/.config/Vortex/downloads/skyrimse/Daedric-Online-*-<rev>-*.7z` | The real pack. One `collection.json` inside. Diff these. |
| `<prefix>/.../DaedricOnline/resources/app.asar` | The contract the running launcher enforces. Stale until the updater installs. |

Connect by name (`play.daedriconline.com`), never a raw IP. HTTP only on
`:3000`.

## Diff the packs

Extract `collection.json` from the old revision pack and the new one.
A mod is new work when `(source.modId, source.fileId)` is in N and not in M.
Nothing else in the pack is a download target. Nexus page titles often
differ from `logicalFilename` — key off `file_id`, not the title.

Each new entry pins `md5` and `fileSize`. A download is done only when both
match. Filename is not a check.

If the entry has a `choices` object, those named radios are mandatory.
An empty `choices` array means leave that group unselected. "Only free
creations (No plugin)" means do not deploy the plugin that option would
have shipped (`CBBE 3BA Creation Club.esp` is that mistake). After install,
`7z l` the archive for every plugin the new revision's `plugins` list added.
A patch esp often lives only under `patches/plugins/<Option>/`. If staging
does not contain it, extract that one file into the staging mod, both Data
trees, and `Plugins.txt`.

## Download the missing files

Vortex's collection install is the right trigger. It logs
`no download found` for each pin that is not already in
`~/.config/Vortex/downloads/skyrimse/`.

**Premium** can take the nxm links Vortex emits. **Supporter / free cannot.**
`api.nexusmods.com/v1/games/skyrimspecialedition/mods/{modId}/files/{fileId}/download_link`
returns 403 (`isPremium` false in Vortex state). Do not fight that with the
REST API, and do not replay Firefox cookies through curl — Cloudflare eats it.

Free path, one file at a time:

1. In a browser already logged into Nexus, open
   `https://www.nexusmods.com/skyrimspecialedition/mods/{modId}?tab=files&file_id={fileId}&nmm=1`.
2. If that lands on the mod page, press **Vortex**. That opens the slow-download gate for that file id. **Manual** saves a browser download Vortex will not match.
3. Press **Slow download** on the gate that is actually showing. A background tab still exposes a Slow download control; that one is the previous file.
4. Vortex must receive `nxm://skyrimspecialedition/mods/{modId}/files/{fileId}?key=...&expires=...`.

The handler only works if the desktop file passes the URL:

```
Exec=/home/synth/.local/bin/vortex %u
```

in `~/.local/share/applications/vortex.desktop`. Without `%u`, every nxm
launch starts Vortex and drops the link. The log says `resolving download
via protocol handler` and no file appears. The wrapper already forwards
`"$@"`; `/usr/bin/vortex` adds `--download` when it is given an argument.
Run `update-desktop-database ~/.local/share/applications` after the edit.

Vortex auto-installs a finished archive into
`~/.config/Vortex/skyrimse/mods/` and deploys. A FOMOD dialog that is just
given Enter advances on whatever is already selected and can finish the
installer early. Walk the pinned choices. Do not mash Enter.

## After the archives are in

1. Let Vortex finish Deploy (log: `mods_deployed`, `added` / `removed` counts).
2. Bridge into the tree the launcher actually runs. Vortex deploys to the
   Steam library. The launcher's `gamePath` is the umu prefix.

   ```bash
   rsync -a "$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data/" \
            "$HOME/Games/umu/umu-489830/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition/Data/"
   ```

   Trailing slash on the source. No `--delete` — the prefix holds
   server-pushed files that are not in the Steam tree.
3. Enable every plugin the new revision added, in the umu
   `AppData/Local/Skyrim Special Edition/Plugins.txt`, as `*Name.esp`.
   Vortex does not always write that file when its discovery points at the
   Steam library. That is the load order the launcher's game reads.

## The banner itself

Leave the launcher open while
`drive_c/users/steamuser/AppData/Local/daedric-launcher-updater/pending/temp-DaedricOnline-Setup-*.exe`
is still growing. It is done when that file's size matches `latest.yml`.
Close the launcher after that so the updater can install. Closing early
installs a partial setup. If the pending file stops growing short of that
size — or Discord says update the launcher from the website — do not close.
SIGKILL, delete the partial, and extract the site installer
(`docs/the-launcher-website-update.md`). The new asar is what changes
"you have M" to N.

Do not click **INSTALL THE COLLECTION** / **GET MODS** in the launcher.
That path overwrites a working Vortex install.

## What is not a stray mod

Aligning to revision N means diff the collection packs. It does not mean
delete every esp that is absent from `collection.json` `plugins`.

- **`role: "overlay"` pins in the running asar** are server armour, not
  Nexus mods. `LostArk_Kamen.esp` and
  `[Kirax] Lost Ark Reborn Paladin Legendary.esp` are pinned by sha256 and
  size. Their meshes live under `meshes/LostArk` and
  `meshes/LoA Reborn Paladin Legendary`. Removing them makes other players'
  worn gear fail to resolve. A near-name twin that does **not** match the
  pin (`[Kirax] LoA Paladin Legendary.esp`, meshes under
  `meshes/loa paladin legendary`) is the stray — remove that one, not the pin.
- **Prefix-only `Daedric*.esp` written during a launcher sync**
  (`DaedricSheogorathFemaleWeight.esp`, `DaedricWardrobeCompatibility.esp`,
  `RP_*.esp`, `Daedric Landscape*.esp`) are server pushes. They are not in
  the Nexus pack and not in the Steam library. Leave them. The launcher
  will rewrite them on the next sync.
- **Vanilla masters and `cc*`** are not collection plugins. Do not touch them.

A file is removable only when it is in neither the new collection's plugin
list nor the asar's overlay/hash pins, and it is not a prefix-only file the
launcher just wrote.

## Amethyst instead of Vortex

Lane D in the README. Amethyst can revision-update `ptmvzi` (Collections →
open current → switch to the revision the banner names → update). Same
bridge after deploy: hardlink into the Steam `Data/`, `rsync -a` into the
prefix, enable new plugins in the umu `Plugins.txt`.

Not verified against this collection's FOMOD pins. If the hash gate still
names an esp after the update, that file or choice is wrong — reinstall the
pinned file, do not xEdit it. Do not install Amethyst on top of a Vortex
tree that already owns the collection. VFS deploy, case-alias symlinks, and
Amethyst's SKSE rename are all disallowed; the README lane has the rules.
