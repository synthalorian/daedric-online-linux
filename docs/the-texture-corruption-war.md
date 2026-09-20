# Root cause deep-dive: the texture corruption war (the launcher's own downloads)

The launcher's built-in downloader silently corrupts the vanilla textures BSAs
it pulls. Its "repair" path then **re-copies the corruption**. This is the
forensics + the fix, end to end.

## The symptom

Textures missing in-game (grey/purple), and the engine log tells the truth:

```
# .../SKSE/EngineFixes.log
[2026-09-19] 140 textures failed to load in this session
# 52 unique paths named — every one maps onto a corrupt BSA entry
```

## Proving it

Scan every `.dds` entry in every textures BSA (repo tool, zero deps):

```bash
python3 scripts/bsa-check.py "$GAME/Data/Skyrim - Textures"*.bsa
# Skyrim - Textures0.bsa: 16384 .dds: {'wrapped-dds': 15607, 'garbage': 777}
# Skyrim - Textures1.bsa: 12288 .dds: {'wrapped-dds': 12169, 'garbage': 119}
# ...9 BSAs, 1,296 garbage entries total
```

Breakdown of the 1,296 corrupt entries:

- **719** hard LZ4-decompress failures
- **577** "short" blocks (truncated frames) — **163** of those with corrupt content

The vanilla layout is: `[bstring path][4B uncompressed size prefix][LZ4 frame]`
(`frame = magic 04 22 4D 18 | FLG | BD | HC | 4B block-size | block | endmark`).
A corrupt block = wrong frame header inside an otherwise valid table — the
archive table itself was never touched.

## The actual mechanism — it's the launcher, not Steam

- The launcher's own depot downloader (`~/Downloads/daedric-dl/dl/`) produced
  the corrupt BSAs. Its `Textures0.bsa` is exactly **652,490,581 bytes** —
  byte-identical in size to the 1.6.1170 CDN depot. It downloads the *right*
  data and corrupts LZ4 blocks **in transit**. The backup it takes before
  writing (`backup-1.7.104/`) has **0 hard failures** — proving the CDN /
  saved game data is clean and the corruption enters through its downloader.
- Its **"repair" re-copies from its own corrupt `dl/`** — never let it
  re-download or "repair" vanilla data.
- The launcher's overlay manifest (`DaedricData/overlay-manifest.json`) tracks
  **zero** vanilla BSA entries. That one fact makes the fix trivial:

## The fix: Steam Verify Integrity (CDN is clean, launcher never notices)

Steam > Skyrim SE > Properties > Installed Files > **Verify integrity of
game files**. Steam re-downloads the BSAs pristine from its CDN; because the
launcher overlay tracks no vanilla BSAs, the launcher doesn't care.

Post-verify verification (all live numbers):

- **9/9** textures BSAs: **0 garbage**, every entry `wrapped-dds`
- **1,296/1,296** known-broken candidates resolve byte-clean vs the pristine
  snapshot
- 10 garbage loose stubs at engine-logged broken paths were replaced with
  clean vanilla, hash-verified (loose files win in Skyrim — the stub would
  have shadowed the healed BSA entry)

## The landmine: `daedric-dl/dl/`

After any launcher pass, re-check. The launcher will happily re-copy its
corrupt `dl/` BSAs over the clean ones. Triage is one command:

```bash
python3 scripts/bsa-check.py "$GAME/Data/Skyrim - Textures"*.bsa
# expect: every line 'wrapped-dds' counts only, zero 'garbage'
```

Garbage again? Re-verify via Steam, then re-run the downgrade hold
(`scripts/downgrade-1.6.1170.sh` — re-merges CDN-clean 1.6.1170 depots).

## Red herrings (so you don't chase ghosts)

- **783 files of identical size 5,592,580 B** (incl. `Textures/MCE/`,
  `Textures/0CCE/`) in the mod layer — **legit**: 714 unique hashes, valid
  DDS headers, zero mentions in the engine failure log. Constant file size
  across many textures is the *normal* DXT family (2048² DXT1/DXT5 packs).
- **249 literal-backslash dirs** at `Data/` root (`textures\actors\dragon` —
  one dir name containing `\`) with 4 MB decompressed DDS inside — inert junk
  (Wine normalizes `\` → `/`, so the game can never resolve into them);
  ~2.1 GB, sweep with one find.
- Loose-file overrides only *mask* corruption (the engine loads loose first)
  and the launcher's folder sync **deletes foreign loose files within
  minutes** — heals must land in the BSAs, not `Data/` root.

## Check it yourself

```bash
python3 scripts/bsa-check.py "$GAME/Data/Skyrim - Textures"*.bsa   # zero 'garbage' = clean
# and after the downgrade-doc step 4:
strings -el "$GAME/SkyrimSE.exe" | grep -A1 '^FileVersion$'          # 1.6.1170.0
```

Clean BSAs + pinned exe = the gate passes and the textures load. That's the
whole campaign.