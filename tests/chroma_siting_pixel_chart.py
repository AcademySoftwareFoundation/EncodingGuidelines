"""
Measure the chroma siting pixel charts (sourceimages/make_chroma_siting_pixel_chart.py): for each cell of a decoded
test frame, which assumption's expected pixels, from the 4:4:4 reference, is it closest to?

FFmpeg decodes (the ffmpeg on the PATH, or FFMPEG_BIN):
    python tests/chroma_siting_pixel_chart.py
Screenshots of a player showing the test file and the reference, at the same zoom (any zoom; the frame is found by
its grey and sampled at the centre of each image pixel):
    python tests/chroma_siting_pixel_chart.py --capture test.png reference.png --420
The labelled images for the docs (static/chroma-siting/pixel_chart_*.png):
    python tests/chroma_siting_pixel_chart.py --images
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "sourceimages"
sys.path.insert(0, str(SRC))
import make_chroma_siting_pixel_chart as chart  # noqa: E402

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
DECODES = {
    "zscale": ["-vf", "zscale,format=gbrp16le"],
    "no filter, to packed RGB": ["-pix_fmt", "rgb48le"],
    "no filter, to planar RGB": ["-pix_fmt", "gbrp16le"],
}


def decode(path, out_args):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-frames:v", "1"] + out_args + ["-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    px = np.frombuffer(raw, "<u2").astype(float) / 65535
    if "rgb48le" in out_args:
        return px.reshape(chart.SIZE, chart.SIZE, 3)
    g, b, r = px.reshape(3, chart.SIZE, chart.SIZE)
    return np.stack([r, g, b], -1)


def window(img, sx, sy):
    return img[sy - 4:sy + 5, sx - 4:sx + 6]


def hypotheses(ref, c420):
    """name: expected pixels around the raised sample."""
    if c420:
        return {f"{a}/{d}": window(ref, sx, sy) for a, sx in zip(chart.ACROSS, chart.SITES)
                for d, sy in zip(chart.DOWN, chart.SITES)}
    return {a: window(ref, chart.SITES[0], sy) for a, sy in zip(chart.ACROSS, chart.SITES)}


def classify(img, ref_hyp):
    rows = []
    for sy in chart.SITES:
        row = []
        for sx in chart.SITES:
            w = window(img, sx, sy)
            err = {k: float(np.sqrt(((w - v) ** 2).mean())) for k, v in ref_hyp.items()}
            best = min(err, key=err.get)
            row.append(f"{best} {err[best]:.4f}")
        rows.append(row)
    return rows


def longest_run(flags):
    best, cur = (0, 0), 0
    for i, v in enumerate(flags):
        cur = cur + 1 if v else 0
        if cur > best[0]:
            best = (cur, i - cur + 1)
    return best


def find_frame(a):
    """The frame in a screenshot: the largest square-ish neutral grey area whose top ruler has the expected ticks."""
    g = (np.abs(a[..., 0] - a[..., 1]) < 0.03) & (np.abs(a[..., 1] - a[..., 2]) < 0.03) & (a[..., 1] > 0.3)
    for frac in (0.8, 0.6, 0.4, 0.25):
        nw, x0 = longest_run(g.sum(0) > frac * g.sum(0).max())
        nh, y0 = longest_run(g.sum(1) > frac * g.sum(1).max())
        if nw >= chart.SIZE and abs(nw - nh) <= max(4, 0.02 * nw):
            return x0, y0, nw / chart.SIZE, nh / chart.SIZE
    raise SystemExit("frame not found: is the whole frame visible, in a neutral viewer background?")


def sample(path):
    """The screenshot's frame, one RGB value per image pixel."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(float) / 255
    x0, y0, sx, sy = find_frame(a)
    xs = (x0 + (np.arange(chart.SIZE) + 0.5) * sx).astype(int)
    ys = (y0 + (np.arange(chart.SIZE) + 0.5) * sy).astype(int)
    print(f"{Path(path).name}: frame at {x0},{y0}, zoom {sx:.2f}")
    return a[np.ix_(ys, xs)]


def correct_frame(ref, c420):
    """What a correct player shows for the test file: the reference with its correct cell repeated in every position.
    That cell is the first in both directions: co-sited, and in 4:2:0 co-sited across and centred down."""
    out, s = ref.copy(), chart.SITES[0]
    for sx in chart.SITES:
        for sy in chart.SITES:
            if c420:
                out[sy - 1:sy + 3, sx - 1:sx + 3] = ref[s - 1:s + 3, s - 1:s + 3]
            else:
                out[sy - chart.HALF:sy + chart.HALF, sx - 1:sx + 3] = ref[s - chart.HALF:s + chart.HALF, s - 1:s + 3]
    return out


