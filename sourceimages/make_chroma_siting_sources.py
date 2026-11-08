"""
Generate 4:2:2 and 4:2:0 versions of chroma_siting_chart.png with known chroma siting, for testing where
FFmpeg assumes the chroma is when it decodes to RGB (enctests/test_configs/decode_siting_tests.yml).

The conversion is done here in numpy, not with FFmpeg: BT.709 limited range, 10-bit, with each chroma sample
taken from the full resolution chroma (lightly blurred, sigma 0.8 luma samples) at exactly its sited
position. The planes are then stored losslessly as FFV1 in MKV, whose ChromaSitingHorz/Vert elements carry
the chroma location tag through to FFmpeg's decoded frames. The untagged files have co-sited (left) chroma
and no chroma location.

  chroma_siting_chart-yuv420p10-left.mkv      4:2:0, co-sited horizontally, centred vertically (H.264 default)
  chroma_siting_chart-yuv420p10-center.mkv    4:2:0, centred both ways (JPEG, MPEG-1)
  chroma_siting_chart-yuv420p10-topleft.mkv   4:2:0, co-sited both ways (BT.2020 UHD, DV PAL)
  chroma_siting_chart-yuv420p10-untagged.mkv  4:2:0, left, with no chroma location
  chroma_siting_chart-yuv422p10-left.mkv      4:2:2, co-sited (BT.709, professional formats)
  chroma_siting_chart-yuv422p10-center.mkv    4:2:2, centred
  chroma_siting_chart-yuv422p10-untagged.mkv  4:2:2, co-sited, with no chroma location

Each gets a .yml for the test framework naming chroma_siting_chart.png as its reference and the siting the
chroma really has. Needs ffmpeg on the PATH (any version from 6.0).

    python sourceimages/make_chroma_siting_sources.py
"""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from make_chroma_siting_chart import H, W, chart

HERE = Path(__file__).resolve().parent
KR, KB = 0.2126, 0.0722
# Chroma offsets in luma samples from the even sample, for each siting.
OFFSETS = {"left": (0, 0.5), "center": (0.5, 0.5), "topleft": (0, 0)}
# (name, subsampling, the siting the chroma has, the tag written)
FILES = [
    ("yuv420p10-left", (2, 2), "left", "left"),
    ("yuv420p10-center", (2, 2), "center", "center"),
    ("yuv420p10-topleft", (2, 2), "topleft", "topleft"),
    ("yuv420p10-untagged", (2, 2), "left", None),
    ("yuv422p10-left", (2, 1), "left", "left"),
    ("yuv422p10-center", (2, 1), "center", "center"),
    ("yuv422p10-untagged", (2, 1), "left", None),
]
YML = """images: false
path: {path}
# Lossless FFV1, BT.709 limited range {fmt} 10-bit, subsampled in numpy with {siting} chroma
# ({tag}); made by make_chroma_siting_sources.py
reference: chroma_siting_chart.png
chroma_siting: {siting}
width: {w}
height: {h}
in: 0
duration: 1
rate: 25.0
"""


def blur(a, sigma, axis):
    """Gaussian blur along one axis, edges extended."""
    r = int(3 * sigma + 1)
    x = np.arange(-r, r + 1)
    k = np.exp(-x * x / (2 * sigma * sigma))
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    a = np.pad(a, pad, mode="edge")
    n = a.shape[axis] - 2 * r
    return sum(w * np.take(a, np.arange(i, i + n), axis) for i, w in enumerate(k))


def sample(plane, positions, axis):
    """plane at fractional positions along axis, by linear interpolation."""
    i0 = np.clip(np.floor(positions).astype(int), 0, plane.shape[axis] - 2)
    w = (positions - i0).reshape([-1 if a == axis else 1 for a in range(2)])
    return np.take(plane, i0, axis) * (1 - w) + np.take(plane, i0 + 1, axis) * w


def planes(rgb, sxsy, offsets):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = KR * r + (1 - KR - KB) * g + KB * b
    out = [np.round(y * 876 + 64)]
    for c in ((b - y) / (2 * (1 - KB)), (r - y) / (2 * (1 - KR))):
        c = c * 896 + 512
        for axis, step, offset in ((1, sxsy[0], offsets[0]), (0, sxsy[1], offsets[1])):
            if step > 1:
                c = sample(blur(c, 0.8, axis), step * np.arange(c.shape[axis] // step) + offset, axis)
        out.append(np.round(c))
    return [np.clip(p, 0, 1023).astype("<u2") for p in out]


def main():
    rgb = chart()
    tags = "-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709".split()
    with tempfile.TemporaryDirectory() as tmp:
        for name, sxsy, siting, tag in FILES:
            pix_fmt = name.split("-")[0] + "le"
            raw = Path(tmp, name + ".yuv")
            raw.write_bytes(b"".join(p.tobytes() for p in planes(rgb, sxsy, OFFSETS[siting])))
            loc = ["-chroma_sample_location", tag] if tag else []
            out = HERE / f"chroma_siting_chart-{name}.mkv"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", pix_fmt, "-s", f"{W}x{H}",
                            *tags, *loc, "-i", str(raw), "-c:v", "ffv1", "-level", "3", *tags, *loc, str(out)],
                           check=True)
            out.with_suffix(".mkv.yml").write_text(YML.format(
                path=out.name, fmt="4:2:0" if sxsy[1] > 1 else "4:2:2", siting=siting,
                tag=f"tagged {tag}" if tag else "no chroma location tag", w=W, h=H))
            print(out.name)


if __name__ == "__main__":
    main()
