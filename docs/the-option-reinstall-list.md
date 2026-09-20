# Option-folder mods to reinstall via Vortex (Layer 3)

These mods were deployed with their **installer-option folders intact** into `Data/`
root — the FOMOD "pick your option" step never ran, so their files sit at
`Data/<Option>/meshes/...` instead of `Data/meshes/...`. The game ignores them
entirely: this is the invisible-armor class.

## The fix
In Vortex, for each mod below: **Reinstall (or re-deploy from archive)** → the
installer runs → pick the option. Recommended picks are listed per mod where
I'm confident; body/visual presets are your call.

## The list

| Mod | Option dirs seen in Data/ | Recommended pick |
|---|---|---|
| **CBBE 3BA (Caliente's Beautiful Bodies Enhancer)** — the big family | `00 Base`, `00 Base - NeverNude/UnderWear`, `01 Complete (+ND/OD)`, `01 Curvy`, `01 ygBase`, `02 Human`, `02 Vanilla`, `03 More Packs`, `03 NeverNude Slim`, `03 Vamp Textures`, `03 UniqueCharacterBase`, `04 NeverNude Curvy`, `04 Werewolf (+Blue/Green/Red)`, `05 Dawnguard`, `06 Aesthetic Elves`, `06 Serana Black/Standard`, `06 Outfits Slim`, `07 EFM / Outfits Curvy`, `08 EFA / Outfits Vanilla`, `09 Outfits BodySlide`, `10 Physics Patch`, `11 Pubic Hair`, `12-14 Brows`, `15 Dirt to Beauty Marks / RaceMenuMorphs`, `16-25 Underwear`, `26-28 Morph Files`, `30 Vagina Texture`, `A/B/C/D/E/F` body+face option groups, `Grey Cat - *`, `Leopard - *` | **MANDATORY pins (launcher/server verification — mod 30174 file 600100):** (1) **`10 Physics Patch` → `99 Only CBPC`** — the server expects `Data/3BBB.esp` = `a1aa2b0a08a1ce77ddb56ab48483f5a9978c671cf508d771e2a2b2f78fd0244e` (3,288 B, the CBPC variant, NOT the 20,257 B main plugin); (2) **`15 RaceMenuMorphs` → `00 RaceMenuMorphs - CBBE`** — server expects `Data/RaceMenuMorphsCBBE.esp` = `1abd6b7176b16a479bd2ea8fc8844c622588083eef7fc3e810a5aa1f62014d29` (697 B). Deviating re-breaks the launcher's "2 mod files don't match the server" gate. Body/outfit options are free. (2026-09-20: both files hand-patched to canonical in Data + staging — `CBBE 3BA (3BBB)-30174-2-48-1740765899.zip` verified canonical: md5 `714f3d83...`, 346,505,352 B.) |
| **Armory of the Dragon Cult** | `Armory of the Dragon Cult/00 Data/00Base`, `01Morokei-Gold`, `02-Morokei-Blue`, `03-Nahkriin-Ebony`, `04-Nahkriin-Gold`, `05-Nahkriin-Silver`, `06-Wyrmstooth`, `07-ICH`, `08-standalone`, `10 - King Priest` | `00 Data` → `00Base` (base set). Color variants are separate armors — pick what you want. |
| **Armors of the Velothi Pt. I - 3BA** | `Armors of the Velothi Pt. I - 3BA - my mod` (CalienteTools + meshes/pulcharmsolis) | Pt. I **3BA** (you're on CBBE). |
| **Armors of the Velothi Pt. II [3BA / HIMBO]** | `Armors of the Velothi Pt. II - 3BA - my mod`, `Armors of the Velothi Pt. II [HIMBO]` | Pt. II **3BA**. |
| **New Legion 3BA** | `New Legion 3BA` | 3BA preset. |
| **Common Clothes and Armors - HIMBO** | `Common Clothes and Armors - HIMBO` | Only if you want HIMBO male-body versions; skip if not. |
| **Sentinel CBBE 3BA Bodyslide** | `Sentinel CBBE 3BA Bodyslide` | 3BA. |
| **Flawn's Argonians - Main + CBBE Patch** | `Flawn's Argonians - Main 1.0 2k compressed`, `Flawn's Argonians - CBBE Patch 1.0 2k compressed` | Main + the CBBE patch. 2k is fine. |
| **0_FVAR (Flawn's Vanilla Argonian Rework) - CBBE** | `0_FVAR_Main - CBBE` (has `0_Base/data`, `0_Base Female`, `0_Base Male`, `3_Eyes`) | Base + your sex. |
| **The Great Cities (pack)** | `The Great Cities - Minor Cities and Towns SSE`, `Resources 2k`, `The Great City Of Dawnstar`, `of Dragon Bridge`, `of Morthal`, `of Rorikstead`, `Of Winterhold` | Reinstall each; they ship `Meshes/`/`Textures/` capital — the reinstall + my case mirror makes them work. |
| **Capital Windhelm Expansion** | `CapitalWindhelmExpansionMain` | Main. |
| **COTN Morthal - Snazzy Interiors** | `COTN Morthal - Snazzy Interiors` | Main. |
| **Dragon Priest Retexture SE** | `Dragon Priest Retexture SE - Half Res` | Half Res (or full if you want). **If you reinstall, tick the `05UniqueDragonPriests` option** — it carries the NPC mask textures (`textures/actors/dragon priest/*`). See the field log below for what was already rescued. |

## Don't bother with these
- `ShaderCache` (3,431 — DXVK cache junk), `Logo`, `Docs`, `Video`, `Screenshots`, `Renderdoc`, `ModderResource` — inert, the game never reads them.
- `FOMOD` / `Fomod` / `FOMod` / `fomod` — installer remnants, harmless.
- `EngineFixes FOMOD Installer`, `powerofthree's Tweaks FOMOD Installer`, `Moons And Stars ... FOMOD Installer` — the actual plugins are working (logs confirm); these are leftovers.
- `CalienteTools`, `Nemesis_Engine`, `FNIS Behavior SE 7.6`, `Creature Meshes/Rig`, `Skeleton Meshes/Rig`, `Animations`, `Sound` — tool/engine dirs; only reinstall if a related mod needs them (Nemesis is generating animations, which is why `FNIS.esp` being quarantined was harmless).
- `100 ExteriorsOnly/Full/InteriorsOnly`, `1024/2048/512 Full`, `Torches of Quality`, `Pipe Smoking SE`, `Obsidian CS` — single-file options; if you don't know the owner mod, leave them.

## Operational warnings (from the field)
1. **Reinstall with the game closed.** Launcher closed too — it quarantines unknown `.esp`s (it already moved `FNIS.esp` + `DragonPriestArmorKP.esp` into `DaedricData/quarantine/2026-09-19T22-38-40-838Z/`).
2. **After reinstalling, launch via the daedric launcher and watch its Mods/Verify panel + the quarantine dir.** If it quarantines a reinstalled mod's plugin, flag it — restore it from the quarantine manifest or re-copy from Vortex staging.
3. Don't let the launcher "repair" vanilla; don't Verify Integrity; launcher stays the only entry point.
4. The case mirror is fully reversible (the `case-normalize.sh` run logs every link it makes) — but leave it in place; without it, capital-cased mod files stay invisible to the game.
## Field log (rescue rounds)

### Round 1 — 2026-09-19: 215 staged-but-never-deployed textures
Full loose audit found 215 textures present in Vortex staging (`~/.config/Vortex/skyrimse/mods/`)
but never deployed into `Data/` — the mod pipeline staged them and the deploy
step never ran. Deployed via `scripts/deploy-staged-textures.py` (hardlink,
case-exact), byte-identical to archive copies. This killed the bulk of the
red-triangle character/armor renders. Sentinel RR provided most of the
rescued set.

### Round 2 — 2026-09-19/20: 27 dragon-priest masks (`05UniqueDragonPriests`)
Board family `actors/dragon priest/`: the NPC masks lived inside the Dragon
Priest Retexture archive under the installer option
`05UniqueDragonPriests` — never extracted because the installer never ran.
27 mask textures extracted from the owned archive
(`Dragon Priests Retexture SE - Half Res-101101-1-1-1717159764.7z`) and
deployed case-exact to `Data/textures/actors/dragon priest/`. Board: 155 → 128 refs.

### Round 3 — 2026-09-20: Northern Iron green triangles (`metalic_e` cubemap)
Deployed IronLamellar (Northern Iron) rendered green = missing envmap.
Forensics chain: Sentinel 3BA refit meshes (capitalized
`Armor_Replacer\2_NordWar\...`) keep the original NordWarUA
`textures\cubemaps\metalic_e.dds` refs; the ref was absent from 134 owned
archives, staging, `Data/`, and every BSA. New Legion base mod = dead end
(owned, ships only `steel_e.dds`, already working). Source: **Scale Nord
Armor** (Nexus 41118) main archive — the origin mod Sentinel credits —
extract-only the single cubemap (`7z e -so`), deployed case-exact:
`Data/textures/cubemaps/metalic_e.dds`. **No other file from that archive was
installed** — the base mod must not run alongside Sentinel. Board: 128 → 127
refs; the ref's 106 instances closed. Full write-up:
`the-missing-texture-board.md`.
