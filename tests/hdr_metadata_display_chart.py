"""
HDR10 metadata display test: does a player or display use the mastering display (MDCV) and content light level
(MaxCLL/MaxFALL) metadata, which copy does it read, and does it change a picture that is already within a known
standard (1000 cd/m^2, P3) when the metadata is honest or missing?

The chart (BT.2020, PQ) is encoded several times as HEVC Main 10 4:2:0 in MP4. Within each set the test patterns
are the same; only the metadata differs. The text on each chart says what it carries, which file to compare it
with and what a difference means. index.html flips between the files (or shows narrow strip versions side by
side); QuickTime or a TV works too.

Questions, and the files that answer them:
  1. Does the player/display use the mastering display info, which value, and from where?     02-05, 08, 09
  2. With no metadata, where does it clip?                                                       01, 10
  3. With no metadata, does the player change the picture? Clipping shows on the chart; a smooth change in
     brightness needs a meter, or the SDR white button on the page (see 10).                    10
  4. With metadata, how does it change the result?                                              02-06
  5. Content limited to 1000 cd/m^2 and P3 (what an OCIO 1000 nit P3 view gives): is it shown the same with no
     metadata and with honest metadata? And with wrong (too high) metadata?                     10, 11, 12
  6. Do the mastering display primaries change colours inside P3?                               02 vs 07
  7-10, not answered by the files alone: does it depend on the display settings (brightness/EDR headroom, TV
     picture mode, dynamic tone mapping, large bright areas)? On the player (QuickTime, Safari, Chrome, RV,
     xStudio, mpv)? Do images and video agree (gamuttests/make_gamut_tag_test.py)? Does the metadata survive the
     review tool's transcode (run --check on its output)?

  File                      Mastering display           MaxCLL           Carried in       Compare with
  01-none.mp4               (none: PQ10)                (none)           -                02, 03
  02-md1000.mp4             P3-D65, 1000 / 0.0001       1000             SEI + mdcv/clli  03
  03-md4000.mp4             P3-D65, 4000 / 0.005        4000             SEI + mdcv/clli  02
  04-md4000-cll1000.mp4     P3-D65, 4000 / 0.005        1000             SEI + mdcv/clli  02, 03
  05-md1000-cll4000.mp4     P3-D65, 1000 / 0.0001       4000             SEI + mdcv/clli  02, 03
  06-md1000-cll0.mp4        P3-D65, 1000 / 0.0001       0 (unknown)      SEI + mdcv/clli  02
  07-md1000-bt2020.mp4      BT.2020-D65, 1000 / 0.0001  1000             SEI + mdcv/clli  02 (colour)
  08-md4000-sei-only.mp4    P3-D65, 4000 / 0.005        4000             SEI only         03, 01
  09-md4000-box-only.mp4    P3-D65, 4000 / 0.005        4000             mdcv/clli only   03, 01
  10-clamped-none.mp4       (none)                      (none)           -                11   <- content limited
  11-clamped-md1000.mp4     P3-D65, 1000 / 0.0001       the real one     SEI + mdcv/clli  10      to 1000 cd/m^2
  12-clamped-md4000.mp4     P3-D65, 4000 / 0.005        4000             SEI + mdcv/clli  11      and P3

01-09 go up to 5000 cd/m^2 and outside P3, so their MaxCLL is deliberately wrong. MaxFALL is the chart's own.
Each file also has a narrow strip version (strips/), with the same metadata, for the side by side view.

Look at the display itself, by eye or with a camera at fixed exposure: tone mapping is often done after the
point a screenshot is taken. Keep the display settings fixed while comparing (macOS: turn off automatic
brightness and leave the slider alone; TV: turn dynamic tone mapping off, e.g. HGIG, to test the static metadata).

Needs FFmpeg 9.0 or later (-mastering_display/-content_light) with libx265, numpy and Pillow:
    rez-env encodingguidelines_env ffmpeg-9.0.2 -- python tests/hdr_metadata_display_chart.py
    rez-env encodingguidelines_env ffmpeg-9.0.2 -- python tests/hdr_metadata_display_chart.py --check
--check prints what each file carries: the MP4 mdcv/clli boxes, and the SEI in the HEVC bitstream (trace_headers).
"""
import argparse
import functools
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sourceimages"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python"))
from chroma_siting_420_colours import pq_eotf, pq_oetf  # noqa: E402
from flipbook import write_flipbook  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "hdr-metadata-display"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
W, H = 1920, 1080
SW = 240  # strip width
FPS, SECONDS = 24, 10
BACKGROUND = 0.5  # cd/m^2; not 0, so the patch edges are clear even on a display that crushes near-black
TEXT = (100.0, 100.0, 100.0)
DIM = (40.0, 40.0, 40.0)
ACCENT = (110.0, 95.0, 8.0)  # yellow (linear BT.2020, cd/m^2): what to compare, and the metadata markers

