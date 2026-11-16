"""
Show how a chroma siting mismatch builds up over repeated round trips, for ChromaSiting.md.

A small RGB test image (coloured text and single-pixel coloured lines on grey) goes through 1, 5 and 10
generations of RGB -> Y'CbCr 4:2:2 10-bit -> RGB, all with zscale, so the only difference is the siting:

  * right: the encoder writes co-sited chroma (zscale's default) and the player assumes co-sited.
  * wrong: the encoder writes centred chroma (chromal=center, which is where libswscale puts it) and the
    player assumes co-sited, as players do for 4:2:2.

The decoder is bilinear, as in most players. Using zscale for both keeps libswscale's other errors (for
example its white level) out of the comparison.

Writes tests/chroma-siting/images/generations.png (the figure: rows are generations, columns right and wrong,
zoomed with nearest neighbour) and prints the measurements: how far the colour has moved left against the luma, and
the error against the source, in 10-bit RGB code values.

Uses the ffmpeg on the PATH (or FFMPEG_BIN):
    python tests/chroma_siting_generations.py
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / "chroma-siting" / "images"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
W, H = 240, 64
GREY = 0.45
GENERATIONS = (1, 5, 10)
ENCODE = "zscale=matrix=709:range=limited:filter=lanczos{loc},format=yuv422p10le"
DECODE = "zscale=range=full:chromalin=left:filter=bilinear,format=gbrp16le"
MODES = {"right": "", "wrong": ":chromal=center"}
ZOOM = 3


def source():
    """Coloured text and single-pixel coloured lines on grey, as float RGB."""
    buf = oiio.ImageBuf(oiio.ImageSpec(W, H, 3, oiio.FLOAT))
    oiio.ImageBufAlgo.fill(buf, (GREY, GREY, GREY))
    oiio.ImageBufAlgo.render_text(buf, 6, 26, "Colour", 24, "", (0.85, 0.08, 0.08))
    oiio.ImageBufAlgo.render_text(buf, 92, 26, "detail", 24, "", (0.10, 0.20, 0.95))
    img = np.array(buf.get_pixels(oiio.FLOAT)).reshape(H, W, 3)
    colours = [(0.9, 0.1, 0.1), (0.1, 0.75, 0.1), (0.1, 0.2, 0.95), (0.95, 0.85, 0.1)]
    for i, x in enumerate(range(12, 228, 9)):   # alternate even and odd columns
        img[38:58, x] = colours[i % 4]
    return np.clip(img, 0, 1)


def generations(img, mode, n):
    """Run n round trips in one filter graph; return float RGB."""
    graph = ",".join([ENCODE.format(loc=MODES[mode]) + "," + DECODE] * n)
    raw = (np.round(img * 65535)).astype("<u2").tobytes()
    r = subprocess.run([FFMPEG, "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}",
                        "-i", "-", "-vf", graph, "-f", "rawvideo", "-pix_fmt", "gbrp16le", "-"],
                       input=raw, capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(r.stderr.decode())
    g, b, r_ = np.frombuffer(r.stdout, "<u2").reshape(3, H, W).astype(float) / 65535
    return np.stack([r_, g, b], -1)


def cb(img):
    return (img[..., 2] - (0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2])) / 1.8556


def shift(src, out):
    """Horizontal shift of the chroma (Cb) against the source, in pixels, from the cross-correlation peak."""
    a, b = cb(src) - cb(src).mean(), cb(out) - cb(out).mean()
    lags = np.arange(-4, 5)
    c = np.array([(a[:, 8:-8] * np.roll(b, -k, 1)[:, 8:-8]).sum() for k in lags])
    i = int(np.argmax(c))
    if 0 < i < len(c) - 1:
        return lags[i] + 0.5 * (c[i - 1] - c[i + 1]) / (c[i - 1] - 2 * c[i] + c[i + 1])
    return float(lags[i])


def tile(img):
    return np.repeat(np.repeat(img, ZOOM, 0), ZOOM, 1)


def label(img, text, x, y, size=16):
    buf = oiio.ImageBuf(np.ascontiguousarray(img.astype(np.float32)))
    oiio.ImageBufAlgo.render_text(buf, x, y, text, size, "", (0.92, 0.92, 0.94))
    return np.array(buf.get_pixels(oiio.FLOAT)).reshape(img.shape)


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    src = source()
    v = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    print(v)
    print("| Round trips | Setting | Colour moved left (px) | Mean error | 99th percentile error |")
    print("| :--- | :--- | ---: | ---: | ---: |")
    tw, th, pad, left, top = W * ZOOM, H * ZOOM, 16, 150, 36
    fig = np.full((top + (len(GENERATIONS) + 1) * (th + pad), left + 2 * tw + pad, 3), 0.12)
    fig = label(fig, "Right: co-sited", left, 24)
    fig = label(fig, "Wrong: centred, read as co-sited", left + tw + pad, 24)
    y = top
    fig[y:y + th, left:left + tw] = tile(src)
    fig = label(fig, "Source", 12, y + th // 2 + 6)
    for n in GENERATIONS:
        y += th + pad
        fig = label(fig, f"{n} round trip{'s' if n > 1 else ''}", 12, y + th // 2 + 6)
        for col, mode in enumerate(MODES):
            out = generations(src, mode, n)
            err = np.abs(out - src)[:, 8:-8] * 1023
            print(f"| {n} | {mode} | {-shift(src, out):.2f} | {err.mean():.2f} | {np.percentile(err, 99):.1f} |")
            x = left + col * (tw + pad)
            fig[y:y + th, x:x + tw] = tile(out)
    path = OUTDIR / "generations.png"
    spec = oiio.ImageSpec(fig.shape[1], fig.shape[0], 3, oiio.UINT8)
    out = oiio.ImageOutput.create(str(path))
    out.open(str(path), spec)
    out.write_image(np.round(np.clip(fig, 0, 1) * 255).astype(np.uint8))
    out.close()
    print("Written", path)


if __name__ == "__main__":
    main()
