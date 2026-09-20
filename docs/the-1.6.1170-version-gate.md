# Root cause deep-dive: the 1.6.1170 version gate (Steam's Aug-2026 auto-update)

The launcher demands **exactly** build 1.6.1170 — it hard-checks the game exe.
Steam's Aug-2026 update shipped a new binary version, and every Skyrim SP
server on the 1.6.1170 modlist standard suddenly failed the gate. This is how
to hold the line.

## The symptom

The launcher refuses the install with a red version banner, or the check
panel shows the game version as unsupported. It is not an error — it is a
gate. The launcher's own code says so:

```js
// Program Files/DaedricOnline/resources/app.asar (unpacked: asar-out/dist/main.js)
const REQUIRED_RUNTIME = "1.6.1170";
// version-check key: "game-version"
```

## Proving it

Compare what the launcher demands against what the exe reports:

```bash
strings -el "$GAME/SkyrimSE.exe" | grep -A1 '^FileVersion$'
#   1.7.104.0          ← Steam Aug-2026 build (exe 37,910,440 B) — gate FAILS
#   1.6.1170.0         ← the build this launcher wants (exe 37,157,144 B)

md5sum "$GAME/SkyrimSE.exe"      # 1.6.1170: 7a44a52dfc92d78f934c4d12ed92f494
```

Skyrim SE shipped **1.6.1170 from Jan 2024 to Aug 2026** — the entire modlist
ecosystem (SKSE `skse64_1_6_1170.dll`, plusskymp, server builds) is pinned to
it. The Aug-2026 Creation-content update jumped the binary to 1.7.99 → 1.7.104
and the launcher gate slammed shut, even though the game still booted. SKSE
living in the game root is not enough — the launcher checks the exe itself.

## The fix: console depot downloads → merge → auto-update hold

**Step 1 — open the Steam console:**

```bash
steam steam://open/console        # or relaunch with:  steam -console
```

**Step 2 — download the three 1.6.1170 depots (one at a time, wait for each):**

```
download_depot 489830 489831 8442952117333549665
download_depot 489830 489832 8042843504692938467
download_depot 489830 489833 1914580699073641964
```

The manifest IDs pin the download to the exact 1.6.1170 build. **Without a
manifest ID you get the current/latest build** (i.e. 1.7.104 — useless).

What each depot holds (verified sizes):

| Depot | Manifest | Contents | Files / size |
|---|---|---|---|
| 489831 | `8442952117333549665` | `Data/`: CC, Animations, Meshes, Misc, Sounds, Voices, Video + `installscript.vdf` | 19 / 7.0 GB |
| 489832 | `8042843504692938467` | root dlls/inis + Textures/Interface/Shaders BSAs + ESMs | 26 / 8.0 GB |
| 489833 | `1914580699073641964` | `SkyrimSE.exe` **1.6.1170.0** (37,157,144 B) | 1 / 0.036 GB |

**Step 3 — merge the depots into the install** (the "paste into your Skyrim
folder" step Windows guides reference — on Linux the console drops them in a
separate tree, so merging is mandatory):

```bash
GAME="$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition"
C="$HOME/.local/share/Steam/ubuntu12_32/steamapps/content/app_489830"   # Linux depot landing zone

rsync -a "$C/depot_489831/Data/" "$GAME/Data/"
rsync -a "$C/depot_489831/installscript.vdf" "$GAME/"
rsync -a "$C/depot_489832/" "$GAME/"
cp -a  "$C/depot_489833/SkyrimSE.exe" "$GAME/SkyrimSE.exe"
```

This overwrites the 1.7.104 files with CDN-pristine 1.6.1170 — the merge is
the sanctioned way to touch the game folder (see the README's rule #1 nuance).

**Step 4 — hold Steam's auto-update** so it can't undo the pin:

```bash
# appmanifest_489830.acf: AutoUpdateBehavior 1 (always) → 2 (only on launch)
python3 - "$HOME/.local/share/Steam/steamapps/appmanifest_489830.acf" <<'EOF'
import sys
p = sys.argv[1]
s = open(p).read()
open(p, "w").write(s.replace('"AutoUpdateBehavior"\t\t"1"', '"AutoUpdateBehavior"\t\t"2"'))
EOF
```

**Step 5 — make the pin permanent.** After a downgrade, two actions re-pull
1.7.104 and must never happen:

- **never click Verify Integrity** in Steam (Steam Properties) — re-downloads 1.7.104
- **never launch the game via the Steam client** — Steam updates on manual
  launch; the launcher (umu path) must be the only entry point

Re-arm any time with `scripts/downgrade-1.6.1170.sh` (idempotent: re-merges
depots + re-holds the manifest + prints the resulting exe version).

## Check it yourself

```bash
bash scripts/downgrade-1.6.1170.sh

strings -el "$GAME/SkyrimSE.exe" | grep -A1 '^FileVersion$'   # → 1.6.1170.0
md5sum "$GAME/SkyrimSE.exe" "$C/depot_489833/SkyrimSE.exe"    # → identical hashes
grep AutoUpdateBehavior "$HOME/.local/share/Steam/steamapps/appmanifest_489830.acf"  # → "2"
```

If the gate is still red after this, the launcher rebuilt its check cache —
restart it cleanly (never SIGTERM; see the README's launch rules).