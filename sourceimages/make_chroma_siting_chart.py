"""
Generate chroma_siting_chart.png, a 16-bit RGB test chart for chroma siting (chroma sample location).

1920x1080, full range, mid grey (0.5) background, in four bands of 270 rows (all band edges are on even
rows, so they line up with 4:2:0 chroma rows):

  rows    0-269  Horizontal tent: blue rises linearly from 0.2 at the left edge to 0.8 exactly between
                 columns 959 and 960, then falls again. Used to measure horizontal chroma position.
  rows  270-539  Vertical tent: the same, rising from 0.2 at row 270 to 0.8 exactly between rows 404 and
                 405, then falling to row 539. Used to measure vertical chroma position (4:2:0).
  rows  540-809  Single-pixel vertical blue lines (blue 0.9), every 16 pixels: on even columns
                 (16, 32 ... 944) in the left half, on odd columns (977, 993 ... 1905) in the right half.
  rows  810-1079 Single-pixel horizontal blue lines, every 16 rows: on even rows (818, 834 ... 1074) in
                 the left half, on odd rows (819, 835 ... 1075) in the right half.

With correctly co-sited chroma, a line on an even column lands on one chroma sample and a line on an odd
column splits evenly between two; with centred chroma it is the other way round. Zoomed in, wrong siting
shows as colour fringing that is lopsided towards one side.

The PNG is written directly (rather than with OpenImageIO, which adds sRGB/gAMA/cHRM chunks), so it
carries no colour tags that FFmpeg would pick up as frame properties.

    python sourceimages/make_chroma_siting_chart.py
"""
import struct
import zlib
from pathlib import Path

import numpy as np

W, H = 1920, 1080
BAND = 270
GREY, LINE = 0.5, 0.9
OUT = Path(__file__).resolve().parent / "chroma_siting_chart.png"

# Line positions, shared with tests/chroma_siting.py.
EVEN_COLUMNS = list(range(16, W // 2, 16))
ODD_COLUMNS = list(range(W // 2 + 17, W - 1, 16))
EVEN_ROWS = list(range(3 * BAND + 8, H - 1, 16))
ODD_ROWS = [r + 1 for r in EVEN_ROWS]


def tent(n):
    """0.2 .. 0.8 .. 0.2 over n samples, peaking exactly between samples n/2-1 and n/2."""
    x = np.arange(n)
    c = (n - 1) / 2
    return 0.2 + 0.6 * (1 - np.abs(x - c) / c)


def chart():
    rgb = np.full((H, W, 3), GREY)
    rgb[0:BAND, :, 2] = tent(W)[None, :]
    rgb[BAND:2 * BAND, :, 2] = tent(BAND)[:, None]
    rgb[2 * BAND:3 * BAND, EVEN_COLUMNS + ODD_COLUMNS, 2] = LINE
    rgb[EVEN_ROWS, :W // 2, 2] = LINE
    rgb[ODD_ROWS, W // 2:, 2] = LINE
    return rgb


def write_png(path, rgb):
    """Minimal 16-bit RGB PNG writer: IHDR, IDAT and IEND only, so no colour chunks."""
    data = np.round(rgb * 65535).astype(">u2")
    raw = b"".join(b"\x00" + row.tobytes() for row in data)

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    ihdr = struct.pack(">IIBBBBB", data.shape[1], data.shape[0], 16, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))


if __name__ == "__main__":
    write_png(OUT, chart())
    print(f"Wrote {OUT}")
