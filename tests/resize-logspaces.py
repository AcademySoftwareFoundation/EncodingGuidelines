"""
Which log space, and which lanczos, for shrinking scene-linear OpenEXRs (the "Which log space and which lanczos"
section of Resizing.md).

Each ACES2065-1 source is shrunk by 4 and viewed through OCIO's ACES 2.0 SDR view for sRGB, then compared with a
reference that averages each 4x4 block in scene-linear light and applies the same view, as tests/resize-test.py does.
The printed tables give the brightness (mean signed difference, negative is too dark) and the largest errors (99th
percentile of the absolute difference), in 8-bit code values. For Sparks they are measured on the 512x270 part with
the most highlights, as on the resize-hdr test page.

  1. lanczos3 in scene-linear and in several log encodings: ACEScct and camera logs, each in its own gamut. For each
     log, the lowest value after the conversion, the share of pixels with a negative channel, and the number of output
     pixels that become infinite or NaN when converted back to linear (lanczos overshoots very negative log values,
     which come from colors outside the log's gamut).
  2. oiiotool's highlightcomp in different linear gamuts: its curve is applied to each channel, so the result depends
     on the primaries.
  3. lanczos with 2, 3 and 4 lobes (zscale's param_a), in scene-linear, ACEScct and Log3G10/REDWideGamutRGB. Nuke names
     lanczos by its full width: Lanczos4 has 2 lobes and Lanczos6 has 3, the lanczos3 of oiiotool and zscale.
  4. If Nuke's Reformat results from tests/resize-nuke.py are present (tests/resize-compare/nuke/, not committed), how
     closely zscale and oiiotool match Nuke's Lanczos4 and Lanczos6 on Sparks.

Needs the OpenImageIO Python bindings (with OCIO 2.2 or later, for the built-in studio config, which has the camera
log spaces) and ffmpeg with zscale on the PATH. The OpenEXR images are read from ../../openexr-images (set
OPENEXR_IMAGES); the Sparks EXR comes from enctests/sources/hdr_sources/download_media.sh. Run from tests/:

    python resize-logspaces.py
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import OpenImageIO as oiio
from OpenImageIO import ImageBufAlgo as IBA

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "python"))
from resizefootprint import area_resize  # noqa: E402

CONFIG = "ocio://studio-config-latest"
DISPLAY, VIEW = "sRGB - Display", "ACES 2.0 - SDR 100 nits (Rec.709)"
OPENEXR_IMAGES = os.environ.get("OPENEXR_IMAGES", os.path.join(HERE, "../../openexr-images"))
SPARKS = os.path.join(HERE, "../enctests/sources/hdr_sources/sparks/SPARKS_ACES_06100.exr")
NUKE = os.path.join(HERE, "resize-compare/nuke")
LOGS = ["ACEScct", "Log3G10 REDWideGamutRGB", "ARRI LogC4", "ARRI LogC3 (EI800)", "S-Log3 S-Gamut3",
        "DaVinci Intermediate WideGamut"]
LINEARS = ["ACES2065-1", "ACEScg", "Linear REDWideGamutRGB", "Linear ARRI Wide Gamut 4"]
TMP = tempfile.mkdtemp()


def zone_plate(w=1920, h=1080, lo=0.05, hi=0.5):
    """resize-test.py's zone plate, as scene-linear values between lo and hi (no highlights at all)."""
    y, x = np.mgrid[0:h, 0:w].astype(float)
    r2 = (x - (w - 1) / 2) ** 2 + (y - (h - 1) / 2) ** 2
    v = 0.5 + 0.5 * np.cos(np.pi * 0.5 * r2 / np.hypot(w / 2, h / 2))
    return np.repeat((lo + (hi - lo) * v)[..., None], 3, 2)


def image(a):
    return oiio.ImageBuf(np.ascontiguousarray(a, dtype=np.float32))


def pixels(b):
    if b.has_error:
        sys.exit(b.geterror())
    return np.array(b.get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)


def convert(b, frm, to):
    return b if frm == to else IBA.colorconvert(b, frm, to, colorconfig=CONFIG)


def shown(b, space="ACES2065-1"):
    """The view transform, from the given space, as display values clipped to 0-1."""
    return np.clip(pixels(IBA.ociodisplay(b, DISPLAY, VIEW, fromspace=space, colorconfig=CONFIG)), 0, 1)


def oiio_lanczos3(b, w, h):
    return IBA.resize(b, "lanczos3", roi=oiio.ROI(0, w, 0, h, 0, 1, 0, 3))


def zscale_lanczos(b, w, h, lobes):
    src = os.path.join(TMP, "in.exr")
    b.write(src, "float")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf",
                          f"zscale=w={w}:h={h}:filter=lanczos:param_a={lobes},format=gbrpf32le",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    g, b_, r = np.frombuffer(raw, "<f4").reshape(3, h, w)
    return image(np.stack([r, g, b_], -1))


