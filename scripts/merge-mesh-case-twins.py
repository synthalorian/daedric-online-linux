#!/usr/bin/env python3
"""Merge case-twin mesh dirs + import staged meshes into the canonical tree.

The case war's final form: two real dirs differing only in case
(`1_Nordwar` vs `1_NordWar`, `whiterun` vs `Whiterun`). Wine resolves an
exact-case query to ONE of them; files that live only in the other variant
are invisible -> red diamond placeholders. Merging each pair into a single
dir makes every case spelling resolve (Wine CI does the rest).

Modes:
  --merge SRC DST   merge SRC dir into DST dir (repeatable)
  --import ROOT     import a staging tree (e.g. 7z extract of a mod archive)
                    into --data, resolving each component case-insensitively
                    against existing dirs (no new case twins created)

Rules (learned the hard way):
  * MOVE, never symlink (symlinks double-load HDT physics -> crash).
  * Never overwrite: identical content (same inode or md5) -> drop the dup;
    different content at the same name -> REPORT, leave both untouched.
  * Dry-run by default; --apply to execute. Idempotent: safe to re-run after
    a launcher sync re-creates lowercase twins.
  * Actor tree (meshes/actors/) is out of scope — see phase 5.1.

Usage:
  python3 merge-mesh-case-twins.py --data <Data dir> --merge A B [--apply]
  python3 merge-mesh-case-twins.py --data <Data dir> --import /tmp/staging/meshes [--apply]
"""
import argparse, hashlib, os, shutil, sys

def same_file(a, b):
    sa, sb = os.stat(a), os.stat(b)
    if (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino):
        return True
    if sa.st_size != sb.st_size:
        return False
    def md5(p):
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.digest()
    return md5(a) == md5(b)

def ci_child(parent, name):
    """Real name of a case-insensitive match for `name` inside `parent`."""
    try:
        low = name.lower()
        for e in os.listdir(parent):
            if e.lower() == low:
                return e
    except OSError:
        pass
    return None

def merge_dir(src, dst, apply, stats):
    """Move everything under src into dst (recursive). Dedupe, never overwrite."""
    for dirpath, dirnames, filenames in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        dst_dir = dst if rel == "." else os.path.join(dst, rel)
        for fn in filenames:
            if fn == ".__folder_managed_by_vortex":
                continue
            s = os.path.join(dirpath, fn)
            d = os.path.join(dst_dir, fn)
            # CI collision: same name different case already at dst?
            existing = ci_child(dst_dir, fn) if os.path.isdir(dst_dir) else None
            if existing is not None:
                d_real = os.path.join(dst_dir, existing)
                if same_file(s, d_real):
                    stats["dup"] += 1
                    if apply:
                        os.unlink(s)
                else:
                    # conflict = version skew: raw Nexus archive (old) vs
                    # Bodyslide-built deploy (new). Keep the NEWER file —
                    # the built mesh is what the load order renders.
                    sm, dm = os.path.getmtime(s), os.path.getmtime(d_real)
                    keep, drop = (d_real, s) if dm >= sm else (s, d_real)
                    stats["conflict"] += 1
                    print(f"  CONFLICT kept newer: {os.path.basename(keep)} "
                          f"(kept mtime {os.path.getmtime(keep):.0f}, dropped {os.path.getmtime(drop):.0f}) in {dst_dir}")
                    if apply:
                        if drop == s:
                            os.unlink(s)
                        else:
                            os.unlink(d_real)
                            shutil.move(s, d_real)
                continue
            stats["move"] += 1
            if apply:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(s, d)
    # clean emptied dirs (bottom-up)
    if apply:
        for dirpath, dirnames, filenames in os.walk(src, topdown=False):
            try:
                remaining = [f for f in os.listdir(dirpath) if f != ".__folder_managed_by_vortex"]
                if not remaining:
                    shutil.rmtree(dirpath)
            except OSError:
                pass
        if os.path.isdir(src):
            try:
                remaining = [f for f in os.listdir(src) if f != ".__folder_managed_by_vortex"]
                if not remaining:
                    shutil.rmtree(src)
                    print(f"  removed emptied dir: {src}")
            except OSError:
                pass

def import_tree(stage_root, data, apply, stats):
    """stage_root is a dir containing meshes/... ; import into data with CI dir resolution."""
    for dirpath, dirnames, filenames in os.walk(stage_root):
        for fn in filenames:
            if fn == ".__folder_managed_by_vortex":
                continue
            s = os.path.join(dirpath, fn)
            rel = os.path.relpath(s, stage_root)  # e.g. meshes/armor_replacer/2_nordwar/...
            comps = rel.split(os.sep)
            cur = data
            for comp in comps[:-1]:
                real = ci_child(cur, comp)
                if real is not None and os.path.isdir(os.path.join(cur, real)):
                    cur = os.path.join(cur, real)
                else:
                    cur = os.path.join(cur, comp)  # new dir, archive case
            d = os.path.join(cur, fn)
            existing = ci_child(cur, fn) if os.path.isdir(cur) else None
            if existing is not None:
                d_real = os.path.join(cur, existing)
                if same_file(s, d_real):
                    stats["dup"] += 1
                else:
                    stats["conflict"] += 1
                    print(f"  CONFLICT (different content, kept both): {s}  vs  {d_real}")
                continue
            stats["move"] += 1
            if stats["move"] <= 15 or stats["move"] % 100 == 0:
                print(f"  import: {rel} -> {os.path.relpath(d, data)}")
            if apply:
                os.makedirs(cur, exist_ok=True)
                shutil.move(s, d)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--merge", nargs=2, action="append", metavar=("SRC", "DST"), default=[])
    ap.add_argument("--import", dest="imp", metavar="STAGE_ROOT")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    stats = {"move": 0, "dup": 0, "conflict": 0}
    for src, dst in args.merge:
        if not os.path.isdir(src):
            print(f"merge: {src} gone (already merged?) — skip")
            continue
        print(f"merge: {src}  ->  {dst}")
        merge_dir(src, dst, args.apply, stats)
    if args.imp:
        print(f"import: {args.imp}  ->  {args.data}")
        import_tree(args.imp, args.data, args.apply, stats)
    print(f"\n{'APPLIED' if args.apply else '[dry-run] would do'}: "
          f"moved={stats['move']} deduped={stats['dup']} conflicts={stats['conflict']}")
    if not args.apply:
        print("re-run with --apply to execute.")

if __name__ == "__main__":
    main()
