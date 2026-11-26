"""
Measure the chroma siting check files (sourceimages/make_chroma_siting_check.py) as FFmpeg decodes them, or in a
screenshot of a player.

For each panel (Across, and Down for 4:2:0) it simulates viewing from a distance (a Gaussian blur in linear light,
display gamma 2.4) and gives the word's contrast against the background (Oklab distance; about 0.07 or more when
the word shows, near 0 when the player follows the label) and the strongest edge left where the word should have
disappeared. With --images it also writes the simulated views as PNGs.

    python tests/chroma_siting_check.py                               # every file, with FFmpeg's decoders
    python tests/chroma_siting_check.py --images out/                 # and write the simulated views
    python tests/chroma_siting_check.py --capture shot.png --file chroma_siting_check_420-hevc-topleft.mp4
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sourceimages"))
from make_chroma_siting_check import CAPTION, LABEL, OUT, ROW, W, panel_mask, panels  # noqa: E402

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
SIGMA = 3.0          # blur, in pixels: enough to hide the four-pixel stripes
DECODES = {
    "zscale": ["-vf", "zscale,format=gbrp16le"],
    "no filter, planar RGB": ["-pix_fmt", "gbrp16le"],
    "no filter, packed RGB": ["-pix_fmt", "rgb48le"],
}
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])


def blur(img, s=SIGMA):
    k = np.exp(-0.5 * (np.arange(-int(4 * s), int(4 * s) + 1) / s) ** 2)
    k /= k.sum()
    for axis in (0, 1):
        img = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), axis, img)
    return img


def grow(m, n):
    out = m.copy()
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def info(name):
    """The panels (as displayed) and whether the file is rotated, from its name."""
    sub, rest = name.split("_")[-1].split("-", 1)
    label = rest.split("-")[1].split(".")[0]
    rotated = "-rot90" in name
    return panels(sub, label, rotated), rotated


def measure(rgb, pans):
    """rgb: R'G'B' 0..1, the chart only. Returns [(panel, word contrast, edge)] and the simulated view."""
    lin = np.clip(rgb, 0, 1) ** 2.4
    view = blur(lin)
    lab = np.cbrt(view @ M1.T) @ M2.T
    out = []
    for k, (_, axis, panel_label) in enumerate(pans):
        r0 = CAPTION + k * ROW
        word = panel_mask(np.arange(r0, r0 + ROW), axis)
        p = lab[r0:r0 + ROW, LABEL:W]
        margin = int(3 * SIGMA)
        inner = ~grow(~word, 5)                         # the middle of the strokes (16 pixels wide)
        bg = ~grow(word, margin)
        bg[:margin], bg[-margin:], bg[:, :margin], bg[:, -margin:] = False, False, False, False
        ref = np.median(p[bg], 0)
        contrast = np.linalg.norm(p[inner] - ref, axis=1).mean()
        near = grow(word, margin) & ~inner
        near[:margin], near[-margin:], near[:, :margin], near[:, -margin:] = False, False, False, False
        edge = np.percentile(np.linalg.norm(p[near] - ref, axis=1), 99)
        out.append((panel_label, contrast, edge))
    return out, view


def decode(path, args, rotated=False):
    """Decode the first frame to R'G'B' as displayed. For "reference" on a rotated file: zscale on the stored frame
    (-noautorotate), then turned upright here, in RGB, which is the right order."""
    reference = args == "reference"
    if reference:
        args = ["-vf", "zscale,format=gbrp16le"]
    pre = ["-noautorotate"] if reference else []
    probe = subprocess.run([FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                           capture_output=True, text=True, check=True).stdout.split(",")
    w, h = int(probe[0]), int(probe[1])
    if rotated and not reference:
        w, h = h, w                                 # FFmpeg's autorotate turns it upright
    raw = subprocess.run([FFMPEG, "-v", "error"] + pre + ["-i", str(path), "-frames:v", "1"] + args +
                         ["-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    px = np.frombuffer(raw, "<u2").astype(float) / 65535
    if "rgb48le" in args:
        img = px.reshape(h, w, 3)
    else:
        g, b, r = px.reshape(3, h, w)
        img = np.stack([r, g, b], -1)
    return np.rot90(img, -1) if rotated and reference else img


def show(name, results):
    cells = "   ".join(f"{p}: word {c:.3f} edge {e:.3f} {'WRONG' if c > 0.03 else 'ok'}" for p, c, e in results)
    print(f"  {name:26s} {cells}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", type=Path, help="Check files (default: all in sourceimages/)")
    parser.add_argument("--images", type=Path, help="Write the simulated distant views here")
    parser.add_argument("--capture", type=Path, help="A 1:1 screenshot of the chart, cropped to it")
    parser.add_argument("--file", help="With --capture, the name of the file shown")
    args = parser.parse_args()
    if args.capture:
        rgb = np.asarray(Image.open(args.capture).convert("RGB")).astype(float) / 255
        results, _ = measure(rgb, info(args.file)[0])
        show(args.capture.name, results)
        return
    if args.images:
        args.images.mkdir(parents=True, exist_ok=True)
    for path in args.files or sorted(OUT.glob("chroma_siting_check_*")):
        print(path.name)
        pans, rotated = info(path.name)
        decodes = dict(DECODES, **({"reference (rotate in RGB)": "reference"} if rotated else {}))
        for name, dec in decodes.items():
            results, view = measure(decode(path, dec, rotated), pans)
            show(name, results)
            if args.images:
                tag = name.split(" (")[0].replace(", ", "-").replace(" ", "")
                png = args.images / f"{path.stem}-{path.suffix[1:]}-{tag}.png"
                Image.fromarray((np.clip(view, 0, 1) ** (1 / 2.4) * 255).round().astype(np.uint8)).save(png)


if __name__ == "__main__":
    main()
