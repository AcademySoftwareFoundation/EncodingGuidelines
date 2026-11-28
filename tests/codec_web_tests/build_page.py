#!/usr/bin/env python3
"""Write web_compatibility.html from the movies made by make_web_tests.py.

For each movie the page gets its RFC 6381 codec string (read from the MP4's sample description), its size and
bit rate (for MediaCapabilities), and the colors it should show (sampled from its source image at the same points
the page samples). Run after make_web_tests.py:
    python3 tests/codec_web_tests/build_page.py
"""
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SOURCES = HERE.parent.parent / "sourceimages"

# Where the page samples each frame, as fractions of width and height. Keep in step with the page's script.
PATCHES = {"gray": (0.5, 0.88), "yellow": (0.08, 0.2), "green": (0.42, 0.2), "red": (0.75, 0.2), "blue": (0.92, 0.2)}

# The Google Apps Script web app URL that receives submitted results (see google_sheet_collector.gs).
# Leave empty to hide the Submit button.
SUBMIT_URL = "https://script.google.com/macros/s/AKfycbx0a7Sw_PghFrpIfH_8VUYp9HKEm1SiXgMTVtIC-eY8LM-XibRefOnWWRpXXSELt2Mw/exec"

CODECS = ["H.264", "HEVC/H.265", "VP9", "AV1"]


def find_box(data, fourcc):
    i = data.find(fourcc)
    if i < 4:
        return None
    size = struct.unpack(">I", data[i - 4:i])[0]
    return data[i + 4:i - 4 + size]


def colr(data):
    box = find_box(data, b"colr")
    if not box or box[:4] != b"nclx":
        return 2, 2, 2, 0
    p, t, m = struct.unpack(">HHH", box[4:10])
    return p, t, m, box[10] >> 7


def codec_string(data):
    """RFC 6381 codecs parameter for the first video track."""
    if (b := find_box(data, b"avcC")) is not None:
        return "avc1.%02X%02X%02X" % (b[1], b[2], b[3])
    if (b := find_box(data, b"hvcC")) is not None:
        space, tier, profile = b[1] >> 6, (b[1] >> 5) & 1, b[1] & 0x1F
        compat = int("{:032b}".format(struct.unpack(">I", b[2:6])[0])[::-1], 2)
        constraints = list(b[6:12])
        while constraints and constraints[-1] == 0:
            constraints.pop()
        s = "hvc1.%s%d.%X.%s%d" % (["", "A", "B", "C"][space], profile, compat, "HL"[tier == 0], b[12])
        return s + "".join(".%02X" % c for c in constraints)
    if (b := find_box(data, b"vpcC")) is not None:
        profile, level, x = b[4], b[5], b[6]
        return "vp09.%02d.%02d.%02d.%02d.%02d.%02d.%02d.%02d" % (
            profile, level, x >> 4, (x >> 1) & 7, b[7], b[8], b[9], x & 1)
    if (b := find_box(data, b"av1C")) is not None:
        profile, level = b[1] >> 5, b[1] & 0x1F
        tier, high, twelve, mono = b[2] >> 7, (b[2] >> 6) & 1, (b[2] >> 5) & 1, (b[2] >> 4) & 1
        subx, suby, pos = (b[2] >> 3) & 1, (b[2] >> 2) & 1, b[2] & 3
        depth = 12 if twelve else 10 if high else 8
        p, t, m, full = colr(data)
        return "av01.%d.%02d%s.%02d.%d.%d%d%d.%02d.%02d.%02d.%d" % (
            profile, level, "MH"[tier], depth, mono, subx, suby, pos, p, t, m, full)
    raise ValueError("no known codec configuration box")


def expected_colors(source):
    im = Image.open(SOURCES / f"{source}.png").convert("RGB")
    w, h = im.size
    return {k: list(im.getpixel((round(w * fx), round(h * fy)))) for k, (fx, fy) in PATCHES.items()}


def source_url(source):
    """Copy a source image next to the page (the page compares edges with it), with a content hash in the URL."""
    data = (SOURCES / f"{source}.png").read_bytes()
    (HERE / f"source-{source}.png").write_bytes(data)
    return "source-%s.png?v=%s" % (source, hashlib.sha1(data).hexdigest()[:10])


