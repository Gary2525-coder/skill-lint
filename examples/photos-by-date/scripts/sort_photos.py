#!/usr/bin/env python3
"""Sort photos into YYYY/MM folders by EXIF capture date. Stdlib only."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import struct
import sys
from pathlib import Path

EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff"}
TAG_EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 0x9003
TAG_DATETIME = 0x0132


class Reader:
    def __init__(self, data: bytes, base: int, big: bool):
        self.data, self.base, self.big = data, base, big

    def u16(self, off: int) -> int:
        return struct.unpack_from(">H" if self.big else "<H", self.data, self.base + off)[0]

    def u32(self, off: int) -> int:
        return struct.unpack_from(">I" if self.big else "<I", self.data, self.base + off)[0]

    def ifd(self, off: int, depth: int = 0) -> dict:
        if depth > 3 or off <= 0 or self.base + off + 2 > len(self.data):
            return {}
        count = self.u16(off)
        out: dict = {}
        for i in range(count):
            entry = off + 2 + i * 12
            if self.base + entry + 12 > len(self.data):
                break
            tag = self.u16(entry)
            typ = self.u16(entry + 2)
            cnt = self.u32(entry + 4)
            if typ == 2 and cnt <= 4:                 # inline ASCII
                raw = self.data[self.base + entry + 8: self.base + entry + 8 + cnt]
                out[tag] = raw.split(b"\x00")[0].decode("ascii", "ignore")
            elif typ == 2:                            # offset ASCII
                ptr = self.u32(entry + 8)
                start = self.base + ptr
                out[tag] = self.data[start: start + cnt].split(b"\x00")[0].decode("ascii", "ignore")
            elif typ == 4 and cnt == 1:
                out[tag] = self.u32(entry + 8)
            if tag == TAG_EXIF_IFD and typ in (4, 13):
                ptr = out.get(tag) or self.u32(entry + 8)
                out.update(self.ifd(ptr, depth + 1))
        return out


def exif_datetime(path: Path) -> dt.datetime | None:
    try:
        with path.open("rb") as fh:
            data = fh.read(256 * 1024)
    except OSError:
        return None
    if data[:2] != b"\xff\xd8":
        return None
    idx = 2
    while idx + 4 < len(data):
        if data[idx] != 0xFF:
            break
        marker = data[idx + 1]
        seg_len = struct.unpack_from(">H", data, idx + 2)[0]
        if marker == 0xE1 and data[idx + 4: idx + 10] == b"Exif\x00\x00":
            tiff = idx + 10
            order = data[tiff: tiff + 2]
            if order not in (b"II", b"MM"):
                return None
            big = order == b"MM"
            reader = Reader(data, tiff, big)
            tags = reader.ifd(reader.u32(4))
            raw = tags.get(TAG_DATETIME_ORIGINAL) or tags.get(TAG_DATETIME)
            if isinstance(raw, str):
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return dt.datetime.strptime(raw.strip(), fmt)
                    except ValueError:
                        continue
            return None
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            idx += 2
        else:
            idx += 2 + seg_len
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sort photos into YYYY/MM by EXIF date.")
    ap.add_argument("directory")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, move nothing")
    ap.add_argument("--recursive", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.directory).expanduser().resolve()
    if not root.is_dir():
        print(f"sort_photos: not a directory: {root}", file=sys.stderr)
        return 2

    walker = root.rglob("*") if args.recursive else root.glob("*")
    files = [p for p in walker if p.is_file() and p.suffix.lower() in EXTS]

    moved = 0
    skipped: list[Path] = []
    plan: dict[Path, Path] = {}

    for src in files:
        when = exif_datetime(src)
        if when is None:
            mtime = src.stat().st_mtime
            when = dt.datetime.fromtimestamp(mtime)
            if mtime <= 0:
                skipped.append(src)
                continue
        dest_dir = root / f"{when:%Y}" / f"{when:%m}"
        dest = dest_dir / src.name
        if dest == src:
            continue
        n = 1
        while dest.exists():
            dest = dest_dir / f"{src.stem}_{n}{src.suffix}"
            n += 1
        plan[src] = dest

    for src, dest in plan.items():
        if args.dry_run:
            print(f"{src.relative_to(root)}  ->  {dest.relative_to(root)}")
            moved += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved += 1

    verb = "Would move" if args.dry_run else "Moved"
    dirs = len({d.parent for d in plan.values()})
    print(f"{verb} {moved} files into {dirs} folders.")
    if skipped:
        print(f"Skipped {len(skipped)} files: no EXIF and no readable mtime.")
        for p in skipped[:10]:
            print(f"  {p.relative_to(root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
