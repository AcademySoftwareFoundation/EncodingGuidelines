#!/usr/bin/env python3
"""Remove the eXIf chunk from PNG files, leaving the pixels and every other chunk unchanged.

OpenImageIO 2.4 wrote big-endian EXIF with a byte-swapped TIFF header (MM*\\0 instead of MM\\0*). From FFmpeg 8.1
the PNG decoder fails the whole frame when the EXIF does not parse (see FFmpegChanges.md, "PNGs with bad EXIF
data"), so images written that way cannot be decoded.

    strip_png_exif.py [--all] <png or folder> ...

Folders are searched recursively. By default only chunks with the bad header are removed; --all removes any eXIf.
"""
import argparse
import struct
import sys
from pathlib import Path

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
BAD_HEADER = b'MM*\x00'


def strip_exif(path, remove_all=False):
    """Rewrite path without its eXIf chunk. Returns True if the file was changed."""
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        return False
    out = [PNG_SIGNATURE]
    pos = len(PNG_SIGNATURE)
    changed = False
    while pos + 8 <= len(data):
        length, chunk_type = struct.unpack('>I4s', data[pos:pos + 8])
        end = pos + 12 + length
        if chunk_type == b'eXIf' and (remove_all or data[pos + 8:pos + 12] == BAD_HEADER):
            changed = True
        else:
            out.append(data[pos:end])
        pos = end
    if changed:
        path.write_bytes(b''.join(out))
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--all', action='store_true', help='remove any eXIf chunk, not just ones with a bad header')
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()

    checked = changed = 0
    for path in args.paths:
        files = sorted(path.rglob('*.png')) if path.is_dir() else [path]
        for f in files:
            checked += 1
            if strip_exif(f, args.all):
                changed += 1
    print(f'{changed} of {checked} PNGs changed', file=sys.stderr)


if __name__ == '__main__':
    main()
