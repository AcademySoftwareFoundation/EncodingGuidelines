"""
Small cropped examples for Resizing.md, cut from the resize comparison pages' images (run resize-test.py first).

Each example is a crop of the same place in several results, enlarged with no filtering so the pixels stay sharp,
written as 8-bit PNGs to static/resizing/. The crops were chosen by eye to show one effect clearly. For each
example the script prints the focus point (fractions of the image) to use in the comparison page's link, as
#...&zoom=Z&at=X,Y.

    python resizing_images.py
"""
import os

import numpy as np
import OpenImageIO as oiio

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "../static/resizing")

# name: (page folder, source id, crop w, crop h, enlargement, crop position (x, y), variants to write)
EXAMPLES = {
    # Right of the centre: coarse rings (the same in every result) getting finer until they average to grey
    'zoneplate': ("resize-compare", "zoneplate", 120, 68, 2, (262, 101),
                  ["reference", "scale_bicubic", "zscale_lanczos_linear"]),
    # A few separate sparks on dark ground (the 512x270 part of the frame the page shows)
    'sparks': ("resize-hdr-compare", "sparks", 56, 32, 3, (352, 219),
               ["reference", "hdr_oiio_scene_lanczos", "hdr_oiio_acescct_lanczos",
                "hdr_oiio_scene_lanczos_hc"]),
    # The left edge of the green disc (fine rings of a single very bright channel) and the ring around it
    'brightrings': ("resize-hdr-compare", "brightrings", 48, 48, 3, (110, 24),
                    ["reference", "hdr_oiio_scene_lanczos", "hdr_oiio_acescct_lanczos",
                     "hdr_oiio_scene_lanczos_hc"]),
}


def read(path):
    return np.array(oiio.ImageBuf(path).get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)


def write(img, path):
    buf = oiio.ImageBuf(np.ascontiguousarray(img.astype(np.float32)))
    if not buf.write(path, "uint8"):
        raise SystemExit(buf.geterror())


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (folder, src, w, h, k, (x, y), variants) in EXAMPLES.items():
        d = os.path.join(HERE, folder)
        H, W = read(os.path.join(d, f"{src}-reference.png")).shape[:2]
        for v in variants:
            img = read(os.path.join(d, f"{src}-{v}.png"))[y:y + h, x:x + w]
            out = os.path.join(OUT, f"{name}-{v}.png")
            write(np.repeat(np.repeat(img, k, 0), k, 1), out)
        print(f"{name}: {w}x{h} at {x},{y} of {W}x{H}, x{k}; link focus at={(x + w / 2) / W:.3f},{(y + h / 2) / H:.3f}")


if __name__ == "__main__":
    main()
