# The Failing Slot Verdict — Daedric Online Skyrim SE Crash Lineage

_Master doc: every crash, every probe, every verdict. Rebuilt 2026-09-20 after
server restart wiped `/tmp/opencode` (live repo) and the Umu drive (crash logs,
probe files, game install)._

---

## TL;DR

Two separate bugs, both server-side, neither fixable from the client JS bundle:

1. **The crash** (`+0E24D66` `mov r12,[rbp+0x20]` rbp=0): another player's
   character model fails to load on the BSJobs worker thread. The engine creates
   `Marker_error` placeholder nodes for failed mesh loads, then crashes on a null
   deref when attaching a child mesh to the placeholder parent. The victims are
   **other players' characters** (Eryndor Carandil, Eats-The-Rocks,
   Slithers-fo-Nuggets, Aleister Rielle, Ka'Zaar, Ra'uul) — not NPCs, not the
   local player.

2. **The armor stripping**: the Daedric Online server removes the player's gear
   from inventory during the login sequence. Gear is added (container events
   `world->player`), then immediately removed (container events
   `player->world`). Only one item (`28010E6B`) survives and gets equipped. The
   rest sit in inventory unequipped. This is NOT the eqstart patch — it happens
   with the canonical bundle and no local patches.

---

## Crash Lineage

| Run | Time | Victim | Race | Failed Parent | Live Tri | Signature |
|-----|------|--------|------|---------------|----------|-----------|
| Armor era | 03-04 | (player) | — | `Marker_error` (IronLamellar) | — | `+0E24D66` |
| Armor era | 04-10 | (player) | — | `Marker_error` (IronLamellar) | — | `+0E24D66` |
| Armor era | 06-47 | (player) | — | `Marker_error` (IronLamellar) | — | `+0E24D66` |
| Skee64 | 03-43 | — | — | — | — | `+04316FB` |
| Skee64 | 05-01 | — | — | — | — | `+04316FB` |
| Skee64 | 05-11 | — | — | — | — | `+04316FB` |
| CS menu UAF | 14-02 | — | — | — | — | `+0CEE250` |
| libcef | Sep 19 | — | — | — | — | launcher crash |
| **NPC era** | **17:12:32** | **Eats-The-Rocks `0xFF001E5C`** | Argonian | `Cloack2M_1.nif` (missing) | `FurCollar1M_1` | `+0E24D66` |
| **NPC era** | **17:57:50** | **Slithers-fo-Nuggets `0xFF001E32`** | Argonian | `Scene Root` (tree failed) | `NPC R Finger42 [RF42]003` | `+0E24D66` |
| **NPC era** | **18:17:31** | **Eryndor Carandil `0xFF0015BE`** | Dark Elf | `Scene Root` (tree failed) | `glove001` (Silver Hand gauntlets) | `+0E24D66` |

