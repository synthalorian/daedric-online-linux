#!/usr/bin/env python3
"""Deploy textures that exist in Vortex staging but were never deployed to Data.

Strategy: hardlink the staging file into Data at the EXACT case the meshes
reference (eye-twin lesson: loose lookups on this engine are case-EXACT).
Idempotent: skips already-present targets. Safe to re-run.

Usage:
  python3 deploy-staged-textures.py [--data PATH] [--staging PATH] [--bsa-index FILE] [--manifest FILE]

Pass 1: deploy every ref in an optional manifest (ref -> staging src) built by
        a prior audit (the 215-ref rescue).
Pass 2: global rescue — re-harvest true-missing refs (loose + BSA excluded)
        and deploy any of them found in the staging tree, lowercased lookup.

Defaults: DATA = Steam Skyrim SE Data; STAGING = ~/.config/Vortex/skyrimse/mods
"""
import argparse, json, os, re, shutil, sys

def default_data():
    return os.path.expanduser(
        "~/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data")

def default_staging():
    return os.path.expanduser("~/.config/Vortex/skyrimse/mods")

PAT = re.compile(rb'textures[\\/][A-Za-z0-9_ .\-\\/{}()!@#$%^&+=\[\]~`"\']+\.(?:dds|DDS)', re.IGNORECASE)

def do_link(src, dst, deployed, skipped, failed):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except FileExistsError:
        skipped.append(dst)
        return "exists"
    except OSError as e:
        try:
            shutil.copy2(src, dst)
        except OSError as e2:
            failed.append((dst, f"{e} / {e2}"))
            return "fail"
    deployed.append(dst)
    return "ok"

def true_missing_set(data, bsa_index=None):
    bsa, bsa_lower = set(), set()
    if bsa_index:
        with open(bsa_index) as fh:
            for line in fh:
                p = line.rstrip("\n").replace("/", "\\")
                bsa.add(p); bsa_lower.add(p.lower())
    out = set()
    for dirpath, _d, files in os.walk(os.path.join(data, "meshes")):
        for fn in files:
            if not fn.lower().endswith(".nif"):
                continue
            with open(os.path.join(dirpath, fn), "rb") as f:
                blob = f.read()
            for m in PAT.finditer(blob):
                ref = m.group(0).decode("latin-1").replace("/", "\\")
                disk = os.path.join(data, ref.replace("\\", "/"))
                if os.path.exists(disk):
                    continue
                if ref in bsa or ref.lower() in bsa_lower:
                    continue
                if os.path.exists(disk.lower()):
                    continue
                out.add(ref)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("DATA", default_data()))
    ap.add_argument("--staging", default=os.environ.get("STAGING", default_staging()))
    ap.add_argument("--bsa-index", default=None)
    ap.add_argument("--manifest", default=None)
    args = ap.parse_args()

    deployed, skipped, failed = [], [], []

    # ---- PASS 1: explicit manifest refs ----
    if args.manifest:
        with open(args.manifest) as fh:
            manifest = json.load(fh)
        print(f"PASS 1: {len(manifest)} manifest refs")
        for m in manifest:
            dst = os.path.join(args.data, m["ref"].replace("\\", os.sep))
            do_link(m["src"], dst, deployed, skipped, failed)
    else:
        print("PASS 1: no --manifest, skipped")

    # ---- PASS 2: global rescue scan ----
    idx = {}
    for mod in os.listdir(args.staging):
        mdir = os.path.join(args.staging, mod)
        if not os.path.isdir(mdir):
            continue
        for dirpath, _d, files in os.walk(mdir):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, mdir).replace(os.sep, "\\")
                idx.setdefault(rel.lower(), []).append(full)

    tm = true_missing_set(args.data, args.bsa_index)
    print(f"PASS 2: {len(tm)} true-missing refs scanned for staging rescue")
    saved_extra = 0
    for ref in sorted(tm):
        hits = idx.get(ref.lower())
        if not hits:
            continue
        dst = os.path.join(args.data, ref.replace("\\", os.sep))
        r = do_link(hits[0], dst, deployed, skipped, failed)
        if r == "ok":
            saved_extra += 1

    # ---- summary ----
    print(f"\ndeployed: {len(deployed)}")
    print(f"already present (skipped): {len(skipped)}")
    print(f"failed: {len(failed)}")
    for dst, err in failed[:20]:
        print(f"  FAIL {dst}: {err}")

if __name__ == "__main__":
    main()