"""
Generate the chroma siting check files: small charts that show the word WRONG when a player rebuilds the chroma
somewhere other than where the file's label says it is, and a blank field when it gets it right. See
ChromaSitingTests.md.

Each file is designed for its own label (or, untagged, for the default of its format), so the rule is the same for
every file: blank means the player followed the label. A 4:2:0 file has two panels, Across and Down, which can be
wrong independently; a 4:2:2 file has only Across.

How it works: the mirror trick of the 4:2:0 player chart (make_chroma_siting_player_chart_420.py), with its colours.
A panel's background repeats a four-pixel cycle of stripes along one direction (vertical stripes across, horizontal
ones down); the word has the same chroma and the luma of the mirror image. For a player that rebuilds the chroma
as the label says, every pixel of the word is a pixel of the background, so from a distance the word disappears;
for any other player the word and background have different linear-light means and the word shows. Where the word's
edge crosses the stripes, the pattern changes phase, which shows as a faint line; the edge is staggered by 0 to 7
pixels from row to row, in a scrambled order, which cancels most of it (to about a twentieth of the word's
contrast, simulated).

As with the player charts, it only works at exactly 100%: a viewer that scales the picture averages the code
values first and the word disappears whatever the player does. The scale check in the caption shows that: its two
halves look equally bright only at 100%.

Writes 10-bit (8-bit for the 8-bit codecs) BT.709 limited range into chroma_siting_check/:

  chroma_siting_check_420-<codec>-<label>.<ext>   4:2:0, labelled left, topleft, center, or untagged (= left)
  chroma_siting_check_422-<codec>-<label>.<ext>   4:2:2, untagged (= co-sited), left, or center

Needs ffmpeg with libx264 and libx265 on the PATH (or FFMPEG_BIN), numpy and Pillow.

    python sourceimages/make_chroma_siting_check.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from make_chroma_siting_player_chart import set_mxf_color_siting
from make_chroma_siting_player_chart_420 import BANDS, MIRROR

HERE = Path(__file__).resolve().parent
OUT = HERE / "chroma_siting_check"
NAME = "chroma_siting_check"
W = 640
CAPTION, ROW, LABEL = 72, 144, 128     # caption height, panel row height, label column width (all multiples of 4)
UNIT = 16                               # size of one block of the 5x7 font
STAGGER = np.array([0, 5, 2, 7, 4, 1, 6, 3])
CHECK = (488, 8, 632, 64)               # scale check: one-pixel checkerboard left, eight-pixel right
BAND = {band[0].split(" (")[0]: band for band in BANDS}
# What a player should do for each label: the band whose mirror matches it, across and down.
EXPECT = {
    "untagged": ("Across: co-sited", "Down: centered"),
    "left": ("Across: co-sited", "Down: centered"),
    "topleft": ("Across: co-sited", "Down: co-sited"),
    "center": ("Across: centered", "Down: centered"),
}
GLYPHS = {
    "W": ["X...X", "X...X", "X...X", "X.X.X", "X.X.X", "XX.XX", "X...X"],
    "R": ["XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
    "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "N": ["X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X", "X...X"],
    "G": [".XXX.", "X...X", "X....", "X.XXX", "X...X", "X...X", ".XXX."],
}


def word_mask(text="WRONG"):
    """The word as a boolean array, one cell per font block, with one block between letters."""
    cols = []
    for k, ch in enumerate(text):
        if k:
            cols.append(np.zeros((7, 1), bool))
        cols.append(np.array([[c == "X" for c in row] for row in GLYPHS[ch]]))
    return np.hstack(cols)


def panel_mask(rows, axis):
    """Where the word is in a panel row (ROW x (W - LABEL)), with its edges across the stripes staggered."""
    cells = word_mask()
    big = np.kron(cells, np.ones((UNIT, UNIT), bool))
    h, w = big.shape
    ph, pw = ROW, W - LABEL
    y0, x0 = (ph - h) // 2 // 4 * 4, (pw - w) // 2 // 4 * 4
    yy, xx = np.mgrid[0:ph, 0:pw]
    # Shift the word by 0..7 pixels along the stripes' direction, in a scrambled order that repeats every eight
    # rows (columns for Down): every phase of the cycle twice, spread out, so the edge lines cancel.
    if axis == "x":
        xx = xx - STAGGER[rows[:, None] % 8]
    else:
        yy = yy - STAGGER[np.arange(pw)[None, :] % 8]
    inside = (yy >= y0) & (yy < y0 + h) & (xx >= x0) & (xx < x0 + w)
    m = np.zeros((ph, pw), bool)
    m[inside] = big[(yy - y0)[inside], (xx - x0)[inside]]
    return m


def panels(sub, label, rotated=False):
    """The panels of a file as displayed, top to bottom: (band, axis the stripes vary along on screen, panel label).
    The band is chosen by the axis of the stored (coded) frame, which is what the label describes; a file rotated
    by 90 degrees for display swaps the axes, so its Across panel (on screen) tests the stored frame's vertical
    siting."""
    bands = [EXPECT[label][0]] if sub == "422" else list(EXPECT[label])
    out = []
    for name in bands:
        axis = BAND[name][2]
        if rotated:
            axis = "y" if axis == "x" else "x"
        out.append((name, axis, "Across" if axis == "x" else "Down"))
    return sorted(out, key=lambda p: p[1])          # Across first


def coded_coords(yy, xx, rotated):
    """Stored-frame coordinates (y, x) of displayed pixels: the stored frame is the displayed one turned 90
    degrees counterclockwise (np.rot90), and the file says to turn it back clockwise."""
    return (W - 1 - xx, yy) if rotated else (yy, xx)


def chart(sub, label, caption, rotated=False):
    """Y, Cb, Cr as 10-bit codes in the stored orientation, Cb and Cr subsampled for sub ("420" or "422"), and the
    stored frame's size (width, height)."""
    pans = panels(sub, label, rotated)
    H = CAPTION + ROW * len(pans)
    y = np.full((H, W), 0.45)
    cb, cr = np.zeros((H, W)), np.zeros((H, W))
    for k, (name, axis, _) in enumerate(pans):
        _, _, coded_axis, mirror, (X, Z, lumas) = BAND[name]
        r0 = CAPTION + k * ROW
        yy, xx = np.mgrid[r0:r0 + ROW, LABEL:W]
        cy, cx = coded_coords(yy, xx, rotated)
        u = cx if coded_axis == "x" else cy        # stored-frame position, so the cycle lines up with its chroma grid
        word = panel_mask(np.arange(r0, r0 + ROW), axis)
        lum = np.array(lumas)
        y[r0:r0 + ROW, LABEL:] = np.where(word, lum[np.array(MIRROR[mirror])[u % 4]], lum[u % 4])
        c = np.array([X, Z])[(u // 2) % 2]
        cb[r0:r0 + ROW, LABEL:], cr[r0:r0 + ROW, LABEL:] = c[..., 0], c[..., 1]
    # Caption and panel labels, luma only.
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    big, small = ImageFont.load_default(size=20), ImageFont.load_default(size=14)
    d.text((12, 8), caption, fill=255, font=big)
    d.text((12, 36), "View at 100%, from a distance. A word = wrong; blank = right.", fill=220, font=small)
    d.text((12, 52), "Scale check (right): both halves equally bright, or not 100%.", fill=220, font=small)
    for k, (_, _, panel_label) in enumerate(pans):
        d.text((12, CAPTION + k * ROW + ROW // 2 - 10), panel_label, fill=255, font=big)
    text = np.zeros((H, W), bool)
    text[:CAPTION] = True
    text[:, :LABEL] = True
    y = np.where(text, 0.15 + 0.7 * np.asarray(img) / 255.0, y)
    cb[text], cr[text] = 0, 0
    x0, y0, x1, y1 = CHECK
    xm = (x0 + x1) // 2
    yy, xx = np.mgrid[y0:y1, x0:x1]
    on = np.where(xx < xm, (yy + xx) % 2, ((yy - y0) // 8 + (xx - xm) // 8) % 2)
    y[y0:y1, x0:x1] = on
    planes = [np.round(y * 876 + 64), np.round(cb * 896 + 512), np.round(cr * 896 + 512)]
    planes = [np.clip(p, 4, 1019).astype("<u2") for p in planes]
    if rotated:
        planes = [np.ascontiguousarray(np.rot90(p)) for p in planes]
    h, w = planes[0].shape
    if sub == "420":
        return [planes[0], planes[1][0::2, 0::2], planes[2][0::2, 0::2]], (w, h)
    return [planes[0], planes[1][:, 0::2], planes[2][:, 0::2]], (w, h)


# (subsampling, codec, label, bit depth, encode arguments, extension)
LOOP = ["-stream_loop", "49"]     # 2 s for the codecs that compress a static frame to almost nothing
HEVC = ["-c:v", "libx265", "-crf", "4", "-tag:v", "hvc1", "-x265-params", "log-level=error"]
JOBS = [
    ("420", "lossless", "left", 10, ["-c:v", "ffv1"], "mkv", "FFV1"),
    ("420", "lossless", "topleft", 10, ["-c:v", "ffv1"], "mkv", "FFV1"),
    ("420", "lossless", "center", 10, ["-c:v", "ffv1"], "mkv", "FFV1"),
    ("420", "hevc", "untagged", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "hevc", "left", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "hevc", "topleft", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "hevc", "center", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "h264", "untagged", 8, LOOP + ["-c:v", "libx264", "-crf", "1"], "mp4", "H.264 8-bit"),
    ("420", "h264", "topleft", 8, LOOP + ["-c:v", "libx264", "-crf", "1"], "mp4", "H.264 8-bit"),
    ("420", "h264", "center", 8, LOOP + ["-c:v", "libx264", "-crf", "1"], "mp4", "H.264 8-bit"),
    ("422", "lossless", "left", 10, ["-c:v", "ffv1"], "mkv", "FFV1"),
    ("422", "lossless", "center", 10, ["-c:v", "ffv1"], "mkv", "FFV1"),
    ("422", "prores", "untagged", 10, ["-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0"], "mov",
     "ProRes 422 HQ"),
    ("422", "hevc", "untagged", 10, LOOP + HEVC, "mp4", "HEVC 4:2:2 10-bit"),
    ("422", "dnxhr", "untagged", 10, ["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx"], "mxf", "DNxHR HQX"),
    ("422", "dnxhr", "center", 10, ["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx"], "mxf", "DNxHR HQX"),
]
# Stored sideways, with a display matrix that turns them upright: a player has to rebuild the chroma on the stored
# frame's grid (which the label describes) and then rotate, or swap the siting if it rotates the planes first.
ROTATED = [
    ("420", "hevc", "left", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "hevc", "topleft", 10, LOOP + HEVC, "mp4", "HEVC 10-bit"),
    ("420", "h264", "untagged", 8, LOOP + ["-c:v", "libx264", "-crf", "1"], "mp4", "H.264 8-bit"),
    ("420", "h264", "topleft", 8, LOOP + ["-c:v", "libx264", "-crf", "1"], "mp4", "H.264 8-bit"),
    ("422", "hevc", "untagged", 10, LOOP + HEVC, "mp4", "HEVC 4:2:2 10-bit"),
    ("422", "prores", "untagged", 10, ["-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0"], "mov",
     "ProRes 422 HQ"),
]


def file_name(sub, codec, label, ext, rotated=False):
    return f"{NAME}_{sub}-{codec}-{label}{'-rot90' if rotated else ''}.{ext}"


def main():
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for (sub, codec, label, bits, enc, ext, codec_name), rotated in \
                [(job, False) for job in JOBS] + [(job, True) for job in ROTATED]:
            sub_name = "4:2:0" if sub == "420" else "4:2:2"
            caption = f"{sub_name}  {codec_name}  " + ("no label" if label == "untagged" else f"labelled {label}")
            if rotated:
                caption += ", rotated 90"
            planes, (w, h) = chart(sub, label, caption, rotated)
            raw = Path(tmp) / "chart.yuv"
            if bits == 8:
                # 8-bit from the 10-bit codes here, so FFmpeg does not dither and break the mirror symmetry.
                raw.write_bytes(b"".join(((p.astype(int) + 2) // 4).clip(1, 254).astype(np.uint8).tobytes()
                                         for p in planes))
                pix = "yuv420p" if sub == "420" else "yuv422p"
            else:
                raw.write_bytes(b"".join(p.tobytes() for p in planes))
                pix = "yuv420p10le" if sub == "420" else "yuv422p10le"
            src = ["-f", "rawvideo", "-pix_fmt", pix, "-s", f"{w}x{h}", "-r", "25", "-color_range", "tv",
                   "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
            loc = [] if label == "untagged" or ext == "mxf" else ["-chroma_sample_location", label]
            # The loop must come before -i; the encoder arguments after it.
            pre = LOOP if enc[:2] == LOOP else []
            post = enc[2:] if pre else enc
            if rotated:
                # Counterclockwise, in degrees: the stored frame is turned 90 counterclockwise, so turn it back.
                # -noautorotate, or FFmpeg rotates the pixels itself and writes no display matrix.
                pre = pre + ["-display_rotation", "-90", "-noautorotate"]
            out = OUT / file_name(sub, codec, label, ext, rotated)
            subprocess.run([ffmpeg, "-v", "error", "-y"] + src + pre + ["-i", str(raw)] + post + loc + [str(out)],
                           check=True)
            if ext == "mxf" and label == "center":
                # ST 377-1 value 1, horizontal mid-point; FFmpeg can only write 4:2:0 values for center.
                out.write_bytes(set_mxf_color_siting(out.read_bytes(), 1))
            print(out.name, out.stat().st_size)


if __name__ == "__main__":
    main()