**Correction (2026-09-20):** The "NPC era" victims are **other players'
characters**, not NPCs. Daedric Online has no NPCs (`RP_NoNatives.esp` strips
them). The `0xFF` runtime refs are multiplayer clones of other players. The
vanilla NPC names (Eats-The-Rocks, Ka'Zaar, etc.) are the base `Skyrim.esm`
form data the engine uses as templates for the character objects.

---

## The Crash Mechanism

### What happens

1. Another player's character enters the local player's cell (or is loaded from
   the server state).
2. The engine spawns a `Character*` object with a `0xFF` runtime ref.
3. The BSJobs worker thread builds the CME (Custom Model Extension) model tree
   for that character.
4. One or more mesh files referenced by the character's armor/outfit fail to
   load (missing NIF, case mismatch, or corrupted file).
5. The engine creates `Marker_error` placeholder `BSFadeNode`/`BSTriShape`
   nodes for the failed meshes.
6. A subsequent mesh attach operation tries to parent a child mesh (e.g.
   `FurCollar1M_1`, `glove001`) to the `Marker_error` placeholder.
7. The placeholder has no valid parent node (`rbp=0`).
8. `mov r12, [rbp+0x20]` → null deref → `EXCEPTION_ACCESS_VIOLATION` → crash.

### Why it's not fixable from the client JS bundle

The crash is on the **BSJobs worker thread** during **CME model-load**. The
client JS bundle (`skymp5-client.js`) runs on the **main thread** and handles
message-driven equip/inventory operations. The `__rpEqReady` gate (eqstart
hunks 4/5) guards `EquipObject`/`applyPcInv` — a completely different code path.
The JS bundle is structurally invisible to the worker-thread model-load path.

### What would fix it

1. **Engine-side (ideal):** The BSJobs worker should handle `Marker_error`
   placeholder parents gracefully — skip the attach, log a warning, continue.
   This is a SkyrimSE engine bug.

2. **Server-side:** Prevent players with broken character setups (armor
   referencing missing meshes) from joining, or sanitize their character data
   before sending to other clients.

3. **SKSE plugin (possible but expensive):** Hook the model-load attach path,
   detect `Marker_error` parents, skip the attach, log a warning. Hours of C++
   work.

4. **Data fix (whack-a-mole):** Add the missing NIF files. We did this for
   `Cloack2M_1.nif` (copied from `CloackM_1.nif`), which fixed that specific
   mesh but the crash moved to a different player's character with a different
   failure mode. The systemic problem is the engine crashing on placeholder
   parents, not any single missing mesh.

---

## The Armor Stripping

### What happens (run-14 probe timeline)

```
us=23026302  EQUIP 00012E4D  equipped=False   ← starting gear unequipped
us=23026559  CONT  00012E4D  player->world    ← removed from inventory
us=23026630  EQUIP 00012E46  equipped=False
us=23026690  CONT  00012E46  player->world
us=23026742  EQUIP 00012E49  equipped=False
us=23026797  CONT  00012E49  player->world
us=23026843  EQUIP 00012E4B  equipped=False
us=23026897  CONT  00012E4B  player->world
         ↓
us=23031722  CONT  28010E6B  world->player    ← item added
us=23032255  EQUIP 28010E6B  equipped=True     ← equipped
         ↓ 74ms ↓
us=23106377  EQUIP 28010E6B  equipped=False    ← unequipped
us=23106581  CONT  28010E6B  player->world     ← removed
         ↓
us=23109506  CONT  00013105  world->player    ← 18 items added
  ... (18 items, us=23109506-23113235) ...
         ↓ 2.3s ↓
us=23385172  CONT  00013790  player->world    ← ALL 18 items removed
  ... (18 items, us=23385172-23386173) ...
         ↓
us=23387690  CONT  28010E6B  world->player    ← re-added
us=23388166  EQUIP 28010E6B  equipped=True     ← re-equipped
         ↓ 4.8s ↓
us=28146012  CONT  00013105  world->player    ← 13 items added
  ... (13 items, us=28146012-28146882) ...
              (NEVER equipped, NEVER removed)
         ↓
us=28186329  gate-ready
```

### Key findings

- The gear is **removed from inventory** (container events `player->world`),
  not just unequipped. The player is left naked.
- Only `28010E6B` survives and gets equipped.
- The Phase 6 items (13 items) are added to inventory but **never equipped**.
- The inventory samples confirm: after the stripping, the player has only
  `00064B41x3` and `03003540x3` (consumables), no armor.
- This happens with the **canonical bundle** (`808f2564`), no eqstart patch,
  no local modifications.

### Why it's not the eqstart patch

The eqstart patch was rolled back before run-14. The bundle was canonical
`808f2564` with zero eqstart markers. The watcher was dead. And yet the armor
was still stripped. The eqstart patch was a red herring for this problem.

### What would fix it

1. **Server-side (the actual fix):** The Daedric Online server is stripping the
   player's gear during the login sequence. The server needs to stop removing
   gear from the player's inventory, or the inventory reconciliation logic needs
   to be fixed so it doesn't treat the initial equip as "wrong."

2. **Client-side (band-aid, not a fix):** The eqstart patch tried to defer the
   equip to avoid the race, but it made things worse (the deferral window caused
   the server to strip the gear entirely). The right fix is server-side.

---

## The eqstart Patch (ROLLED BACK)

### What it was

A 5-hunk patch to `skymp5-client.js` that deferred player equip operations
until after the CME/facegen rebuild completed. The idea: if the player equips
armor before the model tree is ready, the attach fails and the armor doesn't
show. The patch gated the equip behind a `__rpEqReady` flag that was set after
the facegen rebuild.

### Why it was rolled back

1. **It didn't fix the crash.** The crash is on the BSJobs worker thread during
   model-load, which is a completely different code path from the main-thread
   `EquipObject`/`applyPcInv` that the gate guards.

2. **It stripped the player's gear.** The deferral window caused the server (or
   the client's inventory reconciliation) to treat the unequipped state as
   "player doesn't want this gear" and remove it from inventory. Net result:
   naked character.

3. **The armor stripping is server-side, not client-side.** The stripping
   happens even without the eqstart patch (run-14 proved this). The eqstart
   patch was solving the wrong problem.

### Rollback state

- Bundle: canonical `808f2564` (eqstart removed, 5 server DAEDRIC patches intact)
- Watcher: dead (killed)
- `Cloack2M_1.nif`: was in place (both case variants) but the game install is
  now gone (server restart wiped it)

---

## The `Cloack2M_1.nif` Fix (Moot)

### What it was

The run-12 crash victim (Eats-The-Rocks) was wearing a Sentinel SonsOfSkyrim
Cloack that referenced `Cloack2M_1.nif` — a file that didn't exist on disk. The
`Cloack/` directory had `CloackF_1.nif`, `CloackM_1.nif`, `CloackOfficerF_1.nif`,
etc., but no `Cloack2M_1.nif`. The "2" series only existed for `FurCollar`, not
for `Cloack`.

### The fix

Created `Cloack2M_1.nif` as a copy of `CloackM_1.nif` (SHA256
`f25e4afc6403cfdc3d656de11e7f62a566dac53876f2a1e5a2e9704e0b934e2e`) in both
case variants:
- `Data/meshes/NordWar/SonsOfSkyrim/Cloack/Cloack2M_1.nif`
- `Data/meshes/nordwar/sonsofskyrim/cloack/Cloack2M_1.nif`

### Why it's moot

The game install was wiped by the server restart. The fix would need to be
re-applied after reinstallation. But more importantly, the fix was whack-a-mole
— it fixed one missing mesh but the crash moved to a different player's
character with a different failure mode (`Scene Root` as failed parent = entire
model tree failed, not just one missing NIF).

---

## The "No NPCs" Correction

### What we thought

The crash victims were "NPC clones" — runtime-spawned NPCs with `0xFF` form
IDs and vanilla NPC names.

### What's actually true

Daedric Online has **no NPCs**. `RP_NoNatives.esp` (5MB) strips all native
NPCs from the game. The crash victims are **other players' characters** on the
multiplayer server. The `0xFF` runtime refs are the multiplayer clones of other
players. The vanilla NPC names (Eats-The-Rocks, Ka'Zaar, Slithers-fo-Nuggets,
Aleister Rielle, Eryndor Carandil, Ra'uul) are the base `Skyrim.esm` form data
the engine uses as templates for the character objects.

### Why it matters

The crash is not "NPCs spawning with broken outfits." It's "other players'
character models failing to load on your client." The fix needs to be either:
- Engine-side (handle `Marker_error` parents gracefully)
- Server-side (prevent broken character setups from being sent to other clients)

Not client-side (the JS bundle can't hook the worker-thread model-load path).

---

## Current State (post server-restart)

- **Game install:** GONE (Umu prefix wiped, Steam game dir removed)
- **Crash logs:** GONE (were on the Umu drive)
- **Probe files:** GONE (were on the Umu drive)
- **Live repo** (`/tmp/opencode/daedric-online-linux`): GONE (wiped)
- **Projects copy** (`/home/synth/Projects/active/daedric-online-linux`): STALE
  (at `c28b43f`, missing all the crash analysis commits)
- **Remote** (`github.com/synthalorian/daedric-online-linux`): STALE (at
  `c28b43f`, doc was never pushed)
- **This doc:** REBUILT from conversation context

### What needs to happen

1. **Reinstall the game** (Umu prefix + Steam game files)
2. **Verify integrity** (rule out file corruption)
3. **Re-apply `Cloack2M_1.nif` fix** (if the crash recurs with that specific
   mesh)
4. **Report to Daedric Online devs** with crash logs + probe data:
   - The crash is on other players' character models (engine bug)
   - The armor stripping is server-side (inventory reconciliation bug)
5. **Consider a SKSE plugin** to hook the model-load attach path and skip
   `Marker_error` parents (if the devs don't fix it)

---

## Crash Log Locations (when game is running)

```
/home/synth/Games/umu/umu-489830/drive_c/users/steamuser/Documents/
  My Games/Skyrim Special Edition/SKSE/
    crash-YYYY-MM-DD-HH-MM-SS.log
    DaedricItemUseProbe-<timestamp>.jsonl
```

## Bundle Location

```
/home/synth/.local/share/Steam/steamapps/common/Skyrim Special Edition/
  Data/Platform/Plugins/skymp5-client.js
```

- Canonical SHA: `808f2564b04182653047e83f5205abfe5d37fed46ac9a16bbdf1fc6919ce7a59`
- Launcher restores to canonical on every Play (overlay manifest pin)
- 5 server-canonical DAEDRIC patches are in the canonical bundle:
  facesettle, loadin, eqsafe, lodslack, geardiff

## SKSE Plugins (when game is installed)

```
/home/synth/.local/share/Steam/steamapps/common/Skyrim Special Edition/
  Data/SKSE/Plugins/
    EngineFixes.dll       (bCreateArmorNodeNullPtrCrash = true, but doesn't
                           cover the Marker_error attach path)
    CrashLogger.dll       (writes the crash logs)
    DaedricItemUseProbe.dll (writes the probe JSONL)
    MpClientPlugin.dll    (the multiplayer client)
    SkyrimPlatform.dll    (the JS runtime)
    ...
```
