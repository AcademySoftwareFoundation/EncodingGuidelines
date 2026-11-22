"""
Gamut tag test: is a wide gamut picture shown the same whether its colour space is declared by an ICC profile,
a PNG cICP chunk, both, or the video tags of an MP4? And how much of P3 / BT.2020 does the screen show?

The same picture (sRGB transfer, BT.2020 or P3-D65 primaries) is written several ways:

  png-untagged      no colour chunks: the viewer assumes sRGB, so the colours are wrong (the control)
  png-icc           ICC profile (iCCP) only
  png-cicp          cICP chunk only
  png-icc-cicp      both, agreeing
  png-conflict      an sRGB ICC profile but a cICP for the real primaries: shows which one the viewer obeys
                    (PNG 3rd edition: cICP wins)
  png-oiio-default  ICC + cICP, plus the sRGB/gAMA/cHRM chunks oiiotool adds by default (see below)
  mp4-h264          H.264 8-bit 4:2:0, with the primaries/transfer/matrix in the VUI (and MP4 colr)
  mp4-hevc          HEVC Main 10 4:2:0, the same

The PNG chunks are written with oiiotool (--iccread, --cicp). oiiotool reads an untagged PNG as
srgb_rec709_scene and, for that colour space, also writes sRGB, gAMA and cHRM chunks, even next to iCCP (which
the PNG spec does not allow) or cICP. Setting oiio:ColorSpace to the real colour space (srgb_p3d65_display,
srgb_rec2020_display) stops it (OpenImageIO 3.1.12). The ICC profiles are made here (matrix/TRC, sRGB
curve, D65 white adapted to D50 with Bradford), because the ones in ICC/ use gamma 2.4 or 2.6 and would not match
a cICP with transfer 13 (sRGB).

In each row the text is a slightly more saturated colour than its background, both at full strength in their own
gamut: "P3" is the P3 primary on the BT.709 primary, "BT.2020" the BT.2020 primary on the P3 primary. A screen
that clips at its gamut edge shows them as one colour, so you see the names of the gamuts the screen can show.
Faint text means the viewer compresses the gamut rather than clipping. The control text ("sRGB", a darker shade of the
BT.709 primary) is always visible. P3 and BT.709 share the same blue, so the blue row has no P3 test.

Flip between the files on index.html: tagged versions that look different from each other mean one path handles
colour differently; a tagged version that looks like png-untagged means its tags were ignored.

    rez-env encodingguidelines_env ffmpeg-9.0.2 -- python tests/gamuttests/make_gamut_tag_test.py
"""
import argparse
import datetime
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
from flipbook import write_flipbook  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "gamut-tags"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
OIIOTOOL = os.getenv("OIIOTOOL_BIN", "oiiotool")
W, H = 1920, 1080

XY = {"BT.709": [(0.640, 0.330), (0.300, 0.600), (0.150, 0.060)],
      "P3-D65": [(0.680, 0.320), (0.265, 0.690), (0.150, 0.060)],
      "BT.2020": [(0.708, 0.292), (0.170, 0.797), (0.131, 0.046)]}
D65 = (0.3127, 0.3290)
D50_XYZ = np.array([0.9642, 1.0, 0.8249])
BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
# Container: cICP primaries code, FFmpeg names (primaries, matrix), the matrix's Kr/Kb.
CONTAINERS = {"BT.2020": dict(cicp=9, prim="bt2020", matrix="bt2020nc", kr=0.2627, kb=0.0593,
                              oiio="srgb_rec2020_display"),
              "P3-D65": dict(cicp=12, prim="smpte432", matrix="bt709", kr=0.2126, kb=0.0722,
                             oiio="srgb_p3d65_display")}


def xyz(xy):
    x, y = xy
    return np.array([x / y, 1.0, (1 - x - y) / y])


def rgb_to_xyz(name):
    p = np.array([xyz(c) for c in XY[name]]).T
    return p * np.linalg.solve(p, xyz(D65))


def convert(src, dst):
    """Linear RGB in src primaries to linear RGB in dst primaries (same D65 white)."""
    return np.linalg.solve(rgb_to_xyz(dst), rgb_to_xyz(src))


