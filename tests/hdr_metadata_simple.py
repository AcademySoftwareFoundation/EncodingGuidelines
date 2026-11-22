"""
HDR10 metadata display test, simple version: one question per test, each with a single answer.

tests/hdr_metadata_display_chart.py is the full (expert) set; this one keeps only the questions a casual user
needs, each with charts that show one thing large. The page (simple/index.html) gives the question, what to
look at, and what each result means; Space flips between the files of a test.

  Test                                          Files (A / B / C)
  1 Does the player use the mastering peak?     clip-md1000 / clip-md4000
  2 Where does it clip with no metadata?        clip-none / clip-md1000 / clip-md4000
  3 Mastering peak or MaxCLL?                   clip-md4000-cll1000 / clip-md1000-cll4000
  4 Does it use the mastering primaries?        prim-bt709 / prim-bt2020
  5 Where is SDR white in PQ?                   white (PQ patches against the page's white)
  6 Does honest metadata change anything?       lim-none / lim-honest / lim-md4000 (content within 1000 cd/m2, P3)
  7 Do images and video clip the gamut alike?   tests/gamuttests/gamut-tags PNG / HEVC (make_gamut_tag_test.py)
  8 Are colours inside P3 changed?              edge-bt2020 / edge-p3 (the same colours, two containers)

Each chart also gets a reference (refs/*.png): libplacebo with peak detection off, a player that uses all of the
metadata, tone mapped to SDR Display P3. It shows what a difference looks like.

Needs FFmpeg 9.0 or later with libx265 (-mastering_display/-content_light), and libplacebo for the references
(on the maintainer's machine 9.1.dev has both; 9.0.2 has no libplacebo, so its references are skipped):
    rez-env encodingguidelines_env ffmpeg-9.1.dev -- python tests/hdr_metadata_simple.py
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "python"))
import hdr_metadata_display_chart as hdr  # noqa: E402
from hdr_metadata_display_chart import (ACCENT, DIM, FFMPEG, H, TEXT, W, Canvas, at_nits,  # noqa: E402
                                        encode, light_levels, metadata_line, primaries, square_nits)
from questionpage import write_question_page  # noqa: E402

OUT = hdr.OUT / "simple"
CLIP_STEPS = [203, 400, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000]
LIM_STEPS = [100, 203, 300, 400, 500, 600, 700, 800, 900, 1000]
WHITE_STEPS = [50, 80, 100, 125, 160, 203, 250, 320, 400]
P3 = ("P3", 1000, 0.0001)


def header(c, title, look, tag, meta):
    c.text(40, 24, title, 46)
    c.text(40, 86, look, 28)
    c.text(W - 40, 20, tag, 64, "rt", ACCENT)
    c.text(40, 134, "This file:  " + meta, 26, colour=ACCENT)


def steps_row(c, steps, y, ph, darker, mark=None):
    """mark: this file's mastering peak, or {nits: label} for several markers."""
    marks = mark if isinstance(mark, dict) else ({mark: "this file's mastering peak"} if mark else {})
    """Grey steps with an inner square a little brighter (or darker) than the step."""
    n, gap = len(steps), 14
    pw = ((W - 80 - gap * (n - 1)) // n) // 2 * 2
    xs = [40 + i * (pw + gap) for i in range(n)]
    for x, nits in zip(xs, steps):
        c.grey(x, y, pw, ph, nits)
        c.grey(x + pw // 4 // 2 * 2, y + ph // 4 // 2 * 2, pw // 2 // 2 * 2, ph // 2 // 2 * 2,
               square_nits(nits, darker))
        c.text(x + pw // 2, y + ph + 10, f"{nits}", 30, "mt", ACCENT if nits in marks else TEXT)
    for nits, label in marks.items():
        if nits not in steps:
            continue
        x = xs[steps.index(nits)] + pw // 2
        c.triangle(x, y + ph + 52, s=16)
        c.text(x, y + ph + 84, label, 24, "rt" if x > W - 400 else "mt", ACCENT)
    return xs, pw


def clip_chart(v, cll, fall, max_cll):
    c = Canvas()
    tag = {"clip-none": "NONE", "clip-md1000": "1000", "clip-md4000": "4000",
           "clip-md4000-cll1000": "4000 / CLL 1000", "clip-md1000-cll4000": "1000 / CLL 4000"}[v["name"]]
    header(c, "Where does the picture clip?",
           "The last step whose inner square you can still see is where this file clips.", tag,
           metadata_line(v, cll, fall))
    mark = v["mdcv"] and v["mdcv"][1]
    if v["mdcv"] and cll and cll != mark:
        mark = {mark: "mastering peak", cll: "MaxCLL"}
    steps_row(c, CLIP_STEPS, 300, 320, False, mark)
    c.text(40, 820, "Steps in cd/m2 (PQ). The inner square is about 14% brighter than its step.", 26, colour=DIM)
    c.text(40, 860, "Flip between the files of this test: if the clip point moves, the player reads the "
                    "metadata.", 26, colour=DIM)
    return c.signal()


def prim_chart(v, cll, fall, max_cll):
    c = Canvas()
    tag = v["mdcv"][0] + " PRIM."
    header(c, "Does the player use the mastering display primaries?",
           "Flip between the files: does anything in the middle or right column change?", tag,
           metadata_line(v, cll, fall))
    cols = [("CONTROL", "sRGB", "visible on every screen"),
            ("INSIDE P3", "P3", "P3 colour on BT.709: P3 screen, visible"),
            ("OUTSIDE P3", "BT.2020", "BT.2020 colour on P3: P3 screen, clipped")]
    pw, ph, gap, x0 = 580, 250, 30, 40
    for j, (head, _, sub) in enumerate(cols):
        x = x0 + j * (pw + gap)
        c.text(x, 196, head, 28, colour=ACCENT)
        c.text(x, 232, sub, 22, colour=DIM)
    for row in range(2):  # red, green (P3 blue is the BT.709 blue)
        p709, pp3, p2020 = primaries(row)
        y = 274 + row * (ph + 30)
        for j, (head, word, _) in enumerate(cols):
            x = x0 + j * (pw + gap)
            bg, fg = [(at_nits(p709), at_nits(p709, 18)), (at_nits(p709), at_nits(pp3)),
                      (at_nits(pp3), at_nits(p2020))][j]
            c.rect(x, y, pw, ph, bg)
            c.text(x + pw // 2, y + ph // 2, word, 150 if j < 2 else 120, "mm", tuple(np.clip(fg, 0, None)))
    c.text(40, 830, "Identical in both files = the player ignores the mastering display primaries. Any change = it "
                    "uses them,", 26, colour=DIM)
    c.text(40, 864, "e.g. to decide how much to compress colour (libplacebo shows the BT.2020 text, and shifts the "
                    "P3 colours,", 26, colour=DIM)
    c.text(40, 898, "only in the BT.2020 file). Needs a P3 screen: on an sRGB screen the P3 text is invisible in "
                    "every file.", 26, colour=DIM)
    return c.signal()


WHITE_Y, WHITE_PH = 300, 240
WHITE_PW, WHITE_GAP = 180, 24


def white_rects():
    x0 = (W - (len(WHITE_STEPS) * WHITE_PW + (len(WHITE_STEPS) - 1) * WHITE_GAP)) // 2 // 2 * 2
    return [{"x": x0 + i * (WHITE_PW + WHITE_GAP), "y": WHITE_Y + WHITE_PH, "w": WHITE_PW, "h": WHITE_PH}
            for i in range(len(WHITE_STEPS))]


def white_chart(v, cll, fall, max_cll):
    c = Canvas()
    header(c, "Where does the system put SDR white in PQ?",
           "Find the step where the top (PQ) matches the bottom (the page's own white).", "NONE",
           metadata_line(v, cll, fall))
    for r, nits in zip(white_rects(), WHITE_STEPS):
        c.grey(r["x"], WHITE_Y, WHITE_PW, WHITE_PH, nits)
        c.outline((r["x"], r["y"], r["x"] + WHITE_PW - 1, r["y"] + WHITE_PH - 1), DIM, 2)
        c.text(r["x"] + WHITE_PW // 2, r["y"] + WHITE_PH // 2, "page white", 22, "mm", DIM)
        c.text(r["x"] + WHITE_PW // 2, r["y"] + WHITE_PH + 12, f"{nits}", 32, "mt")
    c.text(40, 870, "Top: PQ at the level shown, in cd/m2.  Bottom: the browser page's white (SDR white), drawn by",
           26, colour=DIM)
    c.text(40, 904, "the page over the video. In a player with no page the bottom boxes stay empty.", 26,
           colour=DIM)
    return c.signal()


def lim_chart(v, cll, fall, max_cll):
    c = Canvas()
    tag = {"lim-none": "NONE", "lim-honest": "HONEST", "lim-md4000": "SAYS 4000"}[v["name"]]
    header(c, "Does metadata change content within 1000 cd/m2 and P3?",
           "Compare everything between the files: it should be identical.", tag, metadata_line(v, cll, fall))
    steps_row(c, LIM_STEPS, 230, 240, True, v["mdcv"] and v["mdcv"][1])
    c.text(40, 610, "Steps: the darker inner squares should all be visible (on a display that reaches 1000).", 24,
           colour=DIM)
    # Mid-tones, each next to the page's white.
    y, pw, ph = 700, 160, 190
    c.text(40, 660, "MID-TONES, next to page white", 26, colour=ACCENT)
    for k, nits in enumerate([100, 203]):
        x = 40 + k * (2 * pw + 40)
        c.grey(x, y, pw, ph, nits)
        c.outline((x + pw, y, x + 2 * pw - 1, y + ph - 1), DIM, 2)
        c.text(x + pw // 2, y + ph + 10, f"PQ {nits}", 24, "mt")
        c.text(x + pw + pw // 2, y + ph + 10, "page white", 24, "mt", DIM)
    # Colours inside P3, with a BT.709 square.
    gx, cw, ch = 820, 1060, 58
    c.text(gx, 660, f"COLOURS INSIDE P3, at {hdr.COLOUR_NITS:g} cd/m2", 26, colour=ACCENT)
    white = np.ones(3)
    for row in range(3):
        p709, pp3, _ = primaries(row)
        yy = 700 + row * (ch + 10)
        c.rect(gx, yy, cw, ch, at_nits(at_nits(white) * (1 - hdr.INSIDE) + at_nits(pp3) * hdr.INSIDE))
        c.rect(gx + cw // 2 - 120, yy + 12, 240, ch - 24,
               at_nits(at_nits(white) * (1 - hdr.INSIDE_SQUARE) + at_nits(p709) * hdr.INSIDE_SQUARE))
    return c.signal()


def lim_white():
    y, pw, ph = 700, 160, 190
    return [{"x": 40 + k * (2 * pw + 40) + pw, "y": y, "w": pw, "h": ph} for k in range(2)]


P3_FROM_2020 = np.linalg.inv(hdr.P3_TO_2020)
HUES = [("red", (0,)), ("yellow", (0, 1)), ("green", (1,)), ("cyan", (1, 2)), ("blue", (2,)), ("magenta", (0, 2))]
SATS = [1.0, 0.95, 0.9, 0.8]
EDGE_NITS = 40.0  # saturated blue at 40 cd/m2 needs a component of about 500


def signal_p3(c):
    """Canvas.signal(), but R'G'B' with P3-D65 primaries (the canvas is linear BT.2020)."""
    sig = hdr.pq_oetf(np.clip(c.lin @ P3_FROM_2020.T, 0, 10000))
    for colour, (img, _) in c.layers.items():
        a = (np.asarray(img, dtype=float) / 255)[..., None]
        sig = sig * (1 - a) + hdr.pq_oetf(np.clip(P3_FROM_2020 @ np.array(colour), 0, 10000)) * a
    return sig


def edge_chart(v, cll, fall, max_cll):
    """Colours near the P3 edge, all inside P3; the same picture in a BT.2020 or a P3-D65 container."""
    c = Canvas()
    p3 = v["container"] == "smpte432"
    header(c, "Are colours inside P3 changed by the container?",
           "Flip between the files: the colours should not change at all.",
           "P3 CONTAINER" if p3 else "BT.2020 CONTAINER",
           ("P3-D65" if p3 else "BT.2020") + " primaries.  " + metadata_line(v, cll, fall))
    x0, pw, gap, y0, ph, rg = 200, 404, 20, 230, 96, 12
    white = np.ones(3)
    for j, sat in enumerate(SATS):
        c.text(x0 + j * (pw + gap) + pw // 2, 192, f"{sat:.0%} of the way to P3" + (" (edge)" if sat == 1 else ""),
               24, "mt", ACCENT)
    for row, (name, idx) in enumerate(HUES):
        hue = sum(hdr.P3_TO_2020 @ np.eye(3)[k] for k in idx)
        y = y0 + row * (ph + rg)
        c.text(x0 - 20, y + ph // 2, name, 28, "rm")
        for j, sat in enumerate(SATS):
            x = x0 + j * (pw + gap)
            mix = lambda s: at_nits(at_nits(white, EDGE_NITS) * (1 - s) + at_nits(hue, EDGE_NITS) * s, EDGE_NITS)
            c.rect(x, y, pw, ph, mix(sat))
            c.rect(x + pw // 2 - 80, y + 20, 160, ph - 40, mix(sat - 0.06))
    c.text(40, 900, f"All at {EDGE_NITS:g} cd/m2. The inner squares are 6% less saturated. Nothing here is outside "
                    "P3, so a P3 screen needs no gamut mapping:", 24, colour=DIM)
    c.text(40, 932, "if the BT.2020 file is less saturated than the P3 file, the player compresses colours inside "
                    "P3 to make room for BT.2020.", 24, colour=DIM)
    return signal_p3(c) if p3 else c.signal()


def V(name, draw, mdcv=None, cll=None, label="", container="bt2020"):
    return {"name": name, "draw": draw, "mdcv": mdcv, "cll": cll, "carriage": "both", "label": label,
            "container": container}


VARIANTS = {v["name"]: v for v in [
    V("clip-none", clip_chart, label="no metadata"),
    V("clip-md1000", clip_chart, P3, 1000, "mastering 1000"),
    V("clip-md4000", clip_chart, ("P3", 4000, 0.005), 4000, "mastering 4000"),
    V("clip-md4000-cll1000", clip_chart, ("P3", 4000, 0.005), 1000, "mastering 4000, MaxCLL 1000"),
    V("clip-md1000-cll4000", clip_chart, P3, 4000, "mastering 1000, MaxCLL 4000"),
    V("prim-bt709", prim_chart, ("BT.709", 1000, 0.0001), "real", "BT.709 primaries"),
    V("prim-bt2020", prim_chart, ("BT.2020", 1000, 0.0001), "real", "BT.2020 primaries"),
    V("white", white_chart, label="PQ against page white"),
    V("lim-none", lim_chart, label="no metadata"),
    V("lim-honest", lim_chart, P3, "real", "honest (P3, 1000, real MaxCLL)"),
    V("lim-md4000", lim_chart, ("P3", 4000, 0.005), 4000, "wrong (says 4000)"),
    V("edge-bt2020", edge_chart, P3, "real", "BT.2020 container"),
    V("edge-p3", edge_chart, P3, "real", "P3-D65 container", "smpte432"),
]}

GAMUT = "../../gamuttests/gamut-tags/"
TESTS = [
    dict(title="Mastering peak", files=["clip-md1000", "clip-md4000"],
         question="Does the player or display use the mastering display peak luminance?",
         look="The last step whose inner square you can see, in A and in B.",
         outcomes=[["Clip point moves to the right in B", "Yes, it uses the mastering peak"],
                   ["Same clip point in A and B", "No, it ignores it (or the display really reaches 5000)"],
                   ["B has dimmer steps overall", "Yes, and it compresses the whole range to make room"]],
         note="Depends on the brightness setting: on a MacBook Pro below full brightness the steps carried on "
              "past 1000 in A; at full brightness A clipped at 1000. Note the setting with the result. "
              "Both files also set MaxCLL to the same value; the expert page separates the two."),
    dict(title="Default with no metadata", files=["clip-none", "clip-md1000", "clip-md4000"],
         question="With no metadata, what peak does the player assume?",
         look="Which of B or C file A (no metadata) looks like.",
         outcomes=[["A looks like B", "It assumes 1000 cd/m<sup>2</sup>"],
                   ["A looks like C", "It assumes 4000 cd/m<sup>2</sup>"],
                   ["Every step visible in A", "It assumes 10000 (libplacebo does this) or its own peak"],
                   ["Something else", "It has its own rule: note the last visible step"]],
         note="Repeat at full brightness and at the brightness you work at: the clip point can move."),
    dict(title="Mastering peak or MaxCLL?", files=["clip-md4000-cll1000", "clip-md1000-cll4000"],
         question="When the mastering display peak and MaxCLL disagree, which one does the player use?",
         look="The clip point, against what test 1 gave for 1000 and 4000.",
         outcomes=[["A clips like 1000, B compresses like 4000", "It uses MaxCLL"],
                   ["A compresses like 4000, B clips like 1000", "It uses the mastering peak"],
                   ["Both compress like 4000", "It uses the higher of the two"],
                   ["Both clip like 1000", "It uses the lower of the two"]],
         note="Do test 1 first, at the same brightness. MaxCLL is optional in HDR10 (0 = unknown); this shows "
              "whether setting it to the content's real peak can avoid compression."),
    dict(title="Mastering primaries", files=["prim-bt709", "prim-bt2020"],
         question="Does the player change colours according to the mastering display primaries?",
         look="The middle column (P3 text on BT.709) and the right column (BT.2020 text on P3).",
         outcomes=[["Both files look the same", "No, it ignores the primaries"],
                   ["Right text appears in B, and the P3 colours shift", "Yes: it compresses colour more when the "
                    "mastering gamut is wider (libplacebo does this)"],
                   ["Middle text vanishes or fades in A", "Yes: it clips to the mastering gamut"],
                   ["Right text visible in both", "It ignores the primaries but compresses out-of-gamut colour"],
                   ["Control text not visible", "Screen or player problem: stop here"]],
         note="Needs a P3 (or wider) screen. On an sRGB screen the middle text is invisible in both."),
    dict(title="SDR white in PQ", files=["white"],
         question="At what PQ level does the system put SDR white (the page's white)?",
         look="The step where the top half matches the page white below it.",
         outcomes=[["Matches at 100", "PQ shown at its true level, SDR white = 100 cd/m<sup>2</sup> "
                                      "(e.g. XDR \"HDR Video (P3-ST 2084)\" mode)"],
                   ["Matches at 203", "SDR white = 203, the BT.2408 graphics white"],
                   ["Another step", "SDR white is set elsewhere, often by the brightness slider"]],
         note="Change the brightness slider and repeat: if the match moves, PQ is not shown at an absolute "
              "level. No reference: libplacebo puts SDR white at 203 by definition."),
    dict(title="Honest metadata", files=["lim-none", "lim-honest", "lim-md4000"],
         question="Content already within 1000 cd/m<sup>2</sup> and P3 (e.g. an OCIO 1000 nit P3 view): does the "
                  "metadata change it?",
         look="Everything: steps, mid-tones against page white, colours.",
         outcomes=[["A and B identical", "Honest metadata changes nothing: safe"],
                   ["A and B differ", "The player alters the picture even with correct metadata"],
                   ["C dimmer or flatter than B", "Wrong metadata changes the picture: it must match the content"]]),
    dict(title="Image vs video gamut", files=[],
         items=[{"src": GAMUT + "bt2020-png-icc-cicp.png", "label": "PNG (ICC + cICP)"},
                {"src": GAMUT + "bt2020-mp4-hevc.mp4", "label": "HEVC MP4"}],
         question="Do images and video handle colour outside the screen's gamut the same way?",
         look="The BT.2020 text on the P3 primary, and the P3 text on the BT.709 primary.",
         outcomes=[["Text visible in one, not the other", "They differ: one clips, one compresses"],
                   ["Same in both", "Images and video agree"]],
         note="SDR (sRGB curve), BT.2020 container. More variants on the gamut tag page."),
    dict(title="Colours inside P3", files=["edge-bt2020", "edge-p3"],
         question="Does the player change colours that are inside P3 when they come in a BT.2020 file?",
         look="The inner squares in the 100% column (a 6% step only shows near the edge), and the saturation of "
              "each patch.",
         outcomes=[["A and B identical", "Colours inside P3 are untouched: a BT.2020 container is safe"],
                   ["Edge-column squares visible in B, not in A", "Colours near the P3 edge are compressed in a "
                    "BT.2020 file (what a Mac showed)"],
                   ["A less saturated overall", "It compresses well inside P3 to make room for BT.2020"],
                   ["Edge squares missing in both", "The screen falls a little short of P3 there (not the file)"]],
         note="Run it in the same setup as the others (on a Mac, the HDR Video preset). Both files carry honest "
              "metadata: P3 mastering display, 1000 cd/m<sup>2</sup>."),
]

INTRO = """
<p>Each test answers one question. <b>Results depend on the display brightness</b>: on a Mac, test at full
brightness (or in a reference preset such as "HDR Video (P3-ST 2084)", which fixes it) and note the setting. Keep
the display settings fixed (macOS: automatic brightness off, slider left
alone; TV: dynamic tone mapping off) and look at the screen itself, not a screenshot: tone mapping often happens
after the screenshot is taken.</p>
<p>The browser is a player too: repeat in QuickTime and your review tools. An external HDR monitor or TV that tone
maps from the HDMI/DisplayPort metadata gets one set for the whole screen, so use full screen there.</p>
<p>Made by <code>tests/hdr_metadata_simple.py</code>. The full set, with which copy of the metadata is read and
how mastering peak and MaxCLL interact, is on the expert page.</p>
"""
FOOTER = ('<p class="note"><a href="../index.html" style="color:#99f">Expert page (12 charts)</a> &middot; '
          '<a href="../../gamuttests/gamut-tags/index.html" style="color:#99f">Gamut tag page</a></p>')


def has_libplacebo():
    out = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    return " libplacebo " in out


def reference(src, out):
    """libplacebo, peak detection off: tone mapped from the file's own metadata to SDR Display P3."""
    vf = ("libplacebo=peak_detect=0:color_primaries=smpte432:color_trc=iec61966-2-1:colorspace=gbr:range=pc:"
          "format=rgb48le")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-frames:v", "1",
                    "-vf", vf, str(out)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT, help="Output folder")
    parser.add_argument("--page-only", action="store_true", help="Only rewrite index.html")
    parser.add_argument("names", nargs="*", help="Only encode these files (e.g. prim-bt709)")
    args = parser.parse_args()
    (args.out / "refs").mkdir(parents=True, exist_ok=True)
    refs = has_libplacebo()
    if not refs:
        print(f"{FFMPEG} has no libplacebo: no references")
    if not args.page_only:
        with tempfile.TemporaryDirectory() as tmp:
            for v in VARIANTS.values():
                if args.names and v["name"] not in args.names:
                    continue
                max_cll, fall = light_levels(v["draw"](v, 0, 0, 0))
                cll = max_cll if v["cll"] == "real" else v["cll"]
                out = args.out / f"{v['name']}.mp4"
                encode(v["draw"](v, cll, fall, max_cll), out, v, cll, fall, tmp)
                if refs:
                    reference(out, args.out / "refs" / f"{v['name']}.png")
                print(f"wrote {v['name']}  (MaxCLL {max_cll}, MaxFALL {fall})")
    white = {"white": white_rects(), "lim-none": lim_white(), "lim-honest": lim_white(), "lim-md4000": lim_white()}
    tests = []
    for t in TESTS:
        items = t.get("items") or [
            {"src": f"{n}.mp4", "label": VARIANTS[n]["label"], "white": white.get(n, []),
             "ref": f"refs/{n}.png" if (args.out / "refs" / f"{n}.png").exists() and n != "white" else None}
            for n in t["files"]]
        tests.append({k: t[k] for k in ("title", "question", "look", "outcomes")} | {"note": t.get("note", ""),
                                                                                   "items": items})
    write_question_page(args.out / "index.html", "HDR display tests", tests, INTRO, FOOTER)
    print(f"wrote {args.out / 'index.html'}")


if __name__ == "__main__":
    main()
