# Updating the launcher from the website

When Discord says update the launcher from the website, that does **not**
mean run `DaedricOnline-Setup.exe`. The file is an NSIS installer. Under Wine
it hangs, and "Daedric Online is running" is a stale wineserver, not a real
lock. Extract the payload. Never execute the installer.

Verified 2026-10-01. The site and the updater feed both shipped **1.3.79**.
The installed launcher was **1.3.60**. The in-app pending file had stalled at
41,156,608 of 88,556,895 bytes. A normal close would have installed that
partial.

## What to read

| Source | What it actually is |
|---|---|
| `https://daedriconline.com/download/DaedricOnline-Setup.exe` | The file the announcement means. The homepage version label is not the check. |
| `GET http://play.daedriconline.com:3000/launcher/latest.yml` | `version`, `size`, base64 `sha512`, CDN path, release notes. HTTP only. Connect by name, never a raw IP. |
| `<prefix>/drive_c/users/steamuser/AppData/Local/daedric-launcher-updater/pending/temp-DaedricOnline-Setup-*.exe` | The in-app download. Done only when its size equals `latest.yml`. Short and not growing means stalled. |
| `<prefix>/drive_c/Program Files/DaedricOnline/resources/app.asar` | The contract the running launcher enforces. `"version": "X.Y.Z"` in that file is the installed launcher. |

1.3.79 release notes, so the new panel behavior is not a surprise: mods that
ship with the client files (Immersive Armors Retexture and the same class)
no longer show as missing before those files finish downloading. Press Play.

## Verify the download

```bash
curl -fL --retry 3 -A "Mozilla/5.0" \
  -o "$HOME/Downloads/DaedricOnline-Setup.exe" \
  "https://daedriconline.com/download/DaedricOnline-Setup.exe"
curl -fsSL "http://play.daedriconline.com:3000/launcher/latest.yml"
```

A download is done only when the file's byte size equals `size:` and its
sha512, base64-encoded, equals `sha512:`. Filename is not a check.

```python
import base64, hashlib, os, sys
p = sys.argv[1]
h = hashlib.sha512()
with open(p, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
print(os.path.getsize(p))
print(base64.b64encode(h.digest()).decode())
```

On 2026-10-01 the site file and
`http://cdn.daedriconline.com/launcher/DaedricOnline-Setup-1.3.79.exe` were
the same bytes: size `88556895`, sha512
`Hh0veBZyuGKFjl5yESoAAma2GMv17eQ1KogZTzHwwMz7wzHqBlfb2Cexy8kBph6trtaFuoJMzNXHvGwKnhFgqw==`.
If they ever diverge, the announcement named the site file. Do not install a
mismatch without looking.

## Do not close a partial

If `pending/temp-DaedricOnline-Setup-*.exe` is still growing, leave the
launcher open until it matches `latest.yml`, then close so the updater can
install. If it has stopped short of that size, do not close the window and
do not SIGTERM. Electron treats a normal quit as `quitAndInstall` and will
install the partial.

SIGKILL the launcher processes by PID. `pkill -f "Daedric Online.exe"` also
kills the shell whose command line contains that string. Delete the partial
exe before the next launch, or the next quit installs it.

## Install

User data stays in `AppData/Roaming/Daedric Online` (`settings.json`,
tokens). Do not replace that tree. Replace only the app directory. Do not
copy `$PLUGINSDIR` into `Program Files/DaedricOnline` — the app tree is
`Daedric Online.exe`, `resources/`, and the Electron dlls.

```bash
PREFIX="$HOME/Games/umu/umu-489830"
DEST="$PREFIX/drive_c/Program Files/DaedricOnline"
STAGE="${XDG_CACHE_HOME:-$HOME/.cache}/daedric-launcher-setup"
rm -rf "$STAGE"
mkdir -p "$STAGE/app"
7z x -y -o"$STAGE" "$HOME/Downloads/DaedricOnline-Setup.exe" '$PLUGINSDIR/app-64.7z'
7z x -y -o"$STAGE/app" "$STAGE/\$PLUGINSDIR/app-64.7z"
# launcher must already be dead (SIGKILL, never SIGTERM)
rsync -a --delete "$STAGE/app/" "$DEST/"
rm -f "$PREFIX/drive_c/users/steamuser/AppData/Local/daedric-launcher-updater/pending/"temp-DaedricOnline-Setup-*.exe
```

Confirm the new asar contains `"version": "<the yml version>"` and no longer
contains the old one. Relaunch with `~/.local/bin/daedric-online` (the script
in `scripts/daedric-online`). It exits if the exe is already running, so the
kill has to land first.

Flatpak Steam does not change this step. The launcher lives in the umu
prefix, not in the Steam library.

## What this does not touch

A launcher swap is not a mod deploy and not a vanilla repair. Do not click
**INSTALL THE COLLECTION** / **GET MODS**. Do not let this path re-download
Skyrim data. Mesh case fixes, the 1.6.1170 pin, and Vortex staging are
unchanged.