# Linear RGB (BT.2020 primaries) of the BT.709 and P3-D65 primaries.
BT709_TO_2020 = np.array([[0.6274, 0.3293, 0.0433], [0.0691, 0.9195, 0.0114], [0.0164, 0.0880, 0.8956]])
P3_TO_2020 = np.array([[0.7539, 0.1986, 0.0476], [0.0457, 0.9418, 0.0125], [-0.0012, 0.0176, 0.9836]])
KR, KB = 0.2627, 0.0593
LUMA = np.array([KR, 1 - KR - KB, KB])

STEPS = [100, 203, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000]
CLAMPED_STEPS = [100, 203, 300, 400, 500, 600, 700, 800, 900, 1000]
DELTA = 0.015  # PQ signal: about 13 10-bit codes, 12-16% in luminance over these steps
COLOUR_NITS = 50.0
INSIDE = 0.85  # the "inside P3" colours: 85% of the way from white to the P3 primary, in linear light
INSIDE_SQUARE = 0.6  # and the square in them: 60% of the way to the BT.709 primary

# x265/FFmpeg units: primaries and white point x 50000, luminance x 10000.
PRIMS = {"P3": "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)",
         "BT.2020": "G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)",
         "BT.709": "G(15000,30000)B(7500,3000)R(32000,16500)WP(15635,16450)"}

