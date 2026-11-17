"""
Lanczos3 in scene-linear with an anti-ringing clamp, then OCIO's view: a variant for resize-test.py.

Lanczos's negative lobes make dark halos (and some bloom) around highlights far brighter than white. This clamps
each output pixel to the range (per channel) of the source pixels it covers: its own k x k block, for a resize by a
whole factor k, otherwise every source pixel its footprint touches (3 or 4 across at x2.133, 4096 to 1920). Next
to a highlight, every source pixel in a footprint of plain background is the same, so the result cannot dip below
it (no halo) or rise above it (no bloom). Inside a footprint that holds the highlight, the range is wide and lanczos
is left as it is, so it stays sharp and keeps the highlight's energy. This is the anti-ringing used by libplacebo
and madVR, with the footprint as the window.

It is not "clamp negatives" (oiiotool --clamp:min=0, or geq max(x,0) in FFmpeg): that only lifts values below zero
to zero, which leaves the halos, as black.

oiiotool has no such option, so this does it with the OpenImageIO Python bindings, with exact limits. FFmpeg can
do it too, in a roundabout way (erosion and dilation only work on integers, so the limits go through a log curve):
see ff_antiring() in resize-test.py.

    python resize-antiring.py in.exr WIDTH HEIGHT out.png [--no-view]

The input is treated as ACES2065-1 and viewed through the ACES 2.0 SDR view for sRGB (OCIO 2.5's built-in config,
unless $OCIO is set), and written as a 16-bit PNG; with --no-view the clamped scene-linear result is written as a
float EXR instead.
"""
import argparse
import os
import sys

import numpy as np

os.environ.setdefault("OCIO", "ocio://default")
import OpenImageIO as oiio  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
from resizefootprint import footprint_range  # noqa: E402

DISPLAY, VIEW = "sRGB - Display", "ACES 2.0 - SDR 100 nits (Rec.709)"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("width", type=int)
    p.add_argument("height", type=int)
    p.add_argument("output")
    p.add_argument("--no-view", action="store_true", help="write the scene-linear result (float EXR)")
    args = p.parse_args()

    src = oiio.ImageBufAlgo.channels(oiio.ImageBuf(args.input), (0, 1, 2))
    lin = np.array(src.get_pixels(oiio.FLOAT))

    out = oiio.ImageBufAlgo.resize(src, "lanczos3", roi=oiio.ROI(0, args.width, 0, args.height, 0, 1, 0, 3))
    lo, hi = footprint_range(lin, args.width, args.height)
    clamped = oiio.ImageBuf(np.ascontiguousarray(np.clip(np.array(out.get_pixels(oiio.FLOAT)), lo, hi)))

    if args.no_view:
        result, fmt = clamped, "float"
    else:
        result, fmt = oiio.ImageBufAlgo.ociodisplay(clamped, DISPLAY, VIEW, fromspace="ACES2065-1"), "uint16"
    if result.has_error or not result.write(args.output, fmt):
        sys.exit(result.geterror())


if __name__ == "__main__":
    main()
