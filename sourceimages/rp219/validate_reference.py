"""
Validate the RP 219 Y'CbCr references in this folder.

Checks, over patch interiors (bar edges are excluded, as Resolve's and vapoursynth's
bar widths differ by a pixel in places):
  1. The 10-bit reference against values published in SMPTE RP 219: the top row of 75%
     bars, the 100% white patch in row 2, and the PLUGE patches in the bottom row.
  2. Both references against the BT.709 limited-range formula applied to Resolve's
     independently generated RGB bars (16-bit and 10-bit DPX). The PLUGE section of the
     bottom row is excluded: Resolve places it about 68 pixels right of RP 219, and its
     -2% patch cannot exist in full-range RGB.

The references are stored as lossless FFV1 (.mkv), and decoded with ffmpeg at their own pixel format, so
ffmpeg does no colour conversion. Needs numpy, the OpenImageIO Python bindings and ffmpeg on the PATH (or
FFMPEG_BIN):
    python sourceimages/rp219/validate_reference.py
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

HERE = Path(__file__).resolve().parent

# SMPTE RP 219 75% bars, 10-bit Y'/Cb/Cr: 40% grey, white, yellow, cyan, green, magenta, red, blue, 40% grey.
RP219_TOP_ROW_10BIT = [(414, 512, 512), (721, 512, 512), (674, 176, 543), (581, 589, 176), (534, 253, 207),
                       (251, 771, 817), (204, 435, 848), (111, 848, 481), (414, 512, 512)]
TOP_ROW_SAMPLES = [120, 343, 549, 755, 960, 1166, 1372, 1578, 1800]  # x positions, at y=300
# Other RP 219 patches, 10-bit: (x, y, expected Y'/Cb/Cr)
RP219_PATCHES_10BIT = {
    "row 2, 100% white": (343, 675, (940, 512, 512)),
    "row 4, -2% PLUGE": (1165, 945, (46, 512, 512)),
    "row 4, +2% PLUGE": (1303, 945, (82, 512, 512)),
    "row 4, +4% PLUGE": (1441, 945, (99, 512, 512)),
}
# Bottom row PLUGE section (rows, columns) where Resolve's layout differs from RP 219.
PLUGE_SECTION = (slice(810, 1080), slice(950, 1560))


FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
REFERENCES = ("rp219_yuv444p10.mkv", "rp219_yuv444p12.mkv")


def read_ycbcr(path):
    """Y'CbCr planes and bit depth from a .y4m, or from any file ffmpeg can decode (e.g. the FFV1 .mkv)."""
    path = Path(path)
    if path.suffix == ".y4m":
        return read_y4m(path)
    probe = subprocess.run([FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries",
                            "stream=pix_fmt,width,height", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, pix_fmt = int(probe[0]), int(probe[1]), probe[2]
    bits = int(pix_fmt.split("p")[-1][:2]) if pix_fmt.startswith("yuv444p1") else 8
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", pix_fmt, "-"], capture_output=True, check=True).stdout
    dtype = "<u2" if bits > 8 else "u1"
    return np.frombuffer(raw, dtype)[:3 * w * h].reshape(3, h, w).astype(np.int64), bits


def read_y4m(path):
    data = path.read_bytes()
    end = data.index(b"\n")
    fields = {f[0]: f[1:] for f in data[:end].decode().split()[1:]}
    w, h, bits = int(fields["W"]), int(fields["H"]), int(fields["C"].split("p")[1])
    start = data.index(b"\n", data.index(b"FRAME", end)) + 1
    planes = np.frombuffer(data[start:start + 3 * w * h * 2], "<u2").reshape(3, h, w).astype(np.int64)
    return planes, bits


def read_rgb(path):
    buf = oiio.ImageBuf(str(path))
    bits = buf.spec().get_int_attribute("oiio:BitsPerSample")
    # Exact code values, then normalised to 0-1 full range.
    codes = np.round(buf.get_pixels(oiio.FLOAT)[..., :3].astype(np.float64) * ((1 << bits) - 1))
    return codes / ((1 << bits) - 1), bits


def bt709_limited(rgb, bits):
    """R'G'B' (0-1, full range) to BT.709 limited range Y'CbCr code values."""
    kr, kb = 0.2126, 0.0722
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = kr * r + (1 - kr - kb) * g + kb * b
    cb, cr = (b - y) / (2 * (1 - kb)), (r - y) / (2 * (1 - kr))
    s = 1 << (bits - 8)
    return np.round(np.stack([y * 219 * s + 16 * s, cb * 224 * s + 128 * s, cr * 224 * s + 128 * s])).astype(np.int64)


def flat(planes, margin=4):
    """True where every plane is constant within margin pixels."""
    mask = np.ones(planes.shape[1:], bool)
    for p in planes:
        for axis in (0, 1):
            for shift in range(1, margin + 1):
                mask &= (np.roll(p, shift, axis) == p) & (np.roll(p, -shift, axis) == p)
    return mask


def main():
    failures = 0
    ref10, _ = read_ycbcr(HERE / REFERENCES[0])
    got = [tuple(int(v) for v in ref10[:, 300, x]) for x in TOP_ROW_SAMPLES]
    ok = got == RP219_TOP_ROW_10BIT
    failures += not ok
    print(f"1. 10-bit reference vs RP 219 table:\n   top row 75% bars: {'OK' if ok else 'MISMATCH'}")
    if not ok:
        print(f"   expected {RP219_TOP_ROW_10BIT}\n   got      {got}")
    for name, (x, y, expected) in RP219_PATCHES_10BIT.items():
        got = tuple(int(v) for v in ref10[:, y, x])
        ok = got == expected
        failures += not ok
        print(f"   {name}: {'OK' if ok else f'MISMATCH, expected {expected} got {got}'}")

    print("2. References vs BT.709 formula applied to Resolve RGB (patch interiors):")
    for dpx in ("smptehdbars_16_resolve.dpx", "smptehdbars_10_resolve.dpx"):
        rgb, src_bits = read_rgb(HERE / dpx)
        rgb_mask = flat(np.moveaxis(np.round(rgb * 65535), -1, 0))
        rgb_mask[PLUGE_SECTION] = False
        for ref_name in REFERENCES:
            ref, bits = read_ycbcr(HERE / ref_name)
            mask = flat(ref) & rgb_mask
            diff = np.abs(bt709_limited(rgb, bits) - ref)
            worst = [int(d[mask].max()) for d in diff]
            # A 16-bit source should match exactly; a 10-bit source cannot represent every patch exactly.
            allowed = 0 if src_bits == 16 else 1 << (bits - 10)
            ok = max(worst) <= allowed
            failures += not ok
            print(f"   {dpx} -> {ref_name}: max Y/Cb/Cr diff {worst} "
                  f"(allowed {allowed}, {mask.mean():.0%} of pixels compared) {'OK' if ok else 'FAIL'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