def images():
    """The references, enlarged with nearest neighbour, labelled with the assumption each cell shows, and the frame a
    correct player shows for each test file."""
    zoom, left, top = 8, 110, 30
    font = ImageFont.load_default(size=14)
    for suffix, c420 in [("_422", False), ("_420", True)]:
        rgb = decode(SRC / f"{chart.NAME}{suffix}-reference.mkv", ["-vf", "zscale,format=gbrp16le"])
        big = Image.fromarray((rgb * 255).round().astype(np.uint8)).resize((chart.SIZE * zoom,) * 2, Image.NEAREST)
        out = Image.new("RGB", (big.width + left, big.height + top), (32, 32, 32))
        out.paste(big, (left, top))
        d = ImageDraw.Draw(out)
        at = [(s + 1) * zoom for s in chart.SITES]              # the centre of a cell's pattern
        if c420:
            for a, x in zip(chart.ACROSS, at):
                d.text((left + x, 8), a, fill="white", font=font, anchor="ma")
            for r, y in zip(chart.DOWN, at):
                d.text((left - 10, top + y), r, fill="white", font=font, anchor="rm")
        else:
            for a, y in zip(chart.ACROSS, at):
                d.text((left - 10, top + y), a, fill="white", font=font, anchor="rm")
        out.save(HERE.parent / "static" / "chroma-siting" / f"pixel_chart{suffix}_reference.png")

        good = Image.fromarray((correct_frame(rgb, c420) * 255).round().astype(np.uint8))
        good = good.resize((chart.SIZE * zoom,) * 2, Image.NEAREST)
        out = Image.new("RGB", (good.width, good.height + top), (32, 32, 32))
        out.paste(good, (0, top))
        label = "Correct: co-sited across, centred down" if c420 else "Correct: co-sited"
        ImageDraw.Draw(out).text((0, 8), label, fill="white", font=font)
        out.save(HERE.parent / "static" / "chroma-siting" / f"pixel_chart{suffix}_correct.png")


def guide_image():
    """What correct and wrong look like, zoomed in on one cell, with lines through the ticks. Expected pixels, computed
    here from the chart's definition."""
    zoom, n, left, top, gap = 11, 26, 110, 34, 14
    font = ImageFont.load_default(size=14)
    rows = [("4:2:2", False, [("Correct: co-sited", "co-sited", None), ("Wrong: centred", "centred", None),
                              ("Wrong: sample repeat", "repeat", None)]),
            ("4:2:0", True, [("Correct: co-sited across,", "co-sited", "centred"), ("Wrong: centred both ways", "centred", "centred"),
                             ("Wrong: repeated both ways", "repeat", "repeat")])]
    size = n * zoom
    out = Image.new("RGB", (left + 3 * (size + gap), 2 * (size + top + gap)), (32, 32, 32))
    d = ImageDraw.Draw(out)
    s = chart.SITES[0]
    for r, (name, c420, panels) in enumerate(rows):
        y0 = r * (size + top + gap) + top
        d.text((left - 12, y0 + size // 2), name, fill="white", font=font, anchor="rm")
        for c, (label, across, down) in enumerate(panels):
            x0 = left + c * (size + gap)
            weight = np.zeros((chart.SIZE, chart.SIZE))
            if c420:
                weight[s - 1:s + 3, s - 1:s + 3] = np.outer(chart.PROFILE[down], chart.PROFILE[across])
            else:
                weight[s - chart.HALF:s + chart.HALF, s - 1:s + 3] = chart.PROFILE[across]
            y, cb, cr = chart.luma_plane(c420), weight * chart.CB, weight * chart.CR
            rgb = np.stack([y + 1.5748 * cr, y - 0.1873 * cb - 0.4681 * cr, y + 1.8556 * cb], -1)[:n, :n]
            out.paste(Image.fromarray((rgb.clip(0, 1) * 255).round().astype(np.uint8)).resize((size, size), Image.NEAREST),
                      (x0, y0))
            line = (255, 220, 0)
            d.line([(x0 + (s + 0.5) * zoom, y0), (x0 + (s + 0.5) * zoom, y0 + size - 1)], fill=line)
            if c420:
                d.line([(x0, y0 + (s + 0.5) * zoom), (x0 + size - 1, y0 + (s + 0.5) * zoom)], fill=line)
            text = label + (" centred down" if c420 and c == 0 else "")
            d.text((x0, y0 - 20), text, fill="white", font=font)
    out.save(HERE.parent / "static" / "chroma-siting" / "pixel_chart_guide.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", type=Path, nargs=2, metavar=("TEST", "REFERENCE"))
    parser.add_argument("--420", dest="c420", action="store_true", help="The screenshots show the 4:2:0 chart")
    parser.add_argument("--images", action="store_true", help="Write the labelled reference images for the docs")
    args = parser.parse_args()
    if args.images:
        images()
        guide_image()
        return
    if args.capture:
        rows = classify(sample(args.capture[0]), hypotheses(sample(args.capture[1]), args.c420))
        for row in rows:
            print(" | ".join(row))
        return
    for suffix, c420, ref in [("_422-10bit", False, "_422"), ("_422-8bit", False, "_422"), ("_420-10bit", True, "_420"),
                              ("_420-8bit", True, "_420")]:
        for name, args in DECODES.items():
            r = decode(SRC / f"{chart.NAME}{ref}-reference.mkv", ["-vf", "zscale,format=gbrp16le"])
            rows = classify(decode(SRC / f"{chart.NAME}{suffix}.mkv", args), hypotheses(r, c420))
            print(f"{suffix:12s} {name:26s}", " | ".join(rows[0]))
            for row in rows[1:]:
                print(" " * 40, " | ".join(row))


if __name__ == "__main__":
    main()
