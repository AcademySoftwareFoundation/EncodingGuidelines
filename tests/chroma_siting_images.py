"""
Make illustrations of chroma siting from sourceimages/chroma_siting_chart.png, for the docs.

For each converter the chart is converted to 4:2:2 (16-bit, raw, no codec), then:

  * reconstruction_<band>.png: the 4:2:2 decoded back to RGB the way a player would, assuming co-sited
    chroma (zscale, bilinear, chromalin=left), cropped around the single-pixel blue lines and zoomed with
    nearest neighbour. Columns: source, then each converter. The row below is the difference from the
    source, amplified, so the shape of the colour error is visible.
  * chroma_samples_<band>.png: one bar per Cb sample, drawn at the position the format assumes (co-sited
    with the even luma column), its height the sample's value above the background, under markers for the
    luma columns that hold the lines. One row per converter.

<band> is "even" (lines on even columns) or "odd" (lines on odd columns).

    rez-env encodingguidelines_env ffmpeg-9.0 -- python tests/chroma_siting_images.py
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sourceimages"))
import make_chroma_siting_chart as chart  # noqa: E402

SOURCE = HERE.parent / "sourceimages" / "chroma_siting_chart.png"
OUTDIR = HERE / "chroma-siting" / "images"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
W, H = chart.W, chart.H
SCALE = "scale=out_color_matrix=bt709:out_range=tv"
CONVERTERS = {
    "zscale": ["-vf", "zscale=rangein=full:matrix=709:range=limited,format=yuv422p16le"],
    "scale": ["-vf", SCALE + ",format=yuv422p16le"],
    "scale_left_full_chroma_inp": ["-sws_flags", "bicubic+full_chroma_inp",
                                   "-vf", SCALE + ":out_chroma_loc=left,format=yuv422p16le"],
}
# Crops: 16 rows from the vertical-line band, 24 columns around two lines.
ROWS = slice(2 * chart.BAND + 60, 2 * chart.BAND + 76)
BANDS = {"even": slice(36, 60), "odd": slice(chart.W // 2 + 13, chart.W // 2 + 37)}
ZOOM = 16
GAIN = 8


def run(cmd, data=None):
    r = subprocess.run(cmd, input=data, capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode())
    return r.stdout


def to_422(args):
    return run([FFMPEG, "-v", "error", "-i", str(SOURCE), "-frames:v", "1", *args,
                "-f", "rawvideo", "-pix_fmt", "yuv422p16le", "-"])


def to_rgb(yuv):
    """Decode 4:2:2 the way a player would: co-sited chroma, bilinear upsampling."""
    rgb = run([FFMPEG, "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv422p16le", "-s", f"{W}x{H}", "-i", "-",
               # zscale needs the input tagged: matrixin= on untagged input fails with "no path between colorspaces".
               # format=gbrp16le straight after zscale makes zscale do the conversion; with a format it cannot
               # output (e.g. rgb48be), FFmpeg leaves zscale outputting Y'CbCr and converts with libswscale.
               "-vf", "setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709,"
                      "zscale=range=full:filter=bilinear:chromalin=left,format=gbrp16le",
               "-f", "rawvideo", "-pix_fmt", "rgb48be", "-"], yuv)
    return np.frombuffer(rgb, ">u2").reshape(H, W, 3) / 65535.0


def cb_plane(yuv):
    a = np.frombuffer(yuv, "<u2").astype(np.float64)
    return a[W * H:W * H + W // 2 * H].reshape(H, W // 2)


def zoom(img):
    return np.repeat(np.repeat(img, ZOOM, axis=0), ZOOM, axis=1)


def gap(h, w=4):
    return np.ones((h, w, 3))


def write(path, img):
    img = np.clip(img, 0, 1)
    buf = oiio.ImageBuf(oiio.ImageSpec(img.shape[1], img.shape[0], 3, oiio.UINT8))
    buf.set_pixels(oiio.ROI(), img.astype(np.float32))
    buf.write(str(path))
    print(f"Wrote {path}")


def reconstruction(source, decoded, band):
    cols = BANDS[band]
    tiles = [zoom(source[ROWS, cols])] + [zoom(d[ROWS, cols]) for d in decoded.values()]
    diffs = [np.full_like(tiles[0], 0.5)] + [zoom(0.5 + GAIN * (d[ROWS, cols] - source[ROWS, cols]))
                                             for d in decoded.values()]
    h = tiles[0].shape[0]
    top = np.concatenate(sum(([t, gap(h)] for t in tiles), [])[:-1], axis=1)
    bottom = np.concatenate(sum(([t, gap(h)] for t in diffs), [])[:-1], axis=1)
    return np.concatenate([top, np.ones((4, top.shape[1], 3)), bottom], axis=0)


def chroma_samples(cbs, band):
    """Bars at the co-sited position of each Cb sample, under markers for the luma line columns."""
    cols = BANDS[band]
    first, last = cols.start, cols.stop
    lines = [c for c in chart.EVEN_COLUMNS + chart.ODD_COLUMNS if first <= c < last]
    row_h, z = 120, ZOOM
    rows = []
    for cb in cbs.values():
        profile = cb[(ROWS.start + ROWS.stop) // 2]
        background = np.median(profile)
        peak = max(abs(profile[c // 2] - background) for c in lines)
        img = np.full((row_h, (last - first) * z, 3), 0.92)
        for x in range(first, last):  # luma grid
            img[:, (x - first) * z] = 0.8
        for c in lines:  # the source line
            img[:10, (c - first) * z:(c - first + 1) * z] = (0.2, 0.2, 0.9)
        for k in range(first // 2, (last + 1) // 2):
            x0 = (2 * k - first) * z  # co-sited: sample k sits on luma column 2k
            if x0 < 0:
                continue
            v = (profile[k] - background) / peak
            height = int(abs(v) * (row_h - 30))
            colour = (0.1, 0.1, 0.6) if v >= 0 else (0.8, 0.2, 0.2)
            img[row_h - height:row_h, x0 + z // 4:x0 + 3 * z // 4] = colour
        rows += [img, np.ones((6, img.shape[1], 3))]
    return np.concatenate(rows[:-1], axis=0)


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    buf = oiio.ImageBuf(str(SOURCE))
    source = buf.get_pixels(oiio.FLOAT)[..., :3].astype(np.float64)
    yuvs = {name: to_422(args) for name, args in CONVERTERS.items()}
    decoded = {name: to_rgb(yuv) for name, yuv in yuvs.items()}
    cbs = {name: cb_plane(yuv) for name, yuv in yuvs.items()}
    for band in BANDS:
        write(OUTDIR / f"reconstruction_{band}.png", reconstruction(source, decoded, band))
        write(OUTDIR / f"chroma_samples_{band}.png", chroma_samples(cbs, band))
    (OUTDIR / "README.md").write_text(
        "Generated by tests/chroma_siting_images.py from sourceimages/chroma_siting_chart.png with "
        f"`{run([FFMPEG, '-hide_banner', '-version']).decode().splitlines()[0]}`.\n\n"
        "Column / row order: " + ", ".join(["source"] + list(CONVERTERS)) + " (reconstruction: source first, "
        "then each converter, difference x" + str(GAIN) + " below; chroma_samples: one row per converter, "
        "source excluded).\n")


if __name__ == "__main__":
    main()