def srgb_oetf(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)


# --- ICC profiles -------------------------------------------------------------------------------------------

def s15(v):
    return struct.pack(">i", int(round(v * 65536)))


def mluc(text):
    s = text.encode("utf-16-be")
    return b"mluc" + bytes(4) + struct.pack(">II", 1, 12) + b"enUS" + struct.pack(">II", len(s), 28) + s


def icc_profile(name, description):
    """ICC v4 display profile: the named primaries, D65 white, sRGB transfer curve."""
    adapt = np.linalg.solve(BRADFORD, np.diag((BRADFORD @ D50_XYZ) / (BRADFORD @ xyz(D65))) @ BRADFORD)
    colorants = adapt @ rgb_to_xyz(name)
    xyz_tag = lambda v: b"XYZ " + bytes(4) + b"".join(s15(c) for c in v)
    trc = b"para" + bytes(4) + struct.pack(">HH", 3, 0) + b"".join(
        s15(c) for c in (2.4, 1 / 1.055, 0.055 / 1.055, 1 / 12.92, 0.04045))
    tags = [(b"desc", mluc(description)), (b"cprt", mluc("No copyright, use freely")),
            (b"wtpt", xyz_tag(D50_XYZ)), (b"chad", b"sf32" + bytes(4) + b"".join(s15(c) for c in adapt.flatten())),
            (b"rXYZ", xyz_tag(colorants[:, 0])), (b"gXYZ", xyz_tag(colorants[:, 1])),
            (b"bXYZ", xyz_tag(colorants[:, 2])), (b"rTRC", trc), (b"gTRC", trc), (b"bTRC", trc)]
    offset = 128 + 4 + 12 * len(tags)
    table, data, seen = b"", b"", {}
    for sig, body in tags:
        if body not in seen:  # the three TRCs share one copy
            seen[body] = offset + len(data)
            data += body + bytes(-len(body) % 4)
        table += sig + struct.pack(">II", seen[body], len(body))
    size = offset + len(data)
    now = datetime.datetime(2026, 1, 1)
    header = (struct.pack(">I", size) + bytes(4) + struct.pack(">I", 0x04400000) + b"mntrRGB XYZ "
              + struct.pack(">6H", now.year, now.month, now.day, 0, 0, 0) + b"acsp" + bytes(4) + bytes(4)
              + bytes(8) + bytes(8) + bytes(4) + b"".join(s15(c) for c in D50_XYZ) + bytes(4) + bytes(16)
              + bytes(28))
    profile = bytearray(header + struct.pack(">I", len(tags)) + table + data)
    assert len(header) == 128
    # Profile ID: MD5 of the profile with the flags, intent and ID fields zeroed (they already are).
    profile[84:100] = hashlib.md5(bytes(profile)).digest()
    return bytes(profile)


# --- The chart ------------------------------------------------------------------------------------------------

