#!/usr/bin/env python3
"""Scan Skyrim SE (v0x69) BSAs: verify every .dds entry actually contains DDS data.

Header layout (36 bytes, per TES5Edit/UESP for SSE):
  0x00 magic "BSA\0"
  0x04 version        (0x69)
  0x08 FoldersOffset
  0x0C Flags
  0x10 FolderCount
  0x14 FileCount
  0x18 FolderNamesLength
  0x1C FileNamesLength
  0x20 FileFlags (ushort + padding)
Folder record (SSE): hash(8) count(4) unk(4) offset(4) unk(4) = 24 bytes
Then per folder: bzstring name, then count x 16-byte file records
(hash(8) size(4) offset(4); size bit30 = stored-compressed flag, archive flag 0x4
inverts that so most vanilla entries are raw when archive is "compressed").
Then the file name block (FileCount x NUL-terminated names) right after the
last file record. Vanilla SSE archives may also embed a bstring name at the
start of each data block (flag 0x100) and wrap data in a "CFX" frame.
"""
import os, struct, sys, glob, zlib

F_COMPRESSED      = 0x4
F_EMBEDDED_NAMES  = 0x100
F_SIZE_COMPRESS   = 0x40000000

def parse(path):
    with open(path, "rb") as f:
        hdr = f.read(36)
        if hdr[:4] != b"BSA\x00":
            return None, f"{os.path.basename(path)}: not BSA (magic {hdr[:4]!r})"
        version, folders_off, flags, folder_count, file_count = struct.unpack_from("<IIIII", hdr, 4)
        folder_names_len, file_names_len, file_flags = struct.unpack_from("<III", hdr, 20)
        if version != 0x69:
            return None, f"{os.path.basename(path)}: unsupported version 0x{version:x}"
        f.seek(folders_off)
        folders = []
        for _ in range(folder_count):
            rec = f.read(24)
            name_hash, fc, unk, off, unk2 = struct.unpack_from("<QIIII", rec)
            folders.append(fc)
        # names + interleaved file records
        f.seek(folders_off + folder_count * 24)
        entries = []
        for fc in folders:
            ln = f.read(1)[0]
            fname_raw = f.read(ln - 1) if ln > 1 else b""
            if ln:
                f.read(1)  # NUL
            folder = fname_raw.decode("utf-8", "replace")
            for _ in range(fc):
                rec = f.read(16)
                name_hash, sizefl, off = struct.unpack_from("<QII", rec)
                entries.append((folder, sizefl & 0x3FFFFFFF, off, sizefl))
        names_pos = f.tell()
        f.seek(names_pos)
        names = []
        for _ in range(file_count):
            nm = b""
            while True:
                c = f.read(1)
                if not c or c == b"\x00":
                    break
                nm += c
            names.append(nm.decode("utf-8", "replace"))
        if len(names) != len(entries):
            return None, f"{os.path.basename(path)}: name count mismatch {len(names)} vs {len(entries)} (names_pos={names_pos})"
        return (path, flags, entries, names), None

def payload_at(f, off, flags, sizefl, max_scan=256):
    """Return (kind, info) for the data block at off.
    kind: raw-dds | wrapped-dds | garbage | zero
    """
    pos = off
    if flags & F_EMBEDDED_NAMES:
        try:
            f.seek(pos)
            L = f.read(1)[0]
            pos = off + 1 + L
        except Exception:
            return "garbage", "no-name"
    try:
        f.seek(pos)
        head = f.read(max_scan)
    except Exception as e:
        return "garbage", f"seek err {e}"
    if head[:4] == b"DDS ":
        return "raw-dds", None
    idx = head.find(b"DDS ")
    if idx >= 0:
        head2 = f.read(8) if False else head
        return "wrapped-dds", f"frame={head[:idx].hex()}"
    comp = bool(flags & F_COMPRESSED) != bool(sizefl & F_SIZE_COMPRESS)
    if comp:
        try:
            f.seek(pos)
            zlen = struct.unpack("<I", f.read(4))[0]
            data = zlib.decompress(f.read(zlen))
            if data[:4] == b"DDS ":
                return "wrapped-dds", "zlib"
            return "garbage", f"zlib->{data[:8]!r}"
        except Exception as e:
            return "garbage", f"zlib err {e}"
    return "garbage", head[:16].hex()

def main():
    targets = sys.argv[1:] or sorted(glob.glob("Skyrim - *.bsa"))
    for path in targets:
        res, err = parse(path)
        if err:
            print(err)
            continue
        path, flags, entries, names = res
        kinds = {}
        with open(path, "rb") as f:
            for (folder, size, off, sizefl), nm in zip(entries, names):
                if not nm.lower().endswith(".dds"):
                    continue
                kind, info = payload_at(f, off, flags, sizefl)
                kinds.setdefault(kind, []).append((folder + "\\" + nm, size, info))
        from collections import Counter
        cnt = Counter(k for k in kinds)
        print(f"{os.path.basename(path)}: {sum(len(v) for v in kinds.values())} .dds: {dict(cnt)}")
        for full, size, info in kinds.get("garbage", [])[:8]:
            print(f"    BAD {full} size={size} {info}")

if __name__ == "__main__":
    main()