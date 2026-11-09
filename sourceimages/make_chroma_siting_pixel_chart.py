"""
Generate the chroma siting pixel charts: tiny frames to zoom in on, which show directly what a player does with
one chroma sample. They are the cross-check for the player charts (make_chroma_siting_player_chart.py and _420.py),
whose answer depends on display gamma. See ChromaSitingTests.md, "Checking the pixels".

A 64x64 frame of flat grey luma with a 3x3 grid of cells. In each cell a single chroma sample is raised, always at
a position that 4:2:2 or 4:2:0 stores: column 16, 32 or 48 (and, in 4:2:0, the chroma row stored for luma rows 16, 32
or 48). In 4:2:2 it is a vertical segment of the same sample, eight rows high. Luma-only tick rulers along the top
(and, for 4:2:0, the left) mark the raised sample's column and row, longer ticks, and every chroma site, shorter
ones. Nothing but the player's reconstruction spreads the colour, so where it is centred relative to the tick is the
siting the player assumes:

  Co-sited, interpolated    .5   1  .5   0     centred on the tick
  Centred, linear           .25 .75 .75 .25    (from one column left of the tick) centred between the tick and the next
  Sample repeat              0   1   1   0     centred between the tick and the next

There are three cells across so that a fault in part of the picture shows (the half-width xStudio bug, for one).

The reference files are 4:4:4, so no chroma reconstruction happens in them, and hold those expected pixels. Viewed in
the same player, at the same zoom and through the same view transform, they can be flipped against the test file. In
the 4:2:2 reference each row of cells is one assumption, top to bottom: co-sited, centred linear, sample repeat. In
the 4:2:0 reference the columns are the assumption across (the same three) and the rows the assumption down: centred
linear, sample repeat, co-sited linear.

10-bit (and 8-bit where the name says so) BT.709 limited range, FFV1, 2 s:

  chroma_siting_pixel_chart_422-10bit.mkv, _422-8bit.mkv, _422-reference.mkv
  chroma_siting_pixel_chart_420-10bit.mkv, _420-8bit.mkv, _420-reference.mkv

(No name ends in a number: xStudio would read _422.mkv as frame 422 of a sequence and fail to show it.)

Needs ffmpeg on the PATH (or FFMPEG_BIN) and numpy.

    python sourceimages/make_chroma_siting_pixel_chart.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
NAME = "chroma_siting_pixel_chart"
SIZE, CELL, MARGIN = 64, 16, 8
SITES = [16, 32, 48]                # the columns (and rows) holding a raised chroma sample
HALF = 4                            # 4:2:2: the segment covers rows site - HALF .. site + HALF - 1
LUMA, CB, CR = 0.5, 0.2, 0.2        # in gamut for every assumption, including a bicubic filter's overshoot
# Weight of the sample in the pixels at offset -1, 0, 1, 2 from the tick
PROFILE = {"co-sited": [0.5, 1, 0.5, 0], "centred": [0.25, 0.75, 0.75, 0.25], "repeat": [0, 1, 1, 0]}
ACROSS = ["co-sited", "centred", "repeat"]      # the 4:2:2 reference's rows; the 4:2:0 reference's columns
DOWN = ["centred", "repeat", "co-sited"]        # the 4:2:0 reference's rows


def luma_plane(chroma_h):
    """Flat grey with the rulers: top always, left only when the vertical position matters."""
    y = np.full((SIZE, SIZE), LUMA)
    y[4:6, MARGIN:SIZE - MARGIN] = np.where(np.arange(MARGIN, SIZE - MARGIN) % 2 == 0, 0.75, LUMA)
    for s in SITES:
        y[1:6, s] = 1.0
    if chroma_h:
        y[MARGIN:SIZE - MARGIN, 4:6] = np.where(np.arange(MARGIN, SIZE - MARGIN) % 2 == 0, 0.75, LUMA)[:, None]
        for s in SITES:
            y[s, 1:6] = 1.0
    return y


def test_planes(chroma_h):
    """Y, Cb, Cr as floats: chroma at half width and, for 4:2:0, half height."""
    y = luma_plane(chroma_h)
    w, h = SIZE // 2, SIZE // 2 if chroma_h else SIZE
    weight = np.zeros((h, w))
    for sx in SITES:
        for sy in SITES:
            if chroma_h:
                weight[sy // 2, sx // 2] = 1
            else:
                weight[sy - HALF:sy + HALF, sx // 2] = 1
    return y, weight * CB, weight * CR


def reference_weight(chroma_h):
    """Full-resolution weight of the raised sample, for each assumption in its cell."""
    weight = np.zeros((SIZE, SIZE))
    for i, sx in enumerate(SITES):
        for j, sy in enumerate(SITES):
            across = np.array(PROFILE[ACROSS[i] if chroma_h else ACROSS[j]])
            if chroma_h:
                down = np.array(PROFILE[DOWN[j]])
                weight[sy - 1:sy + 3, sx - 1:sx + 3] = np.outer(down, across)
            else:
                weight[sy - HALF:sy + HALF, sx - 1:sx + 3] = across
    return weight


def reference_planes(chroma_h):
    weight = reference_weight(chroma_h)
    return luma_plane(chroma_h), weight * CB, weight * CR


def to_bytes(planes, bits):
    y, cb, cr = planes
    codes = [np.round(y * 876 + 64), np.round(cb * 896 + 512), np.round(cr * 896 + 512)]
    codes = [np.clip(p, 4, 1019).astype("<u2") for p in codes]
    if bits == 8:                       # here rather than in FFmpeg, which may dither
        return b"".join((((p.astype(int) + 2) // 4).clip(1, 254).astype(np.uint8)).tobytes() for p in codes)
    return b"".join(p.tobytes() for p in codes)


def main():
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    jobs = [("_422-10bit", test_planes(False), "yuv422p10le", 10), ("_422-8bit", test_planes(False), "yuv422p", 8),
            ("_422-reference", reference_planes(False), "yuv444p10le", 10),
            ("_420-10bit", test_planes(True), "yuv420p10le", 10), ("_420-8bit", test_planes(True), "yuv420p", 8),
            ("_420-reference", reference_planes(True), "yuv444p10le", 10)]
    with tempfile.TemporaryDirectory() as tmp:
        for suffix, planes, pix_fmt, bits in jobs:
            raw = Path(tmp) / "chart.yuv"
            raw.write_bytes(to_bytes(planes, bits))
            out = HERE / f"{NAME}{suffix}.mkv"
            subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{SIZE}x{SIZE}",
                            "-r", "25", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", "-stream_loop", "49", "-i", str(raw), "-c:v", "ffv1",
                            "-chroma_sample_location", "left", str(out)], check=True)
            print(out.name, out.stat().st_size)


if __name__ == "__main__":
    main()
