"""
Make the 16-bit gradient test images used by tests/icctest-fulltv.py:

  greyramp-16bit.png    1024x150, a continuous ramp from black to white (each column a quarter of an 8-bit step
                        brighter than the last), so it has no steps of its own
  radialgrad-16bit.png  920x250, the same colour and falloff as radialgrad.png (an 8-bit image of unknown origin),
                        made from a formula: (31, 71, 147)/255 at the bottom centre, fading out over an elliptical
                        radius of 460 by 500 pixels

Both are untagged 16-bit RGB PNGs (no sRGB, gAMA, cHRM or cICP chunks), so FFmpeg reads them without colour
properties. Written directly, not with OpenImageIO, which always adds colour chunks to PNGs.

    python sourceimages/make_gradients_16bit.py
"""
import os
import struct
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def write_png16(img, path):
    """img: float RGB in 0..1, written as 16-bit RGB PNG with no colour chunks."""
    a = np.round(np.clip(img, 0, 1) * 65535).astype(">u2")
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def greyramp(w=1024, h=150):
    v = np.linspace(0, 1, w)
    return np.repeat(np.repeat(v[None, :, None], h, 0), 3, 2)


def radialgrad(w=920, h=250):
    y, x = np.mgrid[0:h, 0:w].astype(float)
    r = np.hypot((x - (w - 1) / 2) / 460, (y - (h - 1)) / 500)
    falloff = np.clip(1 - 0.844 * r ** 1.15, 0, 1)
    return falloff[..., None] * (np.array([31, 71, 147]) / 255)


if __name__ == "__main__":
    for name, img in (("greyramp-16bit.png", greyramp()), ("radialgrad-16bit.png", radialgrad())):
        write_png16(img, os.path.join(HERE, name))
        print("Written", os.path.join(HERE, name))
