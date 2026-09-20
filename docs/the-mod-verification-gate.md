# The Mod Verification Gate — when the launcher says files "don't match the server"

**Symptom:** the launcher blocks (or warns) with **"N mod files don't match the
server"** and names specific files plus file IDs (e.g. *"cbbe 3ba and cbb3ba
files 600100 ... RaceMenuMorphs was edited and 3BBB is a different version"*).

**What actually happened:** the launcher verifies a fixed set of mod files on
disk against a **server manifest bundled into the launcher itself** — not a
remote fetch, not a handshake. The expected bytes are local and readable.
Almost every time, the file on disk is *some* version of the right file; it's
just not the *canonical* bytes the server pins. The usual trigger: reinstalling
a mod via Vortex and picking different installer options than the server's
reference build.

This is **not** the vanilla-version gate (1.6.1170 — `the-1.6.1170-version-gate.md`)
and **not** the texture-corruption repair (`the-texture-corruption-war.md`).
Never "fix" this by letting the launcher re-download anything.

## How the gate works

The launcher bundles its manifest inside its Electron resources — in the umu
prefix that is `<launcher install>/resources/app.asar` (e.g.
`Program Files/DaedricOnline/resources/app.asar`), a single concatenated file
whose contents are plain text and directly greppable:

1. **Required mod list** — `modId`, `name`, `files[]` with `fileId`, `version`,
   `sizeBytes`, `optional`, plus a `detect` file list (e.g. mod
   `30174` "CBBE 3BA (3BBB)" → file `600100` → version `2.48`, detect
   `3BBB.esp`).
2. **Canonical archive check** — each file entry has `archiveMd5`,
   `archiveSize` and `archiveName` (e.g. the zip must be md5
   `714f3d83b296c66b9f0a64c7089b3666`, 346,505,352 bytes).
3. **Per-file hash map** — the real enforcement: for each tracked esp,
   `"<name>.esp": { "sha256": "...", "size": N, "role": "collection",
   "modId": ..., "fileId": ..., "entry": "<path inside the canonical archive>" }`.
   `entry` is the **exact installer-option path** inside the mod archive whose
   bytes are canonical.

The gate compares the local esp against that `sha256`. Mismatch → the file is
reported (UI wording variants: "was edited", "is a different version").
Everything outside the hash map is not checked — body meshes, textures, BSAs,
scripts are all unverified; the esp files are the contract.

## Diagnosing (read the contract before touching disks)

```
grep -abo "600100" app.asar            # offsets of a known fileId
dd if=app.asar bs=1 skip=<off-600> count=2600 | tr -d '\0' | strings -n 3
```

Walk the hits until you find the `files:` map with `sha256`/`size`/`entry`
for the flagged file. That gives you everything: the expected hash, size, and
the archive path to extract from.

## The fix (worked example: CBBE 3BA, fileId 600100)

Case from the field — after a Vortex reinstall of CBBE 3BA (2.48) with
non-default options, the gate flagged exactly two files:

| File | Server canonical (from the asar manifest) | Local (broken) |
|---|---|---|
| `Data/3BBB.esp` | sha256 `a1aa2b0a08a1ce77ddb56ab48483f5a9978c671cf508d771e2a2b2f78fd0244e` — 3,288 B — `entry: "10 Physics Patch/99 Only CBPC/3BBB.esp"` | 20,257 B main plugin (wrong installer variant) |
| `Data/RaceMenuMorphsCBBE.esp` | sha256 `1abd6b7176b16a479bd2ea8fc8844c622588083eef7fc3e810a5aa1f62014d29` — 697 B — `entry: "15 RaceMenuMorphs/00 RaceMenuMorphs - CBBE/RaceMenuMorphsCBBE.esp"` | 697 B but different bytes (a different provider's copy won the conflict) |

Procedure — **never guess, never hand-edit bytes without hash proof**:

1. **Confirm the local archive is canonical.** The mod archive in your
   mod-manager downloads should match the manifest's `archiveMd5` +
   `archiveSize`. If it does, every canonical byte you need is inside it. If it
   doesn't, get the canonical archive — nothing derived from a wrong archive
   will ever match.
2. **Extract the pinned entries** from the canonical archive exactly as the
   manifest's `entry` paths name them:
   ```
   unzip -o -j 'CBBE 3BA (3BBB)-30174-2-48-1740765899.zip' \
     '10 Physics Patch/99 Only CBPC/3BBB.esp' -d ./fix/
   unzip -o -j 'CBBE 3BA (3BBB)-30174-2-48-1740765899.zip' \
     '15 RaceMenuMorphs/00 RaceMenuMorphs - CBBE/RaceMenuMorphsCBBE.esp' -d ./fix/
   ```
3. **Hash-verify before anything touches the game folder.** The extracted
   bytes must equal the manifest sha256 *and* size — both. No match = stop and
   re-read the manifest; you extracted from the wrong entry.
4. **Back up the current files**, then replace the tracked files in `Data/`.
5. **Sync the Vortex staging copies too** — the mod folders under
   `<Vortex>/skyrimse/mods/<mod>/`. The deployed file is usually a hardlink to
   staging; if only `Data/` is patched, the next Vortex deploy/purge cycle
   restores the wrong bytes and the gate re-breaks. Patching staging makes the
   current state deploy-stable.
   - `3BBB.esp` → CBBE 3BA staging.
   - `RaceMenuMorphsCBBE.esp` → **whosever staging currently wins the conflict**
     at that path (in the field case it was a different mod — Caliente's CBBE —
     that had overwritten CBBE 3BA's file). Hash the staged file; whichever
     provider's hash equals the broken `Data/` file, patch that one.
6. **Re-verify all four copies** (Data + every patched staging file) carry the
   canonical hash. Then launch.

## Keeping it fixed

- If you reinstall a verified mod, the manifest pins are **mandatory installer
  options**, not suggestions. For CBBE 3BA 2.48 (mod 30174 / file 600100):
  - `10 Physics Patch` → **`99 Only CBPC`** (this is what makes `3BBB.esp`
    the 3,288 B canonical variant)
  - `15 RaceMenuMorphs` → **`00 RaceMenuMorphs - CBBE`**
  - all body/outfit options are free — only those two pins matter to the gate.
- If two mods both ship a tracked esp, Vortex's conflict resolution picks one
  provider — the gate wants the **specific** provider's bytes the manifest
  names (identified by `entry`). Check who wins the conflict before blaming
  corruption.
- Never "repair" this via the launcher, and never hand-edit without the
  hash-verify loop above — a subtle byte difference buys you a silent gate
  failure an hour later.
- The manifest is pinned to a launcher version. If the launcher updates, re-read
  the asar: fileIds, hashes, and entries can change.

## Operating rules

1. The full verification contract lives in the launcher's own asar — the
   gate is decodable offline, no server round-trip needed.
2. `detect` files gate the required-mod list; the per-file `sha256` map gates
   the esp bytes. They are different checks — a mod can pass "detected" and
   still fail the hash gate.
3. The archive-level `archiveMd5` is your guarantee that the extraction source
   is right. Verify it once per incident.
4. Backups are cheap; the manifest is not. Keep both copies of the pre-patch
   files until the launcher has passed the gate once.