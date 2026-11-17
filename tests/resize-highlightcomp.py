"""
Lanczos3 with highlightcomp, with the lost light put back, then OCIO's view: a variant for resize-test.py.

oiiotool's --resize:highlightcomp=1 compresses each channel (rangecompress), filters, and expands (rangeexpand).
That stops lanczos ringing around highlights far brighter than white, but the averaging is then done on compressed
values, so a block that mixes bright and dark pixels comes out too dark (BrightRings keeps about 9% of its
highlights' light, Sparks 56%), and saturated highlights that should reach white show their colour.

The loss can be measured and undone. Each output pixel covers a footprint of source pixels (for a resize by a whole
factor k, its own k x k block):
    hc      = rangeexpand(lanczos3(rangecompress(src)))         highlightcomp, as oiiotool does it
    area    = the footprint's average, in scene-linear           the right brightness
    area_hc = rangeexpand(footprint average of rangecompress(src)) the same average, done the highlightcomp way
    result  = hc * area / area_hc                                per channel
In flat areas area = area_hc and nothing changes. Where bright and dark mix, the ratio scales the result back to the
right brightness. For a whole factor, the footprint never looks outside its own block, so the correction cannot
spread a highlight into its neighbours (a wider filter, such as the cubic, blooms).

For other factors (4096 to 1920 is x2.133) the footprint cuts through the source pixels at its edges, which are
weighted by how much of them it covers. It works, but less well: an output pixel that only just touches a highlight
gets a large ratio, which also multiplies lanczos's spill into it, so the highlights come out somewhat too bright
(about 1.2x their light on Sparks, more on BrightRings).

--clamp also limits each output pixel to the range of the source pixels its footprint touches (the anti-ringing
clamp of resize-antiring.py), which removes the mild halos highlightcomp leaves.

    python resize-highlightcomp.py in.exr WIDTH HEIGHT out.png [--clamp] [--no-view]

The input is treated as ACES2065-1 and viewed through the ACES 2.0 SDR view for sRGB (OCIO 2.5's built-in config,
unless $OCIO is set), and written as a 16-bit PNG; with --no-view the scene-linear result is written as a float
EXR instead.
"""
import argparse
import os
import sys

import numpy as np

os.environ.setdefault("OCIO", "ocio://default")
import OpenImageIO as oiio  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
from resizefootprint import area_resize, footprint_range  # noqa: E402

IBA = oiio.ImageBufAlgo
DISPLAY, VIEW = "sRGB - Display", "ACES 2.0 - SDR 100 nits (Rec.709)"


def pixels(buf):
    return np.array(buf.get_pixels(oiio.FLOAT)).astype(np.float64)


def image(a):
    return oiio.ImageBuf(np.ascontiguousarray(a.astype(np.float32)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("width", type=int)
    p.add_argument("height", type=int)
    p.add_argument("output")
    p.add_argument("--clamp", action="store_true", help="also clamp each pixel to the range of its footprint")
    p.add_argument("--no-view", action="store_true", help="write the scene-linear result (float EXR)")
    args = p.parse_args()

    src = IBA.channels(oiio.ImageBuf(args.input), (0, 1, 2))
    w, h = args.width, args.height
    lin = pixels(src)
    comp = IBA.rangecompress(src)

    hc = pixels(IBA.rangeexpand(IBA.resize(comp, "lanczos3", roi=oiio.ROI(0, w, 0, h, 0, 1, 0, 3))))
    area = area_resize(lin, w, h)
    area_hc = pixels(IBA.rangeexpand(image(area_resize(pixels(comp), w, h))))
    eps = 1e-6   # below this (or negative) there is nothing to correct
    out = hc * np.where(area_hc > eps, np.maximum(area, 0) / np.maximum(area_hc, eps), 1.0)
    if args.clamp:
        out = np.clip(out, *footprint_range(lin, w, h))

    if args.no_view:
        result, fmt = image(out), "float"
    else:
        result, fmt = IBA.ociodisplay(image(out), DISPLAY, VIEW, fromspace="ACES2065-1"), "uint16"
    if result.has_error or not result.write(args.output, fmt):
        sys.exit(result.geterror())


if __name__ == "__main__":
    main()