SAME = "Same test patterns, different metadata."
VARIANTS = [
    dict(name="01-none", short="none", mdcv=None, cll=None, carriage="both", clamped=False, compare="02 and 03",
         notes=["No HDR metadata (PQ10): this shows what the display assumes by default.",
                "Clip point like 02 = it assumes 1000 cd/m2.  Like 03 = it assumes 4000.  Neither = something else."]),
    dict(name="02-md1000", short="1000/1000", mdcv=("P3", 1000, 0.0001), cll=1000, carriage="both", clamped=False,
         compare="03", notes=[f"{SAME} The markers below show where this file says the content peaks.",
                              "03 clips later, or has dimmer mid-tones = the display uses the metadata.",
                              "03 looks the same = it ignores it (or can show 4000 cd/m2 anyway)."]),
    dict(name="03-md4000", short="4000/4000", mdcv=("P3", 4000, 0.005), cll=4000, carriage="both", clamped=False,
         compare="02", notes=[f"{SAME} The markers below show where this file says the content peaks.",
                              "Clips later than 02, or dimmer mid-tones = the display uses the metadata.",
                              "Same as 02 = it ignores it (or can show 4000 cd/m2 anyway)."]),
    dict(name="04-md4000-cll1000", short="4000/1000", mdcv=("P3", 4000, 0.005), cll=1000, carriage="both",
         clamped=False, compare="02 and 03",
         notes=["Mastering display peak 4000, MaxCLL 1000: the two values disagree.",
                "Looks like 03 = the display uses the mastering display peak.", "Looks like 02 = it uses MaxCLL."]),
    dict(name="05-md1000-cll4000", short="1000/4000", mdcv=("P3", 1000, 0.0001), cll=4000, carriage="both",
         clamped=False, compare="02 and 03",
         notes=["Mastering display peak 1000, MaxCLL 4000: the two values disagree.",
                "Looks like 02 = the display uses the mastering display peak.", "Looks like 03 = it uses MaxCLL."]),
    dict(name="06-md1000-cll0", short="1000/0", mdcv=("P3", 1000, 0.0001), cll=0, carriage="both", clamped=False,
         compare="02", notes=["MaxCLL 0 = unknown.",
                              "Looks like 02 = the display falls back to the mastering display peak.",
                              "Different = it has its own default for an unknown MaxCLL."]),
    dict(name="07-md1000-bt2020", short="BT.2020 prim.", mdcv=("BT.2020", 1000, 0.0001), cll=1000,
         carriage="both", clamped=False, compare="02 (colour check)",
         notes=["Mastering display primaries BT.2020 here, P3 in 02. Everything else is the same as 02.",
                "The colour check differs from 02 = the player gamut maps from the mastering display primaries.",
                "Most important: the INSIDE P3 colours should not change."]),
    dict(name="08-md4000-sei-only", short="SEI only", mdcv=("P3", 4000, 0.005), cll=4000, carriage="sei",
         clamped=False, compare="03 and 01",
         notes=["Metadata only in the HEVC SEI; no MP4 mdcv/clli boxes. Values as 03.",
                "Looks like 03 = the player reads the SEI.",
                "Looks like 01 (no metadata) = it only reads the MP4 boxes."]),
    dict(name="09-md4000-box-only", short="MP4 box only", mdcv=("P3", 4000, 0.005), cll=4000, carriage="box",
         clamped=False, compare="03 and 01",
         notes=["Metadata only in the MP4 mdcv/clli boxes; no SEI. Values as 03.",
                "Looks like 03 = the player reads the MP4 boxes.",
                "Looks like 01 (no metadata) = it only reads the SEI."]),
    dict(name="10-clamped-none", short="lim. none", mdcv=None, cll=None, carriage="both", clamped=True,
         compare="11",
         notes=["Content limited to 1000 cd/m2 and P3, as an OCIO 1000 nit P3 view gives. No metadata.",
                "On a display that reaches 1000 cd/m2 every darker square should be visible, and 11 should look",
                "identical. SDR white button (page): in a reference mode with SDR white at 100, it should match 100."]),
    dict(name="11-clamped-md1000", short="lim. honest", mdcv=("P3", 1000, 0.0001), cll="real", carriage="both",
         clamped=True, compare="10",
         notes=["Same limited content, with honest metadata: P3 mastering display, 1000 cd/m2, the real MaxCLL.",
                "Identical to 10 = honest metadata changes nothing (what we want).",
                "Different = the player changes the picture even when the metadata is right."]),
    dict(name="12-clamped-md4000", short="lim. wrong", mdcv=("P3", 4000, 0.005), cll=4000, carriage="both",
         clamped=True, compare="11",
         notes=["Same limited content, but the metadata claims 4000 cd/m2.",
                "Darker or flatter than 11 = the player makes room for highlights that are not there:",
                "this is why the metadata must match the content."]),
]
LEGEND = ("01 none  02 1000/1000  03 4000/4000  04 4000/1000  05 1000/4000  06 1000/0  07 BT.2020 prim.  "
          "08 SEI only  09 MP4 box only  |  limited to 1000/P3:  10 none  11 honest  12 says 4000")
# The right half of the 100 cd/m^2 mid-tone patch, for the page's SDR white overlay.
SDR_WHITE = {"x": 140, "y": 800, "w": 100, "h": 140, "width": W, "height": H, "label": "SDR white"}


@functools.lru_cache(None)
def font(size):
    return ImageFont.load_default(size=size)


class Canvas:
    """Linear light (cd/m^2, BT.2020 primaries), with text and markers drawn over it in PQ signal."""

    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.lin = np.full((h, w, 3), BACKGROUND)
        self.layers = {}  # colour: (image, draw)

    def _draw(self, colour):
        if colour not in self.layers:
            img = Image.new("L", (self.w, self.h), 0)
            self.layers[colour] = (img, ImageDraw.Draw(img))
        return self.layers[colour][1]

    def rect(self, x, y, w, h, rgb):
        # Even coordinates, so each patch is whole 2x2 chroma blocks and 4:2:0 does not change its colour.
        assert x % 2 == y % 2 == w % 2 == h % 2 == 0, (x, y, w, h)
        self.lin[y:y + h, x:x + w] = rgb

    def grey(self, x, y, w, h, nits):
        self.rect(x, y, w, h, (nits, nits, nits))

    def text(self, x, y, s, size=24, anchor="lt", colour=TEXT):
        self._draw(colour).text((x, y), s, fill=255, font=font(size), anchor=anchor)

    def triangle(self, x, y, colour=ACCENT, s=14):
        self._draw(colour).polygon([(x, y), (x - s, y + s * 1.6), (x + s, y + s * 1.6)], fill=255)

    def outline(self, box, colour=ACCENT, width=3):
        self._draw(colour).rectangle(box, outline=255, width=width)

    def signal(self):
        sig = pq_oetf(np.clip(self.lin, 0, 10000))
        for colour, (img, _) in self.layers.items():
            a = (np.asarray(img, dtype=float) / 255)[..., None]
            sig = sig * (1 - a) + pq_oetf(np.array(colour)) * a
        return sig