def brightest_window(lin, w, h):
    """(x, y) of the w x h window (on an 8-pixel grid) holding the most scene-linear values above 1."""
    over = np.pad((lin.max(-1) > 1).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    best, pos = -1, (0, 0)
    for y in range(0, lin.shape[0] - h + 1, 8):
        for x in range(0, lin.shape[1] - w + 1, 8):
            n = over[y + h, x + w] - over[y, x + w] - over[y + h, x] + over[y, x]
            if n > best:
                best, pos = n, (x, y)
    return pos


def sources():
    exrs = [("Sparks", SPARKS, (512, 270)),
            ("BrightRings", os.path.join(OPENEXR_IMAGES, "TestImages/BrightRings.exr"), None),
            ("Desk", os.path.join(OPENEXR_IMAGES, "ScanLines/Desk.exr"), None)]
    for name, path, window in exrs:
        if not os.path.exists(path):
            print(f"{path} not found: leaving out {name}", file=sys.stderr)
            continue
        lin = pixels(oiio.ImageBuf(path))
        yield name, lin[:lin.shape[0] // 4 * 4], window      # Desk's 874 rows: cut to a multiple of 4
    yield "Zone plate", zone_plate(), None


def table(title, rows, names, results):
    print(f"\n{title}\n")
    print("| Resize | " + " | ".join(f"{n}: brightness | {n}: largest" for n in names) + " |")
    print("| :--- |" + " ---: |" * (2 * len(names)))
    for row in rows:
        print(f"| {row} | " + " | ".join(
            "{:+.1f} | {:.0f}".format(*results[(row, n)]) if (row, n) in results else "| " for n in names) + " |")


def main():
    lanczos = {"lanczos3, scene-linear": ("ACES2065-1", "oiio")}
    lanczos.update({f"lanczos3, {s}": (s, "oiio") for s in LOGS})
    highlightcomp = {f"lanczos3 with highlightcomp, in {s}": s for s in LINEARS}
    lobes = {f"{n} lobes{nk}, {s}": (s, n) for s in ("ACES2065-1", "ACEScct", "Log3G10 REDWideGamutRGB")
             for n, nk in ((2, " (Nuke's Lanczos4)"), (3, " (Nuke's Lanczos6)"), (4, ""))}
    results, gamut, names = {}, {}, []
    for name, lin, window in sources():
        names.append(name)
        w, h = lin.shape[1] // 4, lin.shape[0] // 4
        block = area_resize(lin, w, h)
        reference = shown(image(block))
        x, y = brightest_window(block, *window) if window else (0, 0)
        cw, ch = window if window else (w, h)

        def measure(row, result):
            d = (result - reference)[y:y + ch, x:x + cw] * 255
            results[(row, name)] = (d.mean(), np.percentile(np.abs(d), 99))

        src = image(lin)
        for row, (space, _) in lanczos.items():
            enc = convert(src, "ACES2065-1", space)
            out = oiio_lanczos3(enc, w, h)
            if space != "ACES2065-1":
                e = pixels(enc)
                back = pixels(convert(out, space, "ACES2065-1"))
                gamut[(space, name)] = (e.min(), 100 * (e < 0).any(-1).mean(), int((~np.isfinite(back)).any(-1).sum()))
            measure(row, shown(out, space))
        for row, space in highlightcomp.items():
            out = IBA.rangeexpand(oiio_lanczos3(IBA.rangecompress(convert(src, "ACES2065-1", space)), w, h))
            measure(row, shown(convert(out, space, "ACES2065-1")))
        for row, (space, n) in lobes.items():
            measure(row, shown(zscale_lanczos(convert(src, "ACES2065-1", space), w, h, n), space))
        print(f"done {name}", file=sys.stderr)

    table("1. lanczos3 in scene-linear and in log", lanczos, names, results)
    print("\n| Log space | " + " | ".join(names) + " |")
    print("| :--- |" + " :--- |" * len(names))
    print("| (lowest value after the conversion, pixels with a negative channel, output pixels that are inf or NaN "
          "in linear) |" + " |" * len(names))
    for space in LOGS:
        print(f"| {space} | " + " | ".join("{:.1f}, {:.1f}%, {}".format(*gamut[(space, n)]) for n in names) + " |")
    table("2. highlightcomp in different linear gamuts", highlightcomp, names, results)
    table("3. lanczos with 2, 3 and 4 lobes (zscale param_a)", lobes, names, results)

    if os.path.isdir(NUKE) and os.path.exists(SPARKS):
        lin = pixels(oiio.ImageBuf(SPARKS))
        w, h = 1024, 540
        candidates = {"oiiotool lanczos3": oiio_lanczos3(image(lin), w, h)}
        candidates.update({f"zscale param_a={n}": zscale_lanczos(image(lin), w, h, n) for n in (2, 3, 4)})
        print("\n4. Against Nuke's Reformat on Sparks (whole frame, after the view, 8-bit code values)\n")
        print("| Nuke filter | Resize | 99.9% of pixels within | Largest |")
        print("| :--- | :--- | ---: | ---: |")
        for filt in ("lanczos4", "lanczos6"):
            nuke = shown(oiio.ImageBuf(os.path.join(NUKE, f"nuke-{filt}.exr")))
            for label, b in candidates.items():
                d = np.abs(shown(b) - nuke) * 255
                print(f"| {filt} | {label} | {np.percentile(d, 99.9):.1f} | {d.max():.0f} |")


if __name__ == "__main__":
    main()
