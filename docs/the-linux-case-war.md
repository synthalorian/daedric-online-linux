# The Linux Case War — mods that Windows loads and Linux can't

**Symptom:** vanilla textures are clean (BSAs verified pristine) but modded
armor and clothing are invisible or render as the engine's error shader (the
red/green triangle). `EngineFixes.log` says nothing — because nothing failed
at the archive level.

**Root cause, layer 1 — case sensitivity.**

Skyrim's NIF meshes reference loose textures with **lowercase** paths
(`textures\0cce\dress_diffuse.dds`), and its BSA lookups are
case-insensitive. But mod archives routinely ship their loose files under
**capitalized** roots (`Textures/`, `Meshes/`, `Interface/`, `Scripts/`,
`Sound/`). On Windows this is fine — the filesystem ignores case, the
capitalized file answers the lowercase request. On Linux the filesystem is
**case-sensitive**: the request walks the exact path, finds nothing, and the
material fails.

The one-way traffic is the tell:

| Tree | Files on disk (pre-fix) | What it is |
|---|---|---|
| `Data/meshes/` (lowercase) | ~14,000 | the bulk — correctly packaged mods, loads fine |
| `Data/Meshes/` (capital) | ~1,000 | capital-root minority — unreachable from lowercase NIF refs |
| `Data/textures/` (lowercase) | ~5,100 | the bulk — loads fine |
| `Data/Textures/` (capital) | ~700 | capital-root minority — unreachable |

The capital roots are the tip of it — a second wave hides **deeper inside the
lowercase trees** as mixed-case paths: `meshes/0CCE/`, `textures/actors/Character/`,
`meshes/armor/LunarGuard/`, ... Each of those subdirs is a case variant of the
path the NIFs request and is equally unreachable. The mirror sweep caught
~12,000 files in total across both waves.

Concrete case from the field: the dress mod's NIF asks for
`textures\0cce\dress_diffuse.dds`; the file exists only as
`Data/Textures/0CCE/Dress_Diffuse.dds`. Same bytes (same md5,
`371419135c...`), different case, never loaded. Result: mesh present, texture
missing, error shader.

**Root cause, layer 2 — installer-option folders deployed raw.**

A separate class of broken mods: archives that are structured as *installer
choices* (`00 Base`, `01 Complete`, `02 Human`, `00 Data/00Base`,
`0_Base Female`...) and were deployed without the installer ever running.
Vortex hardlink-deploys the archive's folder structure as-is, so the files
land at `Data/<Option>/meshes/...` instead of `Data/meshes/...`. The game
never even looks there — those mods are invisible to the engine. This is the
"invisible armor" class (whole mods: `Armory of the Dragon Cult`, `Armors of
the Velothi I/II`, `New Legion 3BA`, the CBBE 3BA option family, the Great
Cities pack, ...), not a case problem. The fix is reinstalling those mods via
Vortex and actually picking the installer options.

## The fix

### Layer 1 — `scripts/case-normalize.sh`

Mirrors every loose file under a loadable `Data/` root to its fully-lowercased
path as a hardlink (zero extra space, purely additive, idempotent):

```
Meshes/actors/foo/bar_0.nif   ->  meshes/actors/foo/bar_0.nif
Textures/0CCE/Dress.dds       ->  textures/0cce/dress.dds
```

- Collisions (a lowercase twin already exists with different content) keep the
  existing file and log a conflict — the lowercase path is the one the engine
  loads anyway, so the winner never changes.
- Only loadable roots are touched (`meshes`, `textures`, `scripts`,
  `interface`, `strings`, `sound`, `seq`, `skse`, `source`, `music`, `video`,
  `fonts`, `materials`, `shaders`) — installer-option folders, `CalienteTools`,
  `fomod` metadata and other junk are never duplicated.
- Re-run it after any Vortex deploy: idempotent, and newly deployed
  capital-cased files get picked up. Conflicts from a fresh deployment should
  be rare; when they happen the lowercase file (the one already loading) wins.

```
bash scripts/case-normalize.sh                # apply
bash scripts/case-normalize.sh --dry-run      # preview
bash scripts/case-normalize.sh --restore mirror.log   # exact revert
```

Verify with the mirrors in place — the game then finds e.g.
`Data/textures/0cce/dress_diffuse.dds` (byte-identical to the capitalized
source, md5 check optional).

### Layer 2 — reinstall the option-folder mods via Vortex

For each affected mod (the ones whose installer-choice folders sit under
`Data/` as top-level directories), reinstall it in Vortex and actually run the
installer: pick the option you want and let Vortex deploy the chosen files at
the real `Data/` paths. Typical offenders (names vary by collection):
CBBE 3BA (the whole `00 Base`/`01 Complete`/`02 Human`... family is one mod),
Armory of the Dragon Cult, Armors of the Velothi I/II, New Legion 3BA,
Flawn's Argonians + FVAR, the Great Cities pack, Capital Windhelm Expansion,
Dragon Priest Retexture SE. Tool dirs that are never loaded by the game
(`ShaderCache`, `CalienteTools`, `Logo`, `Docs`, `fomod`, installer
remnants) can be ignored.

Do it with the launcher closed: it quarantines `.esp` files it doesn't
recognize (observed: `FNIS.esp`, `DragonPriestArmorKP.esp` moved into its
`DaedricData/quarantine/`). After reinstalling, if a plugin gets quarantined,
restore it from the quarantine manifest or re-copy it from the Vortex staging
folder.

## Why the vanilla layer stays clean

All vanilla textures ship inside the `Skyrim - Textures*.bsa` archives, and
BSA lookups are case-insensitive in the engine — so the vanilla war (LZ4
corruption) and this war (case sensitivity) never overlapped. Loose vanilla
files barely exist. The case war is exclusively a *mod loose-file* problem,
which is why it surfaced only after the BSA corruption was healed.

## Operating rules

1. Run `case-normalize.sh` after any fresh Vortex deploy or mod update that
   touches loose files.
2. Never "fix" the case by renaming files inside `Data/` by hand — Vortex
   tracks its deployed paths and will fight you on the next deploy/purge. The
   script only *adds* mirrors; it never touches what Vortex manages.
3. Repairs and re-downloads of vanilla data stay banned — launcher repair and
   Steam Verify both re-pull corrupt/1.7.104 builds (see
   `the-texture-corruption-war.md` and `the-1.6.1170-version-gate.md`).
4. Reinstall option-folder mods with the launcher closed, and check its
   quarantine dir afterward.