def square_nits(nits, clamped):
    """The inner square: a little brighter than the step, or a little darker for the limited content."""
    return float(pq_eotf(float(pq_oetf(nits)) + (-DELTA if clamped else DELTA)))


def markers(v, max_cll):
    """{step: [what]} for this file's mastering display peak and MaxCLL."""
    steps = CLAMPED_STEPS if v["clamped"] else STEPS
    out = {}
    cll = max_cll if v["cll"] == "real" else v["cll"]
    for what, value in (("mastering peak", v["mdcv"] and v["mdcv"][1]), ("MaxCLL", cll)):
        if not value:
            continue
        nearest = min(steps, key=lambda s: abs(s - value))
        if value > steps[-1] * 1.1:
            what = f"{what} {value} (above the chart)"
        elif nearest != value:
            what = f"{what} {value}"
        out.setdefault(nearest, []).append(what)
    return out


def at_nits(rgb, nits=COLOUR_NITS):
    return rgb * nits / (LUMA @ rgb)


def primaries(k):
    e = np.eye(3)[k]
    return BT709_TO_2020 @ e, P3_TO_2020 @ e, e


def metadata_line(v, cll, fall):
    if v["mdcv"] is None:
        return "No mastering display, no MaxCLL"
    where = {"both": "HEVC SEI + MP4 boxes", "sei": "HEVC SEI only", "box": "MP4 boxes only"}[v["carriage"]]
    p, peak, low = v["mdcv"]
    return (f"Mastering display {p}-D65, {peak} / {low:g} cd/m2    MaxCLL {cll if cll else '0 (unknown)'}, "
            f"MaxFALL {fall if cll else 0}    in {where}")