def movie(name, codec, depth, layout):
    path = HERE / name
    if not path.exists():
        raise FileNotFoundError(path)
    data = path.read_bytes()
    source = name.split("-")[0]
    # The content hash in the URL makes browsers fetch a re-encoded movie afresh instead of a cached old copy.
    info = {"file": name, "url": "%s?v=%s" % (name, hashlib.sha1(data).hexdigest()[:10]),
            "codec": codec, "depth": depth, "layout": layout,
            "codecs": codec_string(data), "bitrate": len(data) * 8 * 25,
            "expect": expected_colors(source), "source": source_url(source)}
    # No src: the page loads each movie when it tests it, a few at a time (browsers cap active players).
    return ("<td><div class='video-container' data-info='%s'><video preload='auto' muted playsinline></video>"
            "<div class='fallback-text'></div></div><div class='status'>Waiting</div></td>" % json.dumps(info))


def note(text):
    return "<td><div class='video-container'><div class='note'>%s</div></div><div class='status'></div></td>" % text


def table(rows):
    head = "<tr><th></th>" + "".join("<th>%s</th>" % c for c in CODECS) + "</tr>"
    return "<table>\n" + head + "\n" + "\n".join(
        "<tr><th>%s</th>%s</tr>" % (label, "".join(cells)) for label, cells in rows) + "\n</table>\n"


def ycbcr_cells(depth, sub):
    s = sub.replace(":", "")[:3]  # "4:2:0" -> "420"
    stem = f"test{s}-test_{depth}_{s}"
    av1 = "libsvtav1" if s == "420" and depth < 12 else "libaom-av1"
    return [
        note("libx264 has no 12-bit") if depth == 12 else movie(f"{stem}-libx264.mp4", "H.264", depth, sub),
        movie(f"{stem}-libx265.mp4", "HEVC", depth, sub),
        movie(f"{stem}-vp9.mp4", "VP9", depth, sub),
        movie(f"{stem}-{av1}.mp4", "AV1", depth, sub),
    ]


def rgb_cells(depth):
    stem = f"testrgb-test_{depth}_rgb"
    return [
        movie(f"{stem}-libx264rgb.mp4", "H.264", depth, "RGB") if depth == 8 else note("libx264rgb is 8-bit only"),
        movie(f"{stem}-libx265.mp4", "HEVC", depth, "RGB"),
        movie(f"{stem}-vp9.mp4", "VP9", depth, "RGB"),
        movie(f"{stem}-libaom-av1.mp4", "AV1", depth, "RGB"),
    ]


def main():
    sections = []
    for depth in (8, 10, 12):
        sections.append("<h2>%d-bit Y'CbCr</h2>\n" % depth
                        + table([(sub, ycbcr_cells(depth, sub)) for sub in ("4:2:0", "4:2:2", "4:4:4")]))
    sections.append("<h2>RGB (no Y'CbCr conversion)</h2>\n<p>RGB (<code>gbrp</code>, <code>gbrp10le</code>, "
                    "<code>gbrp12le</code>), tagged BT.709 primaries, sRGB transfer, matrix RGB. H.264 uses "
                    "<code>libx264rgb</code>; AV1 uses <code>libaom-av1</code>, since <code>libsvtav1</code> has "
                    "no RGB. See <a href=\"../../RGBEncoding.html\">RGB Encoding</a>.</p>\n"
                    + table([("%d-bit" % d, rgb_cells(d)) for d in (8, 10, 12)]))
    # The source image, drawn by the page next to the movies when it measures the screen.
    ref = (SOURCES / "test444.png").read_bytes()
    (HERE / "reference.png").write_bytes(ref)
    ref_url = "reference.png?v=" + hashlib.sha1(ref).hexdigest()[:10]
    template = (HERE / "web_compatibility_template.html").read_text()
    page = (template.replace("@@SECTIONS@@", "\n".join(sections))
            .replace("@@PATCHES@@", json.dumps(PATCHES))
            .replace("@@SUBMIT_URL@@", json.dumps(SUBMIT_URL))
            .replace("@@REFERENCE@@", ref_url))
    (HERE / "web_compatibility.html").write_text(page)
    print("wrote", HERE / "web_compatibility.html")


if __name__ == "__main__":
    main()
