# Root cause deep-dive: the `lsteamclient=d` bridge kill

This documents the single most important fix in this whole guide, traced end
to end from a silent game death to one environment variable.

## The symptom

Through the launcher (or launching the game directly under GE via umu), the
game died silently:

1. `skse64_loader.log` reaches the end cleanly:
   ```
   hook thread complete
   launching
   ```
2. No process survives. No crash log is written. `skse64.log` stays 0 bytes.
   `skyrim-platform.log`, `EngineFixes.log`, `CommunityShaders.log` all keep
   their previous mtimes — the game died **before SKSE plugins initialized**.
3. No wine abort message appears in the umu log (radv warnings only).

That's the profile of an **early self-exit**, not a crash: SteamAPI_Init
failed and Skyrim exited rather than run without Steam.

## Proving it

With `WINEDEBUG=+seh` the truth surfaces in the wine seh trace:

```
015c:warn:seh:dispatch_exception "[S_API] SteamAPI_Init(): Failed to load module 'C:\\Program Files (x86)\\Steam\\steamclient64.dll'\n"
```

`S_API` messages only print under `+seh` (or `+steam`) — that's why earlier
diagnosis windows looked "clean". The bridge DLL *exists* in the prefix
(symlink to the real Steam client's), so "Failed to load module" means the
**LoadLibrary call itself failed**: the raw Windows `steamclient64.dll` has
imports the prefix can't satisfy.

## The actual mechanism

GE-Proton's `proton` script decides how to launch:

```python
umu_without_steam = "UMU_ID" in os.environ and os.environ.get("UMU_USE_STEAM") != "1"
if umu_without_steam:
    append_to_env_str(self.env, "WINEDLLOVERRIDES", "lsteamclient=d", ";")
```

`WINEDLLOVERRIDES=lsteamclient=d` — and in wine override syntax **`d` means
DISABLE** (GE's own override table documents it: `"winebth.sys": "d",
#disable winebth.sys as it crashes winedevice.exe`).

With `lsteamclient.dll` (wine's Steam API bridge) disabled, the game's
`SteamAPI_Init()` can't resolve through it and falls back to loading the real
Windows `steamclient64.dll` straight from the prefix's
`C:\Program Files (x86)\Steam\` — a 26 MB PE whose import table includes:

```
DLL Name: tier0_s64.dll
DLL Name: vstdlib_s64.dll
```

Neither exists in the prefix (they ship with the Windows Steam client, not
with Linux Steam), so `LoadLibrary` fails, `SteamAPI_Init` fails, and the
game exits silently. Notably `version.dll` is also symlinked into the prefix
by GE at launch — part of the same bridge wiring, and it works fine once
lsteamclient is allowed to live.

## The fix: `UMU_USE_STEAM=1`

Exporting `UMU_USE_STEAM=1` flips the condition:

- `umu_without_steam` becomes False → **no `lsteamclient=d` override**.
- GE routes the launch through its **builtin `steam.exe` shim**
  (`c:\windows\system32\steam.exe`, launched via wine-preloader/wine), which
  brokers SteamAPI against the running Linux Steam client.

The verdict flips to success:

```
[S_API] SteamAPI_Init(): Loaded 'C:\Program Files (x86)\Steam\steamclient64.dll' OK.
```

and the game boots: SKSE 2.2.6 initializes, scans the plugin directory
(ActorLimitFix, AnimationQueueFix, cbp, CommunityShaders, CraftingCategories,
CrashLogger, ...), `skyrim-platform` registers its browser API
(`registering browser api` / `JsEngine::RunScript()`), and the main menu
appears — with the whole 115-mod Vortex stack loading.

## Why plain wine "worked" but GE didn't

- The original plain-wine prefix ran the launcher fine — system wine is 11.17
  and has every export the Electron/CEF layer needs.
- But the game *spawned from that launcher* hit the same Steam bridge wall;
  the plain-wine path never integrated with the Steam runtime.
- The migrated umu prefix puts launcher + game on one wineserver under one
  GE Proton with the Steam bridge variables — the only configuration where
  the full chain holds. Take the bridge away (the `lsteamclient=d` kill) and
  the game dies exactly as before.

## Check it yourself

```bash
# in the launcher's umu prefix Program Files/DaedricOnline:
export GAMEID=umu-489830 UMU_ID=umu-489830 UMU_USE_STEAM=1
export PROTONPATH=$HOME/.local/share/Steam/compatibilitytools.d/GE-Proton11-7-x86_64
export STEAM_COMPAT_CLIENT_INSTALL_PATH=$HOME/.local/share/Steam
export SteamAppId=489830 SteamGameId=489830
export WINEDEBUG=+seh
umu-run "Daedric Online.exe" --no-sandbox
```

The seam between "launcher fine" and "game dead" is exactly this env var.
**The shield holds.** ⚫🦞