def chart(v, cll, fall, max_cll):
    clamped = v["clamped"]
    c = Canvas()

    # Header: which file, and what it carries.
    c.text(40, 18, v["name"][:2], 96)
    c.text(190, 26, "HDR10 METADATA TEST" + ("  -  CONTENT LIMITED TO 1000 cd/m2 AND P3" if clamped else ""), 24,
           colour=ACCENT if clamped else DIM)
    c.text(190, 62, metadata_line(v, cll, fall), 30)

    # What to do with this file.
    c.outline((40, 130, W - 40, 300))
    c.text(64, 146, f"COMPARE WITH {v['compare']}", 32, colour=ACCENT)
    for i, s in enumerate(v["notes"]):
        c.text(64, 192 + i * 34, s, 26)

    # 1. Clip point.
    steps = CLAMPED_STEPS if clamped else STEPS
    y0, ph = 380, 200
    c.text(40, 330, "1  CLIP POINT", 28, colour=ACCENT)
    c.text(250, 332, ("The last step whose darker square you can still see. All visible = nothing clipped."
                      if clamped else
                      "The last step whose inner square you can still see is where this display clips."), 26)
    c.text(W - 40, 336, "Yellow: this file's metadata", 22, "rt", ACCENT)
    n, gap = len(steps), 12
    pw = ((W - 80 - gap * (n - 1)) // n) // 2 * 2
    xs = [40 + i * (pw + gap) for i in range(n)]
    for x, nits in zip(xs, steps):
        c.grey(x, y0, pw, ph, nits)
        c.grey(x + pw // 4 // 2 * 2, y0 + 50, pw // 2 // 2 * 2, 100, square_nits(nits, clamped))
        c.text(x + pw // 2, y0 + ph + 8, f"{nits}", 24, "mt")
    marks = markers(v, max_cll)
    for nits, what in marks.items():
        x = xs[steps.index(nits)] + pw // 2
        c.triangle(x, y0 + ph + 42)
        c.text(x, y0 + ph + 70, " + ".join(what), 22, "rt" if x > W - 300 else "mt", ACCENT)
    if not marks:
        c.text(W // 2, y0 + ph + 50, "(no metadata: no markers)", 22, "mt", DIM)

    # 2. Mid-tones.
    y1 = 700
    c.text(40, y1, "2  MID-TONES", 28, colour=ACCENT)
    c.text(40, y1 + 36, "Compare between files.", 22)
    c.text(40, y1 + 62, "Dimmer here = mid-tones compressed.", 22)
    for i, nits in enumerate([100, 203]):
        x = 40 + i * 220
        c.grey(x, y1 + 100, 200, 140, nits)
        c.text(x + 100, y1 + 248, f"{nits}" + (" (graphics white)" if nits == 203 else ""), 20, "mt")

    # 3. Colour: inside P3 (should never change), and outside P3 (not in the limited content).
    gx, cw, ch, rgap = 560, 560, 58, 8
    ty = y1 + 52
    c.text(gx, y1, "3  COLOUR", 28, colour=ACCENT)
    c.text(gx + 190, y1 + 2, f"All at {COLOUR_NITS:g} cd/m2", 22, colour=DIM)
    for row in range(3):
        p709, pp3, p2020 = primaries(row)
        white = np.ones(3)
        y = ty + row * (ch + rgap)
        # Inside P3: 85% P3 primary, with a BT.709 primary square. Neither should change between files.
        c.rect(gx, y, cw, ch, at_nits(at_nits(white) * (1 - INSIDE) + at_nits(pp3) * INSIDE))
        c.rect(gx + cw // 2 - 80, y + 12, 160, ch - 24,
               at_nits(at_nits(white) * (1 - INSIDE_SQUARE) + at_nits(p709) * INSIDE_SQUARE))
        if not clamped:
            # Outside P3: P3 primary, with squares halfway to BT.2020 and at BT.2020.
            x = gx + cw + 40
            c.rect(x, y, cw, ch, at_nits(pp3))
            c.rect(x + 60, y + 12, 160, ch - 24, at_nits((pp3 + p2020) / 2))
            c.rect(x + cw - 220, y + 12, 160, ch - 24, at_nits(p2020))
    yl = ty + 3 * (ch + rgap)
    c.text(gx + cw // 2, yl, "INSIDE P3: must look the same in every file", 22, "mt", ACCENT)
    c.text(gx + cw // 2, yl + 26, "(85% to the P3 primary, square 60% to the BT.709 primary)", 20, "mt", DIM)
    if clamped:
        c.text(gx + cw + 40, ty + 60, "No colours outside P3 in the limited content.", 22, "lt", DIM)
    else:
        x = gx + cw + 40
        c.text(x + cw // 2, yl, "OUTSIDE P3: halfway to BT.2020 (left), BT.2020 (right)", 22, "mt")
        c.text(x + cw // 2, yl + 26, "P3 screen: squares fade or vanish. Clear = more than P3, or compressed", 20,
               "mt", DIM)

    c.text(W // 2, H - 34, LEGEND, 20, "mt", DIM)
    return c.signal()


def strip(v, max_cll):
    """A narrow version of the clip point check, for the side by side view."""
    clamped = v["clamped"]
    steps = CLAMPED_STEPS if clamped else STEPS
    c = Canvas(SW, H)
    c.text(SW // 2, 8, v["name"][:2], 56, "mt")
    c.text(SW // 2, 72, v["short"], 22, "mt", ACCENT)
    top, bottom = 112, H - 12
    step_h = ((bottom - top) // len(steps)) // 2 * 2
    marks = markers(v, max_cll)
    for i, nits in enumerate(reversed(steps)):
        y = top + i * step_h
        c.grey(84, y, SW - 96, step_h - 8, nits)
        c.grey(84 + (SW - 96) // 4 // 2 * 2, y + step_h // 4 // 2 * 2, (SW - 96) // 2 // 2 * 2,
               (step_h - 8) // 2 // 2 * 2, square_nits(nits, clamped))
        c.text(76, y + (step_h - 8) // 2, f"{nits}", 22, "rm", ACCENT if nits in marks else TEXT)
    return c.signal()


def to_yuv420p10(sig):
    """BT.2020 non-constant luminance, limited range, 10-bit; chroma averaged over each 2x2 block."""
    h, w = sig.shape[:2]
    y = sig @ LUMA
    cb = (sig[..., 2] - y) / (2 * (1 - KB))
    cr = (sig[..., 0] - y) / (2 * (1 - KR))
    sub = lambda p: p.reshape(h // 2, 2, w // 2, 2).mean((1, 3))
    q = lambda v, off, scale: np.clip(np.round(off + scale * v), 0, 1023).astype("<u2")
    return q(y, 64, 876), q(sub(cb), 512, 896), q(sub(cr), 512, 896)


def light_levels(sig):
    """MaxCLL and MaxFALL (cd/m^2): brightest component, and the frame average of it."""
    peak = pq_eotf(sig).max(-1)
    return int(np.ceil(peak.max())), int(np.ceil(peak.mean()))


def encode(sig, out, v, cll, fall, tmp):
    """HEVC Main 10 in MP4 with the variant's metadata.

    -mastering_display/-content_light (input options) give the frames and the stream the metadata, so libx265
    writes the SEI (in the hvcC extradata and on every keyframe) and the MP4 muxer writes mdcv/clli.
    SEI only: x265's own options, which the muxer does not see. Box only: encode with no metadata, then add it
    on a stream-copy remux, which only sets the stream side data."""
    h, w = sig.shape[:2]
    raw = Path(tmp) / "frame.yuv"
    raw.write_bytes(b"".join(p.tobytes() for p in to_yuv420p10(sig)))
    x265 = "log-level=error:keyint=24:min-keyint=24:repeat-headers=1"
    meta = []
    if v["mdcv"]:
        p, peak, low = v["mdcv"]
        mdcv_s = f"{PRIMS[p]}L({int(peak * 10000)},{int(round(low * 10000))})"
        cll_s = f"{cll},{fall if cll else 0}"
        meta = ["-mastering_display", mdcv_s, "-content_light", cll_s]
        if v["carriage"] == "sei":
            x265 += f":hdr10=1:master-display={mdcv_s}:max-cll={cll_s}"
    enc = Path(tmp) / "encoded.mp4" if v["carriage"] == "box" else out
    ff = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
    subprocess.run([*ff, *(meta if v["carriage"] == "both" else []),
                    "-f", "rawvideo", "-pix_fmt", "yuv420p10le", "-s", f"{w}x{h}", "-r", str(FPS),
                    "-stream_loop", str(FPS * SECONDS - 1), "-i", str(raw),
                    "-vf", f"setparams=range=tv:color_primaries={v.get('container', 'bt2020')}:color_trc=smpte2084:"
                    "colorspace=bt2020nc",
                    "-c:v", "libx265", "-preset", "medium", "-crf", "6", "-x265-params", x265,
                    "-tag:v", "hvc1", "-movflags", "+faststart", str(enc)], check=True)
    if v["carriage"] == "box":
        subprocess.run([*ff, *meta, "-i", str(enc), "-c", "copy", "-tag:v", "hvc1", "-movflags", "+faststart",
                        str(out)], check=True)


def write_png(sig, path, tmp):
    """The chart as a 16-bit PNG, R'G'B' in PQ, tagged BT.2020/PQ (cICP)."""
    h, w = sig.shape[:2]
    raw = Path(tmp) / "chart.rgb"
    raw.write_bytes(np.round(np.clip(sig, 0, 1) * 65535).astype("<u2").tobytes())
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le",
                    "-s", f"{w}x{h}", "-i", str(raw), "-vf",
                    "setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=gbr:range=pc",
                    "-frames:v", "1", str(path)], check=True)


def check(path):
    """What the file carries: MP4 boxes (ffprobe stream side data and the raw bytes), and the SEI."""
    data = path.read_bytes()
    boxes = [b for b in ("mdcv", "clli") if b.encode() in data[:200000] or b.encode() in data[-200000:]]
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream_side_data", "-of", "flat", str(path)], capture_output=True, text=True).stdout
    side = {k: v for k, v in re.findall(r'side_data_list\.side_data\.\d+\.(\w+)="?([^"\n]*)', probe)}
    trace = subprocess.run([FFMPEG, "-v", "debug", "-hide_banner", "-i", str(path), "-frames:v", "1", "-c", "copy",
                            "-bsf:v", "trace_headers", "-f", "null", "-"], capture_output=True, text=True).stderr
    sei = [s for s, pat in (("MDCV", r"Mastering Display Colour Volume"), ("CLL", r"Content Light Level"))
           if re.search(pat, trace)]
    vals = dict(re.findall(r"(max_display_mastering_luminance|max_content_light_level)\s+\S+\s+=\s+(\d+)", trace))
    sei_s = (f"L {int(vals['max_display_mastering_luminance']) / 10000:g} "
             f"CLL {vals.get('max_content_light_level', '-')}") if vals else "-"
    box_s = (f"L {side['max_luminance']} CLL {side.get('max_content', '-')}") if "max_luminance" in side else "-"
    print(f"{str(path.relative_to(OUT)):34} boxes: {'+'.join(boxes) or '-':10} SEI: {'+'.join(sei) or '-':9} "
          f"SEI: {sei_s:18} stream: {box_s}")


INTRO = """
<h2>HDR10 metadata display test</h2>
<p>Each chart says what metadata it carries, which file to compare it with, and what a difference means. Flip
between two files with their keys and <kbd>Space</kbd>, or use <b>Side by side</b> for the narrow strip versions
of the clip point check. Keep the display settings fixed while comparing; look at the display, not a
screenshot.</p>
<p><b>The browser is itself a player.</b> Check the same files in QuickTime, and in the review tools you use.
Side by side only shows differences made by the player or the operating system (e.g. macOS tone mapping each
video separately). A display that tone maps from the HDMI/DisplayPort metadata receives one set for the whole
screen, so for an external HDR monitor or TV use Flip, full screen, or play the files on the TV itself.</p>
<p><b>SDR white</b> (<kbd>W</kbd>) covers the right half of the 100 cd/m<sup>2</sup> mid-tone patch with page
white. In a reference mode that fixes SDR white at 100 cd/m<sup>2</sup> (e.g. the MacBook Pro / Pro Display XDR
"HDR Video (P3-ST 2084)" preset) the two halves should match on 10 and 11: if they do, PQ is shown at its real
level. Elsewhere it shows where the system puts PQ 100 against SDR white.</p>
<ol>
<li>Does the player/display use the mastering display info, which value, and from where? 02&ndash;05, 08, 09</li>
<li>With no metadata, where does it clip? 01, 10</li>
<li>With no metadata, does the player change the picture? 10 (clipping by eye; a smooth change needs a meter or
    the SDR white check)</li>
<li>With metadata, how does it change the result? 02&ndash;06</li>
<li>Content limited to 1000 cd/m<sup>2</sup> and P3 (an OCIO 1000 nit P3 view): the same with no metadata (10)
    and honest metadata (11)? And with wrong metadata (12)?</li>
<li>Do the mastering display primaries change colours inside P3? 02 vs 07</li>
<li>Does it depend on display settings, the player, or large bright areas? Repeat with each.</li>
</ol>
<p>Made by <code>tests/hdr_metadata_display_chart.py</code>.</p>
"""


def main():
    global OUT
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT, help="Output folder")
    parser.add_argument("--check", action="store_true", help="Only report the metadata in existing files")
    parser.add_argument("--png", action="store_true", help="Also write each chart as a 16-bit PNG (PQ, cICP)")
    args = parser.parse_args()
    OUT = args.out
    (OUT / "strips").mkdir(parents=True, exist_ok=True)
    if not args.check:
        with tempfile.TemporaryDirectory() as tmp:
            for v in VARIANTS:
                # The metadata describes the full chart; the strip carries the same.
                max_cll, fall = light_levels(chart(v, 0, 0, 0))
                cll = max_cll if v["cll"] == "real" else v["cll"]
                sig = chart(v, cll, fall, max_cll)
                encode(sig, OUT / f"{v['name']}.mp4", v, cll, fall, tmp)
                encode(strip(v, max_cll), OUT / "strips" / f"{v['name']}.mp4", v, cll, fall, tmp)
                print(f"wrote {v['name']}  (chart MaxCLL {max_cll}, MaxFALL {fall})")
                if args.png:
                    write_png(sig, OUT / f"{v['name']}.png", tmp)
        items = [{"src": f"{v['name']}.mp4", "label": f"{v['name'][:2]} {v['short']}"} for v in VARIANTS]
        strips = [{"src": f"strips/{v['name']}.mp4", "label": f"{v['name'][:2]} {v['short']}"} for v in VARIANTS]
        write_flipbook(OUT / "index.html", "HDR10 metadata display test", items, INTRO, strips, SDR_WHITE)
        print(f"wrote {OUT / 'index.html'}")
    for v in VARIANTS:
        check(OUT / f"{v['name']}.mp4")
        check(OUT / "strips" / f"{v['name']}.mp4")


if __name__ == "__main__":
    main()
