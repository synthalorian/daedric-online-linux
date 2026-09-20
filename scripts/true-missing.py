#!/usr/bin/env python3
"""Merge the loose-audit missing refs with the BSA index to find TRUE missing
textures: refs with no loose file at exact case, no loose at lowercase, and no
BSA entry at any case = guaranteed error-shader (red/green triangle) renders.

Also reports the risky middle: loose lower-only (case-mismatch) refs that also
lack BSA coverage, which depend on engine lookup case-sensitivity.

Usage:
  DATA=/path/to/Data python3 true-missing.py            # builds BSA index itself
  python3 true-missing.py --data PATH --bsa-index FILE  # reuse bsa-names.sh output

Default DATA: $HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data
"""
import argparse, collections, os, re, subprocess, sys

def default_data():
    return os.path.expanduser(
        "~/.local/share/Steam/steamapps/common/Skyrim Special Edition/Data")

def build_bsa_index(data):
    """Case-exact paths servable from every BSA in Data/ (grep-equivalent scan
    of raw BSA bytes; same method as bsa-names.sh, pure python)."""
    pat = re.compile(rb'textures\\[A-Za-z0-9_ .\'\-\\/{}()!@#$%^&+=\[\]~`"]+\.(?:dds|DDS)', re.IGNORECASE)
    paths = set()
    for bsa in glob_bsas(data):
        with open(bsa, "rb") as fh:
            blob = fh.read()
        for m in pat.finditer(blob):
            s = m.group(0)
            if 8 <= len(s) <= 300:
                paths.add(s.decode("latin-1").replace("/", "\\"))
    return paths

def glob_bsas(data):
    import glob
    return sorted(glob.glob(os.path.join(data, "*.bsa")))

PAT = re.compile(rb'textures[\\/][A-Za-z0-9_ .\-\\/{}()!@#$%^&+=\[\]~`"\']+\.(?:dds|DDS)', re.IGNORECASE)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get("DATA", default_data()))
    ap.add_argument("--bsa-index", default=None,
                    help="pre-built bsa-names.sh output; builds its own if absent")
    args = ap.parse_args()

    DATA = args.data
    if args.bsa_index:
        bsa = set()
        with open(args.bsa_index) as fh:
            for line in fh:
                bsa.add(line.rstrip("\n").replace("/", "\\"))
    else:
        print("building BSA index (no --bsa-index given)...", file=sys.stderr)
        bsa = build_bsa_index(DATA)
    bsa_lower = {p.lower() for p in bsa}

    missing = {}   # ref -> dict(exact_exists, lower_exists, bsa_exact, bsa_lower, fam, n)
    mesh_root = os.path.join(DATA, "meshes")
    for dirpath, _d, files in os.walk(mesh_root):
        for fn in files:
            if not fn.lower().endswith(".nif"):
                continue
            with open(os.path.join(dirpath, fn), "rb") as f:
                data = f.read()
            for m in PAT.finditer(data):
                ref = m.group(0).decode("latin-1").replace("/", "\\")
                norm = ref.lower()
                if not norm.endswith((".dds",)):
                    continue
                if ref in missing and missing[ref]["exact"]:
                    continue
                disk = os.path.join(DATA, ref.replace("\\", "/"))
                if os.path.exists(disk):
                    missing[ref] = dict(exact=True, lower=True, bsa=True, fam="?", n=0)
                    continue
                d = missing.setdefault(ref, dict(
                    exact=False, lower=None, bsa=None,
                    fam=ref.lower().split("\\")[1] if "\\" in ref else "?", n=0))
                d["n"] += 1
                if d["lower"] is None:
                    d["lower"] = os.path.exists(disk.lower())
                if d["bsa"] is None:
                    d["bsa"] = ref in bsa
                    d["bsa_lower"] = norm in bsa_lower

    true_missing = {}   # no exact loose, no lower loose, no bsa any case
    risky = {}          # loose lower-only (case mismatch) and no BSA coverage
    for ref, d in sorted(missing.items()):
        if d["exact"] or d["bsa"]:
            continue
        if not d["lower"] and not d.get("bsa_lower"):
            true_missing.setdefault(d["fam"], []).append((d["n"], ref))
        else:
            risky.setdefault(d["fam"], []).append(
                (d["n"], ref, "lower-loose" if d["lower"] and not d.get("bsa_lower") and not d["bsa"] else "bsa-lower-only"))

    print(f"== TOTAL refs missing loose-exact: {len(missing)}")
    print(f"== TRUE MISSING (guaranteed red triangles): {sum(len(v) for v in true_missing.values())} refs")
    for fam, lst in sorted(true_missing.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(lst):4d} refs  {fam}/")
        for n, r in sorted(lst)[:12]:
            print(f"      {n:3d}x {r}")
        if len(lst) > 12:
            print(f"      ... +{len(lst)-12} more")

    print(f"\n== RISKY (case-mismatch, BSA may or may not serve): {sum(len(v) for v in risky.values())} refs")
    for fam, lst in sorted(risky.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(lst):4d} refs  {fam}/")
        for n, r, why in sorted(lst)[:8]:
            print(f"      {n:3d}x {r}  [{why}]")
        if len(lst) > 8:
            print(f"      ... +{len(lst)-8} more")

    # machine-parseable: the true-missing refs, one per line, for other tools
    out = os.environ.get("TRUE_MISSING_OUT")
    if out:
        with open(out, "w") as fh:
            for fam, lst in sorted(true_missing.items()):
                for n, r in sorted(lst):
                    fh.write(f"{r}\t{n}\t{fam}\n")

if __name__ == "__main__":
    main()