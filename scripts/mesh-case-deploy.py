#!/usr/bin/env python3
"""Reverse case mirror for esp-referenced meshes (mesh-side eye-twin).

The texture board already solved "mod ships capital, engine asks lowercase"
(case-normalize.sh mirrors capital -> lowercase). This tool solves the exact
opposite: an esp authored on Windows references HIGHERCASE mesh paths
(e.g. NordWar\\SonsOfSkyrim\\Windhelm\\...nif) while this setup's deploy
pipeline lowercased every loose file. The engine's loose lookups are
case-EXACT (eye-twin lesson), so the mesh misses and the armor renders as a
placeholder even when every texture exists.

What it does: scan the given esps for every .nif path they reference, and for
each ref that is NOT present at exact case but whose lowercase twin exists on
disk, hardlink the twin to the exact ref'd path. Purely additive, idempotent,
byte-identical (hardlink), zero new content. Refs with no file at ANY case are
reported as REAL GAPS (true missing meshes - next layer's problem).

Usage:
  python3 mesh-case-deploy.py                    # default esps, default Data
  python3 mesh-case-deploy.py --data PATH --esp "Sentinel.esp" [--esp ...]
  python3 mesh-case-deploy.py --dry-run          # report only, write nothing
  TRUE_GAP_OUT=/tmp/gaps.txt python3 mesh-case-deploy.py   # machine list

Defaults: DATA = Steam Skyrim SE Data; ESPs = the six Sentinel-server esps.
"""
import argparse, os, re, sys

def default_data():
    return os.path.expanduser(
        "~/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data")

DEFAULT_ESPS = [
    "Sentinel.esp",
    "Sentinel - City Guards.esp",
    "Sentinel - Priests and Acolytes.esp",
    "Sentinel - Master Plugin.esp",
    "Sentinel Bodyslide.esp",
    "Sentinel - More Craftable Equipment.esp",
]

PAT = re.compile(rb'[A-Za-z0-9_ .\\/-]+\.nif')
MASTERS = ("skyrim.esm", "update.esm", "dawnguard.esm",
           "hearthfires.esm", "dragonborn.esm")

def harvest_refs(data, esps):
    """All unique .nif paths referenced by the esps, backslash normalized.
    Skips refs that point into the vanilla master BSAs."""
    refs = set()
    for f in esps:
        p = os.path.join(data, f)
        if not os.path.exists(p):
            continue
        with open(p, "rb") as fh:
            blob = fh.read()
        for m in PAT.finditer(blob):
            s = m.group(0).decode("latin-1").replace("\\", "/")
            low = s.lower()
            if low.startswith("meshes/") and low[7:].split("/", 1)[0] in MASTERS:
                continue
            refs.add(s)
    return refs

def full_path(ref):
    return ref if ref.lower().startswith("meshes/") else "meshes/" + ref

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("DATA", default_data()))
    ap.add_argument("--esp", action="append", default=None,
                    help="esp to scan; repeatable (default: the Sentinel set)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    esps = args.esp or DEFAULT_ESPS
    DATA = args.data
    refs = harvest_refs(DATA, esps)
    print(f"scanned {len(esps)} esps -> {len(refs)} unique mesh refs")

    deployable, gaps, present = [], [], []
    for ref in sorted(refs):
        fp = full_path(ref)
        # lowercase only the RELATIVE part — the DATA root itself is case-kept
        rel = fp.replace("/", os.sep)
        exact = os.path.join(DATA, rel)
        if os.path.exists(exact):
            present.append(fp)
        elif os.path.exists(os.path.join(DATA, rel.lower())):
            deployable.append((os.path.join(DATA, rel.lower()), exact, ref))
        else:
            gaps.append(fp)

    print(f"exact-case present : {len(present)}")
    print(f"deployable twins   : {len(deployable)}")
    print(f"REAL GAPS (nowhere): {len(gaps)}")

    if args.dry_run:
        print("\n[dry-run] would deploy:")
        for src, dst, ref in deployable[:8]:
            print(f"  {dst}")
        if len(deployable) > 8:
            print(f"  ... +{len(deployable)-8} more")
    else:
        ok, skp, fail = 0, 0, 0
        for src, dst, ref in deployable:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                os.link(src, dst)
                ok += 1
            except FileExistsError:
                skp += 1
            except OSError as e:
                fail += 1
                print(f"  FAIL {dst}: {e}")
        print(f"\ndeployed={ok} already-present={skp} failed={fail}")
        print("re-run any time: idempotent. Vortex re-deploys land lowercase;"
              " this mirror is ref-driven, so re-running re-closes any gap.")

    # machine-parseable gap list (real missing meshes, for the next rescue)
    out = os.environ.get("TRUE_GAP_OUT")
    if out and not args.dry_run:
        with open(out, "w") as fh:
            for g in gaps:
                fh.write(g + "\n")
        print(f"gap list written: {out} ({len(gaps)} paths)")

if __name__ == "__main__":
    main()