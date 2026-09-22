# Root cause deep-dive: Community Shaders vs Wine's stub compiler

How ~3,400 shaders all died at the same line, why the obvious scapegoat
(DXVK) was innocent, and the 4.9 MB DLL that ends the war.

## The symptom

Community Shaders enabled, game boots, and `CommunityShaders.log` fills with
thousands of compile failures — every single one the same error at the same
line:

```
Failed to compile Vertex shader Sky::2:
Data/Shaders/Sky.hlsl:24:1: E5000: syntax error, unexpected KW_NAMESPACE
```

`Sky.hlsl:24`, `RunGrass.hlsl:24`, `Particle.hlsl:24` — always line 24,
always `KW_NAMESPACE`. Line 24 of the *file* is a benign `#elif`; line 24 of
the **preprocessed translation unit** is the first `namespace` declaration in
CS's shared headers, prepended to every shader before compilation.

## The actual mechanism

Community Shaders doesn't ship prebuilt binaries for its shaders — it
compiles HLSL **at runtime**, through `D3DCompile()`, which resolves to
`d3dcompiler_47.dll`.

A umu/GE prefix ships **Wine's builtin** `d3dcompiler_47.dll`:

```
-rw-r--r-- 370547  windows/system32/d3dcompiler_47.dll   # ~370 KB stub
```

Wine's builtin HLSL compiler is incomplete: it has no `namespace` keyword.
The parser hits the shared-header `namespace` and rejects every single
shader with `E5000`. DXVK never sees HLSL at all — it only translates
compiled D3D bytecode to Vulkan — so "DXVK lacks namespace support" (the
first-pass theory) was wrong. The compiler was the casualty, not the
translator.

## The fix: the native Microsoft compiler

Skyrim SE itself ships the real thing:

```
~/.local/share/Steam/steamapps/common/Skyrim Special Edition/
    Data/Platform/Distribution/RuntimeDependencies/d3dcompiler_47.dll
    # 4,891,080 bytes — the native Microsoft DLL, the exact build the game expects
```

Deploy it to **two** places in the prefix and pin the load order:

```bash
PREFIX="$HOME/Games/umu/umu-489830"
GAME="$PREFIX/drive_c/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition"
SRC="$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data/Platform/Distribution/RuntimeDependencies/d3dcompiler_47.dll"

cp -a "$SRC" "$GAME/d3dcompiler_47.dll"                  # app dir — first in DLL search order
cp -a "$SRC" "$PREFIX/drive_c/windows/system32/d3dcompiler_47.dll"   # overwrites the stub
```

Then add the native-first override to the launch env (already in
`launch-daedric.sh`):

```bash
export WINEDLLOVERRIDES="winemenubuilder.exe=d;d3dcompiler_47=n,b"
```

`n,b` = native first, builtin as fallback. The copy next to `SkyrimSE.exe`
wins via normal DLL search order even without the override; the system32
copy + override is belt-and-braces for anything that loads the compiler by
absolute path.

Enable CS in the launcher's settings
(`.../AppData/Roaming/Daedric Online/settings.json` →
`"communityShaders": true`) and relaunch.

## Verifying the kill

First boot with a working compiler is slow — CS compiles its full shader
set (~3,400 programs) and writes the disk cache. Success looks like:

```bash
grep -c "E5000" "$PREFIX/drive_c/users/steamuser/Documents/My Games/Skyrim Special Edition/SKSE/CommunityShaders.log"
# 0 on a fresh session
```

The log should show compiles completing and
`Saved disk cache info (plugin version: ...)` without the E5000 barrage.
Later boots reuse the disk cache and load fast.

## Lessons

- **`E5000: unexpected KW_NAMESPACE` = wrong compiler, not bad shaders.**
  If every shader fails at the same line of the preprocessed source, suspect
  the toolchain, not the content.
- **Wine builtin DLLs are stubs with sharp edges.** Size is the tell: a
  ~370 KB `d3dcompiler_47.dll` is Wine's; the real one is ~4.9 MB.
- **Check the game's own redist folders first.** `RuntimeDependencies/` in
  the vanilla install shipped exactly the DLL we needed — no winetricks
  download, no version roulette.
