"""
Generate the 4:2:0 chroma siting player chart: a test you look at, zoomed out, to see where a player puts 4:2:0
chroma, across and down. See ChromaSitingTests.md.

4:2:0 halves the chroma both ways, so unlike the 4:2:2 chart there is no direction in which a reference block is
held exactly. Instead each band compares a striped pattern with its mirror image. The stripes run one way only
(vertical stripes test the siting across, horizontal stripes the siting down), so the other direction does not
matter. Mirror the pattern through a chroma sample, and any player that treats the samples as co-sited, with any
symmetric filter, rebuilds the mirror block as the mirror image of the original: the two contain the same pixels,
and the band looks like a uniform field. A player that thinks the samples are centred pairs luma and chroma
differently in the two blocks, and the checkerboard shows. Mirror it between two pixels instead and it is the
other way round. So each direction has two bands, and a player makes exactly one of them uniform:

  Across: co-sited    uniform when the player treats the chroma as co-sited across (H.264, HEVC, AV1, BT.2020)
  Across: centred     uniform when it treats it as centred (JPEG, MPEG-1; also sample repeat)
  Down: centred       uniform when it treats it as centred down: FFmpeg's "left", the H.264/HEVC/AV1 default
  Down: co-sited      uniform when it treats it as co-sited down: "topleft", BT.2020

The pattern is a four-pixel cycle, luma Y0..Y3, chroma samples X and Z. The colours were chosen so that the wrong
band differs by at least 0.065 in Oklab (linear-light means, display gamma 2.4) for co-sited players (interpolating
or smoothing) and centred ones (linear to sample repeat), with every pixel in gamut, so the result comes from
display gamma alone, and so that the bands' uniform colours are at least 0.12 apart. As with the 4:2:2 chart, it only works at exactly 100%, and has the same scale check.

Writes 10-bit (and 8-bit H.264) BT.709 limited range 4:2:0. The chroma has no true position here: the bands say
what the player assumes, and which is right depends on the label. The files say left (the H.264/HEVC default),
and some say topleft or center on purpose, to show whether a player reads the label:

  chroma_siting_player_chart_420-lossless.mkv     FFV1, lossless, 10-bit, labelled left
  chroma_siting_player_chart_420-hevc.mp4         HEVC Main 10, CRF 4, 2 s, VUI left (plays in browsers)
  chroma_siting_player_chart_420-hevc-topleft.mp4 the same, VUI topleft
  chroma_siting_player_chart_420-h264.mp4         H.264 High, 8-bit, CRF 1, 2 s, no VUI location (= left)
  chroma_siting_player_chart_420-h264-topleft.mp4 the same, VUI topleft
  chroma_siting_player_chart_420-h264-center.mp4  the same, VUI center
  chroma_siting_player_chart_420-hevc-center.mp4  HEVC Main 10, VUI center
  chroma_siting_player_chart_420-hevc-8bit.mp4    HEVC Main, 8-bit, VUI left
  chroma_siting_player_chart_420-h264-10bit.mp4   H.264 High 10, no VUI location (plus -topleft and -center copies)

(The .mkv names must not end in a digit: xStudio would read one as a single frame of a sequence.)

The 8-bit HEVC and 10-bit H.264 files separate the codec from the bit depth in a player that differs between
them.

Needs ffmpeg with libx264 and libx265 on the PATH (or FFMPEG_BIN), numpy and Pillow.

    python sourceimages/make_chroma_siting_player_chart_420.py
"""
import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from make_chroma_siting_player_chart import BLOCK, H, LABEL, TOP, W, annotate

HERE = Path(__file__).resolve().parent
NAME = "chroma_siting_player_chart_420"
# Luma order in the mirror block: through a chroma sample (co-sited players see a mirror image), or between two
# pixels (centred players do).
MIRROR = {"co-sited": [0, 3, 2, 1], "centred": [1, 0, 3, 2]}
# label, note, direction the stripes vary in, mirror, and the pattern: chroma X, chroma Z (Cb, Cr), luma of the four
# pixels in the cycle. Each band has its own colours, so that two uniform bands never look alike by accident.
BANDS = [
    ("Across: co-sited", "H.264, HEVC, AV1, BT.2020", "x", "co-sited",
     ((0.147, 0.173), (-0.139, -0.164), (0.108, 0.728, 0.258, 0.258))),
    ("Across: centred", "JPEG, MPEG-1; sample repeat", "x", "centred",
     ((0.266, 0.317), (-0.108, -0.127), (0.198, 0.501, 0.850, 0.200))),
    ('Down: centred ("left")', "H.264, HEVC, AV1 default", "y", "centred",
     ((0.299, 0.352), (-0.320, -0.377), (0.445, 0.221, 0.594, 0.763))),
    ('Down: co-sited ("topleft")', "BT.2020", "y", "co-sited",
     ((-0.095, -0.112), (0.229, 0.290), (0.177, 0.179, 0.179, 0.535))),
]


