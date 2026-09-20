# The Missing-Texture Board — textures that exist nowhere (Layer 3)

**Symptom:** after the BSA heal (`the-texture-corruption-war.md`) and the case
mirror + option reinstall (`the-linux-case-war.md`), most broken renders were
fixed — but a residual class stayed red/green: textures that **do not exist
anywhere on disk**. Not a case mismatch, not a corrupt archive: the file is
genuinely absent from every loose path, every BSA, any case.

**How to read the render errors while in-game:**

- **red triangle + white exclamation** = missing diffuse (`_d` / base) texture
- **green triangle** = missing environment map (`_e` cubemap) the mesh demands

`EngineFixes.log` stays silent for these — they never fail at archive level.

## The board tool

`scripts/true-missing.py` merges two inputs:

1. **The loose audit** — every `.dds` path referenced by every `.nif` under
   `Data/meshes/` (walk + regex harvest; the engine prepends `Meshes\` to ARMA
   records, so this walks the resolved mesh dir directly).
2. **The BSA index** — every path inside every vanilla + mod BSA
   (`scripts/bsa-index.sh` output).

A ref is **TRUE MISSING** only when all four answers are no: no loose file at
exact case, no loose at lowercase, no BSA entry at exact case, no BSA entry at
lowercase. That class is a guaranteed error-shader render. Everything else
lands in a RISKY bucket (case-mismatch with partial BSA coverage) — engine
dependent, mostly false alarms for cubemaps that live in the vanilla BSAs.

Current board: **127 true-missing refs / 1,129 instances** (after the rescues
below). Prior to the round-3 cubemap rescue it was 128 refs / 1,235
instances; the `metalic_e` ref accounted for 106 of those.

## Phase 1 — 215 textures staged but never deployed

The first sweep found the biggest single class: **textures present in Vortex
staging and in the mod archives, but never deployed into `Data/`**. The
mod-install pipeline staged them (`staging/`) and stopped — the deploy step
never ran for these files. The game never saw them. All 215 were deployed
from the staging tree via the repo deploy tooling, byte-identical to their
archive copies. This fixed the bulk of the red triangles on characters and
armor (the original "why is my armor still broken after the BSA heal" report).

## Phase 2 — dragon-priest masks (27 textures rescued)

Board family `actors/dragon priest/`: the NPC masks. Source mod: **Dragon
Priests Retexture SE** (`05UniqueDragonPriests` installer option carries the
mask textures under `textures/actors/dragon priest/*`). The archive was
deployed raw (installer never ran — the option dirs went into `Data/`), so
the masks never reached the game path. 27 textures extracted from the archive
option dir and deployed case-exact at the game path. Board dropped past 155
refs to 128.

> If the mod is ever reinstalled via Vortex: **tick `05UniqueDragonPriests`**
> so the masks come along. See `the-option-reinstall-list.md`.

## Phase 3 — Northern Iron green triangles: the `metalic_e` cubemap

### The report

Northern Iron (and Scale / ScaleSteel / Nord_Mercenary refits) rendered with
green shader — the mesh demanded an envmap that didn't exist.

### The chain of custody (each link proven, not assumed)

1. **Which meshes demand it** — the deployed Sentinel CBBE 3BA Bodyslide
   refit meshes at capitalized `Armor_Replacer\2_NordWar\...` paths (41
   exact-case OK refs in `Sentinel.esp`; the lowercase RR namespace resolves
   separately to vanilla `quickskydark_e.dds`, which exists in the base BSA —
   so the RR packaging is self-consistent and only the 3BA refit kept the
   original NordWarUA `metalic_e` refs). Byte-level proof: the deployed
   IronLamellar meshes are md5-identical to the RR archive copies.
2. **`metalic_e` absent everywhere** — scanned 134 owned archives (any case),
   the whole Vortex staging tree, all of `Data/`, and the full BSA index:
   zero hits. The 3BA archive ships zero envmaps; the RR archive ships only
   `gold_e.dds`; RR's ScaleSteel meshes reference `steel_e.dds` (present).
3. **The New Legion dead end (checked so nobody re-downloads it)** — New
   Legion base mod (Base-30468 + Textures Medium-30468) was already owned,
   never deployed, and its texture pack ships only `steel_e.dds` — already
   deployed and working (PLAIN, nlink 3). It does **not** contain
   `metalic_e.dds`. Coverage of the missing refs: 0.
4. **The source** — Sentinel's credits name **Scale Nord Armor** (Nexus
   41118) as the origin mod for Scale/ScaleSteel/Nord_Mercenary/IronLamellar.
   Its main archive ships exactly `textures\cubemaps\metalic_e.dds`
   (1,048,784 B) plus `steel_e.dds`.

### The fix (one file, one contract)

Extracted only `Data/Textures/cubemaps/metalic_e.dds` from
`Main Archive-41118-1-0-1601840333.7z` (scale Nord Armor main, 33 MB) via
`7z e -so`, deployed case-exact at `Data/textures/cubemaps/metalic_e.dds`.
DDS magic verified (`DDS |`). No other file from that archive was deployed —
**the base mod must not be installed alongside Sentinel** (mod page: "Do not
use Sentinel alongside the mods on which it is based"). One asset, taken from
a real owned download, not aliased from another cubemap.

Board after: **128 → 127 refs; the `metalic_e` ref's 106 instances closed**
(all Northern Iron / Scale / ScaleSteel / Nord_Mercenary envmap demanders).

## Phase 4 — the mesh-side reverse case war (1,175 twins deployed)

### Symptom

`metalic_e` round closed the texture gaps, yet the player's worn armor still
rendered as a placeholder. The board was clean — every texture on the worn
set's meshes existed at both cases (`windhelmarmor.dds/_m/_n`,
`windhelmhelmet*`, `schelmet1*`, `steel_e.dds`). The failure was one layer
up: **the meshes themselves**.

### Root cause

Sentinel's esps are authored on Windows and reference mesh paths with the
original capital root — `NordWar\SonsOfSkyrim\Windhelm\WindhelmArmorHeavyM_1.nif`.
This setup's deploy pipeline lowercased every loose file
(`meshes/nordwar/sonsofskyrim/...`), and `case-normalize.sh` only mirrors in
one direction (capital → lowercase) because Windows-authored *mods* ship
capital roots while the *engine* answers lowercase refs. The Sentinel esps
are the inverse: cap refs, lowercase files. Loose lookups are case-EXACT
(eye-twin lesson) — so every cap-root mesh ref missed and the armor rendered
as a placeholder even with perfect textures.

### Scope

Cross-scanned the six Sentinel esps for every `.nif` ref (1,399 unique).
Exact-case present: **141** (the 3BA female refits that shipped capital
`Armor_Replacer\1_NordWar\ScaleSteel\...` and stayed that way). Missing
exact-case: **1,258** — of which **1,175** had byte-identical lowercase
twins (deployable) and **83** existed nowhere (vanilla-root
`Armor/Ebony|Elven|Glass|Dragonplate/...` replacer meshes the server expects
but no owned archive provides — new sealed-gap family, see below).

### The fix

`scripts/mesh-case-deploy.py` — ref-driven reverse mirror: for every esp
`.nif` ref missing at exact case with a lowercase twin, hardlink the twin to
the exact ref'd path. Purely additive, idempotent, byte-identical, zero new
content (unlike metalic_e, nothing was extracted — the files were already
deployed, just not at the case the esp demands). Depends only on the game
Data dir and the Sentinel esp filenames; no machine-specific paths.

After: **1,316 / 1,399 refs exact-case present; 0 deployable; 83 real gaps.**

The worn armor — TH_WindhelmCuirassHeavy + TH_WindhelmCloak +
TH_WindhelmHelmet/Closed/Heavy (Sentinel - City Guards.esp, forms
FE00C816–C81B via the item-use probe log) — now resolves end-to-end:
biped, 1st-person, ground, helmet, cloak and weapon meshes all exist at
exact case (verified, nlink=4 pairs).

### Note on the 83 real mesh gaps

`meshes/Armor/Ebony|Elven|Glass|Dragonplate|.../M|F/*.nif` — vanilla-root
armor replacer meshes (`BootsGND.nif`, `Helmet_1.nif`, `CuirassGlassGO.nif`
naming) referenced by Sentinel but present in no owned archive and no
staging tree. They will placeholder *if the player equips vanilla ebony /
elven / glass* — a real content gap, same sealed-gap discipline as the
texture board. Machine list survives at `TRUE_GAP_OUT` output of
`mesh-case-deploy.py`. No fabrication; needs a real source archive.

## The remaining board — sealed gaps (do not fabricate)

These families are real content gaps. They are documented and left as-is;
each needs its real source mod (or a Vortex reinstall of one already owned).
**Never hand-author a stand-in file to clear a board entry** — that's how
mods rot. If a source archive is owned, extract the real file; otherwise the
entry stays.

| Family | Refs | Instances | Source / note |
|---|---|---|---|
| Lost Ark cubemap `dynamic1pxcubemap_black.dds` | 1 | 96 | Lost Ark assets mod — the biggest single instance count on the board |
| `armor_replacer/` (nordplate shields, `1_armor_fractions` boots/gauntlets, fur stormcloak gloves) | ~39 | —| NordWarUA-era or collection-pack assets; check owned armor-replacer archives |
| `armor/` (hunterarmor deadhare/roche, knights-of-the-nine kotn set incl. reforged, orcish `Orc_Armor_Male_body_m.dds`) | ~32 | — | `Orc_Armor_Male_body_m.dds` is a known-per-mod gap; kotn set comes from a Knights of the Nine retexture |
| `architecture/` (NordicTGC Winterhold walls) | ~23 | — | The Great Cities Winterhold — reinstall via `the-option-reinstall-list.md`, then re-mirror case |
| `nordwar/` + weapons/actors misc | ~5+4 | — | Sentinel-family fallouts to re-check after option reinstalls |
| speculars: `saviik/`, `isil/`, `knighterrant/`, `ks hairdo's/`, `clothes/`, `interface/`, `01test/`, `blood/`, `amb variants/`, `_n.dds/`, `bdo cubemaps/`, `bless cubemaps/`, `weapons/` | 1 each | — | scattered single-file refs; low priority, check after reinstalls |

## Operating rules

1. **Never fabricate a missing file** — a stand-in `.dds` hides the real gap
   and rots the board. Every cleared entry must trace to a real downloaded
   archive, extract-only where the base mod must not be installed.
2. **Extract-only deploys stay extract-only** — when a board entry points
   into a mod that can't be installed wholesale (Sentinel forbids its base
   mods), take the demanded asset and nothing else. No Vortex, no esp, no
   overlapping meshes.
3. **Re-run the audit after every session of reinstalls** — `true-missing.py`
   is idempotent and cheap; the board should trend down, never up.
4. **Case-exact deploy** — the game answers lowercase NIF refs on a
   case-sensitive FS; a capitalized deploy is an invisible deploy.