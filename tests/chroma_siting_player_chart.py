"""
Measure the chroma siting player charts (sourceimages/make_chroma_siting_player_chart.py for 4:2:2,
make_chroma_siting_player_chart_420.py for 4:2:0), either as decoded by FFmpeg or in a screenshot of a player.

For each band it gives the zoomed-out difference between the test and reference blocks: the Oklab distance
between their linear-light means (display gamma 2.4). The band near 0 is how the player reconstructs the chroma;
a wrong band is 0.04 or more. It also gives the scale check (light of the fine checkerboard over the coarse one,
display gamma 2.2: 1.00 at 100%, lower if the viewer scales) and, for the co-sited band, how many of its test
blocks match the reference pixel for pixel, left to right, which shows a player that is right on only part of
the picture. The 4:2:0 chart's bands come in two pairs, across and down; the verdict is the lower of each pair.

FFmpeg decodes (the ffmpeg on the PATH, or FFMPEG_BIN):
    python tests/chroma_siting_player_chart.py
A screenshot, taken at one image pixel per screen pixel (e.g. screencapture -o -l <window id> shot.png on macOS):
    python tests/chroma_siting_player_chart.py --capture shot.png
The 4:2:0 chart: --chart sourceimages/chroma_siting_player_chart_420-hevc.mp4, or --420 with --capture.
"""
import argparse
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
CHART = HERE.parent / "sourceimages" / "chroma_siting_player_chart_422-lossless.mkv"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
W, H = 1920, 1080
BANDS = ["co-sited", "centred linear", "centred bicubic", "sample repeat"]
BANDS_420 = ["across co-sited", "across centred", "down centred", "down co-sited"]
DECODES = {  # name: ffmpeg output arguments; the output is read as 16-bit RGB, packed (rgb48le) or planar (gbrp16le)
    "zscale": ["-vf", "zscale,format=gbrp16le"],
    "no filter, to packed RGB": ["-pix_fmt", "rgb48le"],
    "no filter, to planar RGB": ["-pix_fmt", "gbrp16le"],
    "scale bilinear+full_chroma_int": ["-vf", "scale=flags=bilinear+full_chroma_int+accurate_rnd", "-pix_fmt", "rgb48le"],
    "scale bicubic+full_chroma_int": ["-vf", "scale=flags=bicubic+full_chroma_int+accurate_rnd", "-pix_fmt", "rgb48le"],
    "scale lanczos+full_chroma_int": ["-vf", "scale=flags=lanczos+full_chroma_int+accurate_rnd", "-pix_fmt", "rgb48le"],
}
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])


def oklab(rgb):
    return M2 @ np.cbrt(M1 @ rgb)


def bands(img, left=0, top=0, s=1.0):
    """Difference between test and reference blocks for each band; img is R'G'B' in 0..1."""
    lin = np.clip(img, 0, 1) ** 2.4
    out = []
    for k in range(4):
        sums, n = np.zeros((2, 3)), np.zeros(2)
        for by in range(2):
            for bx in range(12):
                y0 = top + (120 + k * 240 + by * 120 + 12) * s
                x0 = left + (480 + bx * 120 + 12) * s
                blk = lin[int(round(y0)):int(round(y0 + 96 * s)), int(round(x0)):int(round(x0 + 96 * s))]
                sums[(by + bx) % 2] += blk.reshape(-1, 3).sum(0)
                n[(by + bx) % 2] += blk.shape[0] * blk.shape[1]
        out.append(np.linalg.norm(oklab(sums[0] / n[0]) - oklab(sums[1] / n[1])))
    return out


def scale_check(img, left, top, s):
    lin = img.mean(2) ** 2.2
    mean = lambda x0, y0, x1, y1: lin[int(top + y0 * s):int(top + y1 * s), int(left + x0 * s):int(left + x1 * s)].mean()
    return mean(1570, 20, 1720, 100) / mean(1740, 10, 1900, 110)