def chart(container, label, sub):
    """Linear RGB in the container's primaries, with the text layer; returns R'G'B' (sRGB curve)."""
    lin = np.full((H, W, 3), 0.0)
    to_c = lambda gamut, rgb: convert(gamut, container) @ np.asarray(rgb, float)
    grey = to_c("BT.709", (0.03, 0.03, 0.03))
    lin[:] = grey
    layers = []  # (mask image, linear colour)

    def text(x, y, s, size, colour, anchor="lt"):
        img = Image.new("L", (W, H), 0)
        ImageDraw.Draw(img).text((x, y), s, fill=255, font=ImageFont.load_default(size=size), anchor=anchor)
        layers.append((img, np.asarray(colour, float)))

    white = to_c("BT.709", (0.8, 0.8, 0.8))
    dim = to_c("BT.709", (0.3, 0.3, 0.3))
    text(40, 24, label, 56, white)
    text(40, 96, sub, 28, dim)
    text(W - 40, 30, f"container: {container} primaries, sRGB transfer", 28, dim, "rt")

    pw = 560
    xs = [40, 40 + pw + 40, 40 + 2 * (pw + 40)]
    text(xs[0] + pw // 2, 170, "control: always visible", 26, dim, "mt")
    text(xs[1] + pw // 2, 170, "\"P3\" visible = screen shows more than sRGB", 26, dim, "mt")
    if container == "BT.2020":
        text(xs[2] + pw // 2, 170, "\"BT.2020\" visible = more than P3", 26, dim, "mt")
    for row in range(3):
        e = np.eye(3)[row]
        y, ph = 220 + row * 250, 220
        p709, pp3, p2020 = to_c("BT.709", e), to_c("P3-D65", e), to_c("BT.2020", e) if container == "BT.2020" else None
        lin[y:y + ph, xs[0]:xs[0] + pw] = p709
        text(xs[0] + pw // 2, y + ph // 2, "sRGB", 110, p709 * 0.25, "mm")
        lin[y:y + ph, xs[1]:xs[1] + pw] = p709
        if row < 2:
            text(xs[1] + pw // 2, y + ph // 2, "P3", 150, pp3, "mm")
        else:
            text(xs[1] + pw // 2, y + ph // 2, "(P3 blue = sRGB blue)", 30, dim, "mm")
        if p2020 is not None:
            lin[y:y + ph, xs[2]:xs[2] + pw] = pp3
            text(xs[2] + pw // 2, y + ph // 2, "BT.2020", 110, p2020, "mm")
    text(W // 2, H - 40, "Flip between the files: tagged versions should all look the same. One that looks like "
         "png-untagged had its tags ignored.", 24, dim, "mt")
    sig = srgb_oetf(np.clip(lin, 0, 1))
    for img, colour in layers:
        a = (np.asarray(img, dtype=float) / 255)[..., None]
        sig = sig * (1 - a) + srgb_oetf(np.clip(colour, 0, 1)) * a
    return sig


def write_raw_png(sig, path, tmp):
    """16-bit PNG with no colour chunks (FFmpeg writes none for an untagged frame)."""
    raw = Path(tmp) / "chart.rgb"
    raw.write_bytes(np.round(np.clip(sig, 0, 1) * 65535).astype("<u2").tobytes())
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le",
                    "-s", f"{W}x{H}", "-i", str(raw), "-frames:v", "1", str(path)], check=True)


def png_chunks(path):
    data = Path(path).read_bytes()[8:]
    out = []
    while data:
        n = struct.unpack(">I", data[:4])[0]
        kind = data[4:8].decode()
        body = data[8:8 + n]
        if kind == "cICP":
            kind += "(" + ",".join(str(b) for b in body) + ")"
        if kind not in ("IDAT", "IEND", "IHDR"):
            out.append(kind)
        data = data[12 + n:]
    return out


def encode_video(sig, container, codec, path, tmp):
    """Y'CbCr made here (exact matrix, limited range, chroma averaged per 2x2), tagged with setparams."""
    c = CONTAINERS[container]
    kr, kb = c["kr"], c["kb"]
    y = sig @ np.array([kr, 1 - kr - kb, kb])
    cb = (sig[..., 2] - y) / (2 * (1 - kb))
    cr = (sig[..., 0] - y) / (2 * (1 - kr))
    bits = 10 if codec == "hevc" else 8
    s = 2 ** (bits - 8)
    sub = lambda p: p.reshape(H // 2, 2, W // 2, 2).mean((1, 3))
    q = lambda v, off, scale: np.clip(np.round((off + scale * v) * s), 0, 2 ** bits - 1)
    planes = [q(y, 16, 219), q(sub(cb), 128, 224), q(sub(cr), 128, 224)]
    raw = Path(tmp) / "frame.yuv"
    raw.write_bytes(b"".join(p.astype("<u2" if bits > 8 else "u1").tobytes() for p in planes))
    pix = "yuv420p10le" if bits > 8 else "yuv420p"
    enc = (["-c:v", "libx265", "-crf", "4", "-tag:v", "hvc1", "-x265-params", "log-level=error"] if codec == "hevc"
           else ["-c:v", "libx264", "-crf", "4", "-profile:v", "high"])
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pix,
                    "-s", f"{W}x{H}", "-r", "24", "-stream_loop", "119", "-i", str(raw),
                    "-vf", f"setparams=range=tv:color_primaries={c['prim']}:color_trc=iec61966-2-1:"
                           f"colorspace={c['matrix']}", *enc, "-movflags", "+faststart", str(path)], check=True)


VARIANTS = [
    ("png-untagged", "PNG, no colour chunks", "Control: shown as sRGB, so the colours are wrong."),
    ("png-icc", "PNG, ICC profile", "iCCP only."),
    ("png-cicp", "PNG, cICP", "cICP only."),
    ("png-icc-cicp", "PNG, ICC profile + cICP", "Both, agreeing."),
    ("png-conflict", "PNG, sRGB ICC + real cICP", "Looks like png-cicp = the viewer obeys cICP (correct). "
                                                  "Like png-untagged = it obeys the ICC profile."),
    ("png-oiio-default", "PNG, ICC + cICP + sRGB/gAMA/cHRM chunks",
     "What oiiotool writes without oiio:ColorSpace. Looks like png-icc-cicp = the extra chunks are ignored."),
    ("mp4-h264", "MP4, H.264 8-bit", "Primaries, transfer and matrix in the VUI and MP4 colr."),
    ("mp4-hevc", "MP4, HEVC 10-bit", "Primaries, transfer and matrix in the VUI and MP4 colr."),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.out
    (out / "icc").mkdir(parents=True, exist_ok=True)
    profiles = {"BT.709": "sRGB (BT.709 primaries, sRGB curve)", "P3-D65": "P3-D65 (sRGB curve, = Display P3)",
                "BT.2020": "BT.2020 primaries, sRGB curve"}
    icc = {}
    for name, desc in profiles.items():
        icc[name] = out / "icc" / f"{name}-srgb-curve.icc"
        icc[name].write_bytes(icc_profile(name, desc))
    items = []
    with tempfile.TemporaryDirectory() as tmp:
        for container, short in (("BT.2020", "bt2020"), ("P3-D65", "p3")):
            cicp = f"{CONTAINERS[container]['cicp']},13,0,1"
            for key, label, sub in VARIANTS:
                sig = chart(container, f"{container}:  {label}", sub)
                ext = ".mp4" if key.startswith("mp4") else ".png"
                path = out / f"{short}-{key}{ext}"
                if key.startswith("mp4"):
                    encode_video(sig, container, key[4:], path, tmp)
                else:
                    raw = Path(tmp) / "raw.png"
                    write_raw_png(sig, raw, tmp)
                    opts = {"png-untagged": [], "png-icc": ["--iccread", str(icc[container])],
                            "png-cicp": ["--cicp", cicp],
                            "png-icc-cicp": ["--iccread", str(icc[container]), "--cicp", cicp],
                            "png-conflict": ["--iccread", str(icc["BT.709"]), "--cicp", cicp],
                            "png-oiio-default": ["--iccread", str(icc[container]), "--cicp", cicp]}[key]
                    if key != "png-oiio-default":
                        opts += ["--attrib", "oiio:ColorSpace", CONTAINERS[container]["oiio"]]
                    if key != "png-untagged":
                        subprocess.run([OIIOTOOL, str(raw), *opts, "-o", str(path)], check=True)
                    else:
                        raw.replace(path)
                    print(f"{path.name:28} chunks: {' '.join(png_chunks(path)) or '-'}")
                items.append({"src": path.name, "label": f"{short} {key}"})
    intro = ("<h2>Gamut tag test</h2><p>The same picture, with its colour space declared different ways. "
             "Flip between them (keys, <kbd>Space</kbd> for the previous): tagged versions should look the same; "
             "one that looks like <i>png-untagged</i> had its tags ignored. Within a picture, the names you can "
             "read are the gamuts the screen shows (\"P3\": more than sRGB; \"BT.2020\": more than P3); faint "
             "text means the viewer compresses rather than clips. The page opens side by side; <b>Flip</b> (or a "
             "file's key) compares them one at a time, full size."
             "</p><p>Made by <code>tests/gamuttests/make_gamut_tag_test.py</code>.</p>")
    write_flipbook(out / "index.html", "Gamut tag test", items, intro, mode="grid")
    print(f"wrote {out / 'index.html'}")


if __name__ == "__main__":
    main()
