"""
Generate the 4:2:2 chroma siting player chart: a test you look at, zoomed out, to see where a player puts 4:2:2
chroma. See ChromaSiting.md, "Checking a player by eye".

Four bands, each a checkerboard of 120x120 blocks. Test blocks have vertical stripes with a four-pixel cycle,
the chroma samples X and Z on the even (co-sited) columns. How a player fills in the odd columns depends on where
it thinks the chroma is: co-sited, the odd columns get the average of X and Z; centred, each pixel pair shares
one value, mid +- a*(X-Z)/2, where a is 0.5 for linear interpolation (GPU texture sampling, libswscale bilinear),
about 0.7 for bicubic/lanczos (libswscale's default, measured 0.67-0.71) and 1 for sample repeat. Reference
blocks have horizontal stripes, which 4:2:2 holds exactly whatever the player does, set to the pixels one kind of
player produces from the test stripes. So in the band that matches the player, test and reference blocks contain
the same pixels and the band looks like a uniform field; in the others the checkerboard shows. The colours were
chosen so every wrong band differs by at least 0.04 in Oklab (linear-light means, display gamma 2.4), with every
pixel in gamut for every kind of player, so the difference comes from display gamma alone, not from clipping.

The difference only appears when the display turns each pixel into light and the eye averages it: Y'CbCr to
R'G'B' is linear, so the mean code value of a test block is the same for every player. A viewer that shrinks the
picture averages code values first, which removes it, and at half size or less a wrong player looks right. A
scale check in the title band guards against that: a one-pixel black/white checkerboard beside a 20-pixel one.
Both are half black, half white, so whatever the display or view transform does, at 100% they look equally bright
from a distance; shrunk, the fine half turns into a darker grey. It is neutral, so chroma siting does not affect
it.

Writes 10-bit BT.709 limited range 4:2:2. The chroma is always co-sited; where the container can say so, it is
labelled co-sited, and two files carry a wrong label on purpose, to show whether a player reads the label:

  chroma_siting_player_chart_422.mkv                       FFV1, lossless, labelled left (co-sited)
  chroma_siting_player_chart_422-labelled-center.mkv       the same pixels, labelled center
  chroma_siting_player_chart_422-prores.mov                ProRes 422 HQ, one frame (MOV has no label)
  chroma_siting_player_chart_422-hevc.mp4                  HEVC Main 4:2:2 10, CRF 4, 2 s (plays in browsers)
  chroma_siting_player_chart_422-h264.mp4                  H.264 High 4:4:4 Predictive, lossless 4:2:2, 2 s
  chroma_siting_player_chart_422-dnxhr.mxf                 DNxHR HQX, OP1a, one frame, ColorSiting 0 (co-sited)
  chroma_siting_player_chart_422-dnxhr-labelled-center.mxf the same file with ColorSiting 1 (horizontal mid-point)

A player that ignores the label shows the same band for both files of a pair; one that reads it shows a centred
band for the "labelled-center" file. FFmpeg cannot write ColorSiting 1 (it maps center to 3, a 4:2:0 value), so
that byte is patched after encoding.

Needs ffmpeg with libx264 and libx265 on the PATH (or FFMPEG_BIN), numpy and Pillow.

    python sourceimages/make_chroma_siting_player_chart.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
NAME = "chroma_siting_player_chart_422"
W, H, BLOCK, TOP, LABEL = 1920, 1080, 120, 120, 480
CHECK = (1560, 10, 1900, 110)       # scale check: x0, y0, x1, y1; fine checkerboard left, coarse right
# label, note, centred strength a (None = co-sited), chroma X, chroma Z (Cb, Cr), luma of the four pixels in the
# cycle. Found by searching for the largest smallest difference between the right band and the others.
BANDS = [
    ("Co-sited (correct)", "interpolates co-sited chroma", None,
     (0.233, 0.175), (-0.218, -0.191), (0.351, 0.126, 0.404, 0.870)),
    ("Centred, linear", "e.g. GPU texture sampling", 0.5,
     (-0.340, -0.401), (0.369, 0.435), (0.631, 0.631, 0.315, 0.315)),
    ("Centred, bicubic", "e.g. FFmpeg's default (libswscale)", 0.69,
     (0.345, 0.407), (-0.297, -0.350), (0.360, 0.256, 0.551, 0.577)),
    ("Sample repeat", "each chroma sample used for two pixels", 1.0,
     (0.348, 0.421), (-0.101, -0.120), (0.262, 0.262, 0.189, 0.188)),
]


def decoded_chroma(a, X, Z):
    """Chroma of the four pixels in a cycle as a player of kind a reconstructs it."""
    X, Z = np.array(X), np.array(Z)
    mid, h = (X + Z) / 2, (X - Z) / 2
    if a is None:
        return np.stack([X, mid, Z, mid])
    return np.stack([mid + a * h, mid + a * h, mid - a * h, mid - a * h])


def chart():
    """The chart as 10-bit Y, Cb, Cr planes (Cb and Cr at half width, co-sited)."""
    y = np.full((H, W), 0.5)
    cb = np.zeros((H, W))
    cr = np.zeros((H, W))
    for k, (_, _, a, X, Z, lumas) in enumerate(BANDS):
        r0, r1 = TOP + k * 2 * BLOCK, TOP + (k + 1) * 2 * BLOCK
        yy, xx = np.mgrid[r0:r1, LABEL:W]
        test = ((yy - r0) // BLOCK + (xx - LABEL) // BLOCK) % 2 == 0
        lum = np.array(lumas)
        # Test: varies along x, chroma X/Z on columns 0 and 2 of each cycle (4:2:2 keeps only the even columns).
        sampled = decoded_chroma(None, X, Z)
        ty, tc = lum[xx % 4], sampled[xx % 4]
        # Reference: varies along y, the pixels this band's kind of player makes from the test stripes.
        ry, rc = lum[(yy - r0) % 4], decoded_chroma(a, X, Z)[(yy - r0) % 4]
        y[r0:r1, LABEL:] = np.where(test, ty, ry)
        cb[r0:r1, LABEL:] = np.where(test, tc[..., 0], rc[..., 0])
        cr[r0:r1, LABEL:] = np.where(test, tc[..., 1], rc[..., 1])
    # Text in luma only, on the neutral grey of the title band and the label column.
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    big, mid, small = (ImageFont.load_default(size=s) for s in (30, 26, 20))
    d.text((24, 14), "4:2:2 chroma siting: which band is a uniform field?", fill=255, font=big)
    d.text((24, 58), "H.264, HEVC, ProRes and DNxHD 4:2:2 are co-sited: only the top band should be uniform. "
                     "None uniform: something else (e.g. 4:2:0).", fill=255, font=small)
    d.text((24, 86), "View at exactly 100%. If the two halves of the patch on the right are not equally bright, "
                     "the viewer is scaling: ignore the bands.", fill=255, font=small)
    for k, (label, note, *_) in enumerate(BANDS):
        r0 = TOP + k * 2 * BLOCK
        d.text((24, r0 + 90), label, fill=255, font=mid)
        d.text((24, r0 + 126), note, fill=200, font=small)
    text_area = np.zeros((H, W), bool)
    text_area[:TOP] = True
    text_area[:, :LABEL] = True
    y = np.where(text_area, 0.45 + 0.45 * np.asarray(img) / 255.0, y)
    cb[text_area], cr[text_area] = 0, 0
    # Scale check: one-pixel checkerboard on the left half, 20-pixel checkerboard on the right half.
    x0, y0, x1, y1 = CHECK
    xm = (x0 + x1) // 2
    yy, xx = np.mgrid[y0:y1, x0:x1]
    y[y0:y1, x0:x1] = np.where(xx < xm, (yy + xx) % 2, ((yy - y0) // 20 + (xx - xm) // 20) % 2)
    y, cb, cr = np.round(y * 876 + 64), np.round(cb * 896 + 512), np.round(cr * 896 + 512)
    return [np.clip(p, 4, 1019).astype("<u2") for p in (y, cb[:, 0::2], cr[:, 0::2])]


def main():
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "chart.yuv"
        with open(raw, "wb") as f:
            for plane in chart():
                f.write(plane.tobytes())
        src = ["-f", "rawvideo", "-pix_fmt", "yuv422p10le", "-s", f"{W}x{H}", "-r", "25", "-color_range", "tv",
               "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        loop = ["-stream_loop", "49"]           # 2 s for the formats that compress a static frame to nothing
        mp4 = ["-movflags", "+write_colr", "-chroma_sample_location", "left"]
        jobs = [
            (src + ["-i", raw, "-c:v", "ffv1", "-chroma_sample_location", "left"], ".mkv"),
            (src + ["-i", raw, "-c:v", "ffv1", "-chroma_sample_location", "center"], "-labelled-center.mkv"),
            (src + ["-i", raw, "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0"], "-prores.mov"),
            (src + loop + ["-i", raw, "-c:v", "libx265", "-crf", "4", "-tag:v", "hvc1",
                           "-x265-params", "log-level=error"] + mp4, "-hevc.mp4"),
            (src + loop + ["-i", raw, "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv422p10le"] + mp4, "-h264.mp4"),
            # No chroma location on the frames, so FFmpeg writes ColorSiting 0 (co-sited), the right value.
            (src + ["-i", raw, "-c:v", "dnxhd", "-profile:v", "dnxhr_hqx"], "-dnxhr.mxf"),
        ]
        for args, suffix in jobs:
            out = HERE / (NAME + suffix)
            subprocess.run([ffmpeg, "-v", "error", "-y"] + [str(a) for a in args] + [str(out)], check=True)
            print(out.name, out.stat().st_size)
        mxf = (HERE / (NAME + "-dnxhr.mxf")).read_bytes()
        out = HERE / (NAME + "-dnxhr-labelled-center.mxf")
        out.write_bytes(set_mxf_color_siting(mxf, 1))
        print(out.name, out.stat().st_size)


def set_mxf_color_siting(data, value):
    """Set the CDCI descriptor's ColorSiting (local tag 0x3303, one byte) to value."""
    tag = b"\x33\x03\x00\x01"
    at = data.find(tag)
    if at < 0 or data.find(tag, at + 1) >= 0:
        raise RuntimeError("expected exactly one ColorSiting in the MXF file")
    at += len(tag)
    return data[:at] + bytes([value]) + data[at + 1:]


if __name__ == "__main__":
    main()
