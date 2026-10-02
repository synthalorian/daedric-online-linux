# Fedora Atomic: `umu-run` leaves the Steam install path empty

Field report. Not reproduced on the CachyOS machine the rest of this guide
was verified on.

**Setup that hit it:** Bazzite (Fedora Atomic, KDE), native Steam, Nvidia
2080 Super, umu 1.4.4, GE-Proton11-7.

## The symptom

The launcher window opens. Skyrim never spawns. The full Step 4 environment
was already exported, including `UMU_USE_STEAM=1` and
`STEAM_COMPAT_CLIENT_INSTALL_PATH`. Every attempt logged:

```
Proton: Error: unable to use parent for game drive, path /var/home
setup_steam_files steam_install_path ""
[S_API] SteamAPI_Init(): Failed to load module 'steamclient64.dll'
```

That `steamclient64.dll` line is the same *wording* as the
`lsteamclient=d` failure in `docs/the-lsteamclient-fix.md`. It is not the
same bug. `UMU_USE_STEAM=1` was already set. Exporting it again does nothing.

## Why `/var/home` shows up

On Fedora Atomic (Bazzite, Silverblue, Kinoite, and the same ostree family)
the real home is `/var/home/<user>`. `/home` is a symlink to `/var/home`.
Proton realpaths through that symlink, then tries to turn a library path
into a game drive.

GE-Proton11-7's `proton` script only accepts that parent when the path is a
directory named `steamapps`, the parent is writable, and both are on the
same device (`get_validated_steamapps_parent`). Anything else logs:

```
Proton: Error: unable to use parent for game drive, path <whatever was passed>
```

and returns the original path. A normal umu launch often prints this with
`path /home` and still continues — the line by itself is not an abort. On
this report the path was `/var/home`, and the next line was the fatal one:
`setup_steam_files steam_install_path ""`. Proton never handed the bridge a
Steam install path, so `SteamAPI_Init` could not load `steamclient64.dll`.
The launcher (already up) had nothing to spawn into.

`setup_steam_files` is not in the GE-Proton11-7 `proton` script this repo
was written against (umu 1.4.3). The report used umu 1.4.4. Quote the log.
Do not go hunting a missing function on 11-7 and call that the fix.

Retuning the umu environment will not fill that path. This report already
had the full Step 4 env.

## What worked

Launch the **launcher exe** through the Steam client as a non-Steam game, so
Steam fills the compat paths before Proton starts.

1. GE-Proton11-7 is already in
   `~/.local/share/Steam/compatibilitytools.d/`. Restart Steam if it is not
   in the compatibility-tool list.
2. Steam → **Games → Add a Non-Steam Game to My Library** → Browse to
   `Daedric Online.exe`. That is the extracted launcher
   (`Program Files/DaedricOnline/Daedric Online.exe` inside the prefix, or
   wherever you unpacked it). Not `DaedricOnline-Setup.exe`. Not
   `SkyrimSE.exe`.
3. Right-click the shortcut → **Properties** → **Compatibility** → check
   **Force the use of a specific Steam Play compatibility tool** →
   **GE-Proton11-7**.
4. Launch options: `%command% --no-sandbox`
5. Press Play on that shortcut.

Steam's Proton then builds the steam bridge that umu could not.
Reported result: the game spawned and connected.

This replaces the `umu-run` launch (Step 4 and the Step 9 script). It does
not replace the downgrade, the mod manager, or the case fixes. Those still
apply to the Skyrim tree the launcher points at. Steam creates its own
`compatdata/` prefix for the shortcut — leave it. If the umu prefix's
`settings.json` does not come along, log in again and point the launcher at
the **Steam** Skyrim.

## What not to do

- Do not press Play on **Skyrim Special Edition** in the Steam library.
  That is app 489830. Steam will update it off 1.6.1170. The non-Steam
  shortcut is the launcher exe only.
- Do not switch to distro Wine. The Electron launcher still needs Proton.
  The working runtime is still GE-Proton11-7 — Steam is just the thing that
  starts it.
- Do not treat a lone `unable to use parent for game drive, path /home` as
  this bug. The signature is `path /var/home` plus `steam_install_path ""`
  plus a launcher that never spawns the game.

A distro whose `$HOME` is `/home/<user>` stays on Step 4.