def cosited_blocks(img, left, top):
    """For each test block of the co-sited band, left to right: does it match the reference pixel for pixel?"""
    a = (img * 255).round().astype(int)
    ref = a[top + 132:top + 136, left + 640]        # one cycle down a reference block
    result = []
    for bx in range(12):
        r = top + 120 + (bx % 2) * 120 + 40
        xs = left + 480 + bx * 120
        result.append(all(np.abs(a[r, xs + i] - ref[(xs + i - left) % 4]).max() <= 6 for i in range(12, 108)))
    return result


def find_chart(img):
    """Top-left corner and scale of the chart in a screenshot: the first row with a long run of the title band's
    grey (it spans the chart's full width) that continues down its unlettered left edge for the band's height."""
    g = ((np.abs(img[..., 0] - img[..., 1]) < 0.02) & (np.abs(img[..., 1] - img[..., 2]) < 0.02)
         & (img[..., 1] > 0.15) & (img[..., 1] < 0.6))

    def longest_run(row):
        best, start, cur = (0, 0), 0, 0
        for x, v in enumerate(row):
            cur = cur + 1 if v else 0
            if cur == 1:
                start = x
            if cur > best[0]:
                best = (cur, start)
        return best

    for y in range(img.shape[0] - 4):
        if g[y].sum() < 900:
            continue
        n, x0 = longest_run(g[y])
        s = n / W
        if n >= 900 and g[y:y + int(110 * s), x0 + 4].all():
            # Confirm with the scale check's coarse checkerboard (20-pixel cells from x 1730, y 10 of the chart):
            # the cell centres alternate black and white whatever the scale.
            def cell(i, j):
                cy, cx = int(y + (20 + 20 * j) * s), int(x0 + (1740 + 20 * i) * s)
                return img[cy, cx].mean() if cy < img.shape[0] and cx < img.shape[1] else 0.5
            if all(abs(cell(i, j) - (i + j) % 2) < 0.2 for i in range(8) for j in range(5)):
                return x0, y, s
    raise SystemExit("chart not found: is the whole title band visible?")


def report(name, values, extra="", c420=False):
    names = BANDS_420 if c420 else BANDS
    best = [int(np.argmin(values[:2])), 2 + int(np.argmin(values[2:]))] if c420 else [int(np.argmin(values))]
    cells = "  ".join(f"{b} {v:.3f}{' <' if i in best else '  '}" for i, (b, v) in enumerate(zip(names, values)))
    print(f"{name:32s} {cells}{extra}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", type=Path, nargs="*", help="Screenshots of a player showing the chart")
    parser.add_argument("--chart", type=Path, default=CHART, help="Chart file to decode with FFmpeg")
    parser.add_argument("--420", dest="c420", action="store_true", help="The screenshots show the 4:2:0 chart")
    args = parser.parse_args()
    c420 = args.c420 or "_420" in args.chart.name
    if args.capture:
        for path in args.capture:
            img = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
            left, top, s = find_chart(img)
            check = scale_check(img, left, top, s)
            report(path.name, bands(img, left, top, s), f"  scale {s:.3f}, scale check {check:.2f}", c420)
            if abs(s - 1) < 0.01 and not c420:
                print(" " * 33 + "co-sited band, test blocks left to right: " +
                      " ".join("ok" if ok else "x" for ok in cosited_blocks(img, int(left), int(top))))
        return
    for name, out_args in DECODES.items():
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(args.chart), "-frames:v", "1"] + out_args +
                             ["-f", "rawvideo", "-"], capture_output=True, check=True).stdout
        px = np.frombuffer(raw, "<u2").astype(float) / 65535
        if "rgb48le" in out_args:
            img = px.reshape(H, W, 3)
        else:
            g, b, r = px.reshape(3, H, W)
            img = np.stack([r, g, b], -1)
        report(name, bands(img), c420=c420)


if __name__ == "__main__":
    main()