def chart():
    """The chart as 10-bit Y, Cb, Cr planes (Cb and Cr at half width and half height)."""
    y = np.full((H, W), 0.5)
    cb = np.zeros((H, W))
    cr = np.zeros((H, W))
    for k, (_, _, axis, mirror, (X, Z, lumas)) in enumerate(BANDS):
        r0, r1 = TOP + k * 2 * BLOCK, TOP + (k + 1) * 2 * BLOCK
        yy, xx = np.mgrid[r0:r1, LABEL:W]
        original = ((yy - r0) // BLOCK + (xx - LABEL) // BLOCK) % 2 == 0
        u = xx if axis == "x" else yy             # position along the stripes' direction; blocks start on a cycle
        lum = np.array(lumas)
        y[r0:r1, LABEL:] = np.where(original, lum[u % 4], lum[np.array(MIRROR[mirror])[u % 4]])
        # Chroma samples alternate X, Z along u (sample index u // 2) and are the same in both blocks.
        c = np.array([X, Z])[(u // 2) % 2]
        cb[r0:r1, LABEL:], cr[r0:r1, LABEL:] = c[..., 0], c[..., 1]
    y, cb, cr = annotate(y, cb, cr, [
        "4:2:0 chroma siting: which bands are uniform fields?",
        "Across: co-sited is right for H.264, HEVC and AV1. Down: centred (\"left\") is their default; "
        "co-sited (\"topleft\") is BT.2020.",
        "View at exactly 100%. If the two halves of the patch on the right are not equally bright, "
        "the viewer is scaling: ignore the bands."], [band[:2] for band in BANDS])
    return [np.clip(p, 4, 1019).astype("<u2") for p in (y, cb[0::2, 0::2], cr[0::2, 0::2])]


def main():
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    with tempfile.TemporaryDirectory() as tmp:
        planes = chart()
        raw, raw8 = Path(tmp) / "chart.yuv", Path(tmp) / "chart8.yuv"
        raw.write_bytes(b"".join(p.tobytes() for p in planes))
        # 8-bit from the 10-bit codes here rather than in FFmpeg, which may dither and break the mirror symmetry.
        raw8.write_bytes(b"".join(((p.astype(int) + 2) // 4).clip(1, 254).astype(np.uint8).tobytes() for p in planes))
        tags = ["-s", f"{W}x{H}", "-r", "25", "-color_range", "tv",
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        src = ["-f", "rawvideo", "-pix_fmt", "yuv420p10le"] + tags
        src8 = ["-f", "rawvideo", "-pix_fmt", "yuv420p"] + tags
        loop = ["-stream_loop", "49"]           # 2 s for the formats that compress a static frame to nothing
        hevc = ["-c:v", "libx265", "-crf", "4", "-tag:v", "hvc1", "-x265-params", "log-level=error",
                "-movflags", "+write_colr"]
        h264 = ["-c:v", "libx264", "-profile:v", "high", "-crf", "1", "-movflags", "+write_colr"]
        h264_10 = ["-c:v", "libx264", "-profile:v", "high10", "-crf", "1", "-movflags", "+write_colr"]
        jobs = [
            (src + ["-i", raw, "-c:v", "ffv1", "-chroma_sample_location", "left"], "-lossless.mkv"),
            (src + loop + ["-i", raw] + hevc + ["-chroma_sample_location", "left"], "-hevc.mp4"),
            (src + loop + ["-i", raw] + hevc + ["-chroma_sample_location", "topleft"], "-hevc-topleft.mp4"),
            (src8 + loop + ["-i", raw8] + h264, "-h264.mp4"),
            (src8 + loop + ["-i", raw8] + h264 + ["-chroma_sample_location", "topleft"], "-h264-topleft.mp4"),
            (src8 + loop + ["-i", raw8] + h264 + ["-chroma_sample_location", "center"], "-h264-center.mp4"),
            (src + loop + ["-i", raw] + hevc + ["-chroma_sample_location", "center"], "-hevc-center.mp4"),
            (src8 + loop + ["-i", raw8] + hevc + ["-chroma_sample_location", "left"], "-hevc-8bit.mp4"),
            (src + loop + ["-i", raw] + h264_10, "-h264-10bit.mp4"),
            (src + loop + ["-i", raw] + h264_10 + ["-chroma_sample_location", "topleft"], "-h264-10bit-topleft.mp4"),
            (src + loop + ["-i", raw] + h264_10 + ["-chroma_sample_location", "center"], "-h264-10bit-center.mp4"),
        ]
        for args, suffix in jobs:
            out = HERE / (NAME + suffix)
            subprocess.run([ffmpeg, "-v", "error", "-y"] + [str(a) for a in args] + [str(out)], check=True)
            print(out.name, out.stat().st_size)


if __name__ == "__main__":
    main()
