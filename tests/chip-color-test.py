"""
Compare ways of converting RGB to Y'CbCr with ffmpeg, for tests/chip-chart-yuvconvert/compare.html.

Two sources: the chip chart (16-bit RGB PNG) and Resolve's colour bars (10-bit RGB DPX, see
sourceimages/README.md). Each conversion is encoded losslessly with libx264 (-qp 0) at 4:2:2 or 4:4:4 10-bit, then
decoded back to 16-bit RGB with zscale, reading it as BT.709 the way a player would for HD. Every result is decoded
the same way, so only the encode differs. Errors are measured on R, G and B against the source, in 10-bit code
values, from the 16-bit decode; the PNGs on the page are 8-bit copies for display.

The page is an A/B viewer (tests/python/yuvcompare_template.html) with the results written into it.

Run from the tests folder, with the ffmpeg to test on the PATH (it needs zscale, --enable-libzimg):
    python chip-color-test.py [--outdir ./chip-chart-yuvconvert] [--keep-videos]
"""
import argparse
import json
import os
import subprocess
import sys

import zlib

import numpy as np
import OpenImageIO as oiio

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "python", "yuvcompare_template.html")

SOURCES = [
    {'id': 'chip', 'label': 'Chip chart', 'path': '../sourceimages/chip-chart-1080-16bit-noicc.png',
     'description': '16-bit RGB PNG, untagged'},
    {'id': 'bars', 'label': 'Colour bars', 'path': '../sourceimages/rp219/smptehdbars_10_resolve.dpx',
     'description': '10-bit full-range RGB DPX from DaVinci Resolve, untagged'},
]

# Tags for the encode. setparams sets primaries and transfer on the frames (-color_primaries and -color_trc are
# ignored from FFmpeg 7.1), and the encoder and MP4 muxer copy them into the stream and the colr atom.
# -colorspace and -color_range also set the matrix and range of the conversion FFmpeg inserts (7.1 and later).
SETPARAMS = "setparams=color_primaries=bt709:color_trc=iec61966-2-1"
TAGS = "-color_range {tv} -colorspace bt709"
SWS = "-sws_flags spline+accurate_rnd+full_chroma_int"

# Decode as a player would for HD: BT.709, at the range the file is tagged with (or limited, if untagged).
# zscale cannot output packed RGB, so it outputs planar 16-bit.
DECODE = "zscale=matrixin=709:rangein={range}:range=full:filter=spline36,format=gbrp16le"

COLORMATRIX = ("colormatrix converts Y'CbCr from one matrix to another, here from BT.601 (bt470bg), which is what "
               "the conversion FFmpeg inserts in front of it produces, on every version tested. It works in 8-bit, "
               "so it is the least accurate filter here. Not recommended.")
COLORSPACE = ("colorspace converts Y'CbCr between matrices, at up to 12-bit. Here it is told the input is BT.601, "
              "which is what the conversion FFmpeg inserts in front of it produces. Close, but the image is "
              "converted twice, and libswscale still does the RGB conversion.")
LIBSWSCALE = ("libswscale, with the flags that get the most out of it. The matrix is right, but from 10-bit and "
              "higher sources limited-range white is 943 instead of 940{chroma}.")
ZSCALE = ("zscale (zimg): the conversion these guidelines recommend. Exact matrix and range, and co-sited chroma. "
          "Needs an ffmpeg built with --enable-libzimg.")

GROUPS = [
    ('4:2:2 10-bit', 'yuv422p10le', [
        ('basic', 'Default encode (wrong)', '', False, False,
         "No filter and no colour options. FFmpeg converts with BT.601 and leaves the file untagged, but players "
         "assume BT.709 for HD, so the colours shift. The same on every version."),
        ('basictagged', 'Default encode + colour options', '', False, True,
         "No filter, but with -colorspace bt709. From FFmpeg 7.1 that also sets the matrix of the conversion FFmpeg "
         "inserts, so the matrix is right; before 7.1 it only tagged the file and the pixels were still BT.601. "
         "The conversion is libswscale's, with its white level and centred chroma."),
        ('colormatrix', 'colormatrix filter', 'colormatrix=bt470bg:bt709', True, True, COLORMATRIX),
        ('colorspace', 'colorspace filter', 'colorspace=bt709:iall=bt601-6-625:fast=1', True, True, COLORSPACE),
        ('splinecolormatrix', 'scale (libswscale) + flags', 'scale=in_color_matrix=bt709:out_color_matrix=bt709',
         'inp', True, LIBSWSCALE.format(chroma=", and the 4:2:2 chroma is centred instead of co-sited")),
        ('zscale', 'zscale (recommended)', 'zscale=matrix=709:range=limited:filter=lanczos', False, True, ZSCALE),
    ]),
    ('4:4:4 10-bit', 'yuv444p10le', [
        ('basic444', 'Default encode (wrong)', '', False, False,
         "No filter and no colour options, at 4:4:4: BT.601 and untagged."),
        ('basic444tagged', 'Default encode + colour options', '', False, True,
         "No filter, but with -colorspace bt709. The matrix is right from FFmpeg 7.1; the conversion is "
         "libswscale's."),
        ('spline444colormatrix2', 'colormatrix filter', 'colormatrix=bt470bg:bt709', True, True, COLORMATRIX),
        ('spline444colorspace', 'colorspace filter', 'colorspace=bt709:iall=bt601-6-625:fast=1', True, True,
         COLORSPACE),
        ('spline444out_color_matrix', 'scale (libswscale) + flags',
         'scale=in_color_matrix=bt709:out_color_matrix=bt709', 'inp', True, LIBSWSCALE.format(chroma="")),
        ('spline444out_color_matrixfull', 'scale (libswscale) + flags, full range',
         'scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709', 'inp', True,
         "libswscale to full-range Y'CbCr. From FFmpeg 8.0 its full-range output is slightly too bright at 10-bit "
         "and above (see FFmpeg Version Changes)."),
        ('zscale444', 'zscale (recommended)', 'zscale=matrix=709:range=limited:filter=lanczos', False, True, ZSCALE),
        ('zscale444full', 'zscale, full range', 'zscale=matrix=709:range=full:filter=lanczos', False, True,
         "zscale to full-range Y'CbCr."),
    ]),
]


def read_rgb(path):
    return np.array(oiio.ImageBuf(path).get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)


def write_display_png(img, path):
    """8-bit copy for the page."""
    spec = oiio.ImageSpec(img.shape[1], img.shape[0], 3, oiio.UINT8)
    out = oiio.ImageOutput.create(path)
    out.open(path, spec)
    out.write_image(np.round(np.clip(img, 0, 1) * 255).astype(np.uint8))
    out.close()


ERR_STEPS = 4   # error maps: 128 is no error, each step is 1/ERR_STEPS of a 10-bit code (range about +-32 codes)


def write_error_png(diff10, path):
    """Signed error against the source (10-bit codes), as an 8-bit RGB PNG with no colour chunks, so the page can
    subtract two of them exactly in a canvas."""
    import struct
    import zlib
    img = np.clip(np.round(diff10 * ERR_STEPS) + 128, 0, 255).astype(np.uint8)
    h, w = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def run(cmd, binary=False):
    print("\n" + cmd)
    r = subprocess.run(cmd, shell=True, capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode()[-3000:])
    return r.stdout


def decode(video, rng, w, h):
    cmd = 'ffmpeg -v error -i {} -frames:v 1 -vf "{}" -f rawvideo -'.format(video, DECODE.format(range=rng))
    g, b, r = np.frombuffer(run(cmd), "<u2").reshape(3, h, w).astype(np.float64) / 65535
    return np.stack([r, g, b], -1), cmd.replace(" -v error", "").replace("-f rawvideo -", "decoded.png")


def raw_planes(video, pix_fmt):
    """The file's Y'CbCr planes as stored (10-bit, little-endian), with no conversion."""
    return run(f"ffmpeg -v error -i {video} -frames:v 1 -f rawvideo -pix_fmt {pix_fmt} -")


def write_planes(raw, path):
    """Raw planes for the page's pixel probe: Y', then Cb, then Cr, uint16 little-endian, zlib-compressed."""
    with open(path, "wb") as f:
        f.write(zlib.compress(raw, 9))


def ideal_ycbcr(rgb):
    """BT.709 limited-range 10-bit Y'CbCr of the source, rounded: what a perfect 4:4:4 conversion stores."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    planes = [64 + 876 * y, 512 + 896 * (b - y) / 1.8556, 512 + 896 * (r - y) / 1.5748]
    return b"".join(np.clip(np.round(p), 0, 1023).astype("<u2").tobytes() for p in planes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="./chip-chart-yuvconvert")
    parser.add_argument("--keep-videos", action="store_true",
                        help="keep the encoded .mp4 files (the page only needs the decoded PNGs)")
    args = parser.parse_args()
    root = args.outdir
    os.makedirs(root, exist_ok=True)
    version = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    version = version.split(" Copyright")[0].replace("ffmpeg version ", "FFmpeg ")

    sources, items, groups, focus = [], {}, [], {}
    for s in SOURCES:
        src = read_rgb(s['path'])
        h, w = src.shape[:2]
        s.update(image=f"{s['id']}-source.png", width=w, height=h, data=src,
                 white=np.all(src >= 1.0 - 1e-6, axis=-1))
        write_display_png(src, os.path.join(root, s['image']))
        s['planes'] = f"{s['id']}-source-ideal.yuv.z"
        write_planes(ideal_ycbcr(src), os.path.join(root, s['planes']))
        ys, xs = np.nonzero(s['white'])
        focus[s['id'], 'white'] = [float(xs.mean() / w), float(ys.mean() / h)] if len(xs) else [0.5, 0.5]
        sources.append(s)

    for glabel, pix_fmt, entries in GROUPS:
        groups.append({'label': glabel, 'items': [e[0] for e in entries]})
        for id_, label, vf, sws, tags, description in entries:
            full = 'full' in vf.split(':range=')[-1] or 'out_range=full' in vf
            rng, tv = ('full', 'pc') if full else ('limited', 'tv')
            flags = []
            if sws:
                flags.append(SWS + ("+full_chroma_inp" if sws == 'inp' else ""))
            filters = [f for f in (vf, SETPARAMS if tags else '') if f]
            if filters:
                flags.append('-vf "%s"' % ",".join(filters))
            if tags:
                flags.append(TAGS.format(tv=tv))
            flags = " ".join(flags)
            it = {'label': label, 'group': glabel, 'description': description, 'flags': flags, 'results': {},
                  'chroma': '422' if '422' in pix_fmt else '444', 'range': rng}
            for s in sources:
                video = os.path.join(root, f"{s['id']}-{id_}.mp4")
                enc = (f'ffmpeg -y -i {s["path"]} -frames:v 1 {flags} -c:v libx264 -preset placebo -qp 0 '
                       f'-pix_fmt {pix_fmt} {video}')
                run(enc)
                out, dec = decode(video, rng, s['width'], s['height'])
                image = f"{s['id']}-{id_}.png"
                write_display_png(out, os.path.join(root, image))
                diff = (out - s['data']) * 1023
                errimage = f"{s['id']}-{id_}-err.png"
                write_error_png(diff, os.path.join(root, errimage))
                err = np.abs(diff)
                # Y' of 100% white against the specification: 940 limited, 1023 full range.
                raw = raw_planes(video, pix_fmt)
                planes = f"{s['id']}-{id_}.yuv.z"
                write_planes(raw, os.path.join(root, planes))
                white = None
                if s['white'].any():
                    yplane = np.frombuffer(raw, "<u2")[:s['width'] * s['height']].reshape(s['height'], s['width'])
                    white = float(yplane[s['white']].mean()) - (1023 if full else 940)
                it['results'][s['id']] = {
                    'image': image, 'err': errimage, 'planes': planes, 'encode': enc, 'decode': dec.replace(video, os.path.basename(video)),
                    'mean': round(float(err.mean()), 3), 'p99': round(float(np.percentile(err, 99)), 2),
                    'max': round(float(err.max()), 2), 'white': None if white is None else round(white, 2)}
                if not args.keep_videos:
                    os.remove(video)
                if id_ == 'splinecolormatrix' and s['id'] == 'chip':
                    yx = np.unravel_index(np.argmax(err.max(-1)), err.shape[:2])
                    focus['chip', 'edge'] = [float(yx[1] / s['width']), float(yx[0] / s['height'])]
            items[id_] = it

    print("\n" + version)
    print("| Encode | Conversion | " + " | ".join(f"{s['label']} mean | 99th | max | white" for s in sources) + " |")
    print("| :--- | :--- |" + " ---: | ---: | ---: | ---: |" * len(sources))
    for g in groups:
        for id_ in g['items']:
            cells = []
            for s in sources:
                r = items[id_]['results'][s['id']]
                cells.append(f"{r['mean']:.2f} | {r['p99']:.1f} | {r['max']:.1f} | "
                             + ("–" if r['white'] is None else f"{r['white']:+.1f}"))
            print(f"| {g['label']} | {items[id_]['label']} | " + " | ".join(cells) + " |")

    data = {
        'sources': [{k: s[k] for k in ('id', 'label', 'description', 'image', 'width', 'height', 'planes')}
                    for s in sources],
        'groups': groups, 'items': items, 'errSteps': ERR_STEPS,
        'defaults': {'a': 'source', 'b': 'basic'},
        'presets': [
            {'label': 'Default encode vs zscale', 'src': 'chip', 'a': 'basic', 'b': 'zscale',
             'title': 'The colour shift of a plain encode, against the recommended command'},
            {'label': 'libswscale vs zscale, difference', 'src': 'bars', 'a': 'splinecolormatrix', 'b': 'zscale',
             'mode': 'diff', 'title': 'The bright lines are the bar edges, where the 4:2:2 chroma is placed '
                                      'differently. The white level error (943 instead of 940) is clipped when '
                                      'decoded to RGB, so it only shows in the table.'},
            {'label': '4:2:2 chroma edge, 8×', 'src': 'chip', 'a': 'splinecolormatrix', 'b': 'zscale',
             'mode': 'toggle', 'zoom': 8, 'focus': focus.get(('chip', 'edge'), [0.5, 0.5]),
             'title': 'libswscale centres 4:2:2 chroma; zscale co-sites it, as 4:2:2 formats expect'},
            {'label': 'colormatrix (8-bit) vs zscale, 4:4:4', 'src': 'bars', 'a': 'spline444colormatrix2',
             'b': 'zscale444', 'mode': 'diff'},
        ],
        'footer': (
            f"<p>Made with {version}. Every file is encoded with <code>libx264 -preset placebo -qp 0</code> "
            "(lossless) and decoded with <code>zscale</code> as BT.709, so the only difference is the conversion. "
            "The errors come from the 16-bit decode; the images shown are 8-bit copies, so differences below one "
            "8-bit step (four 10-bit codes) may not show in <i>Difference</i>. The large maximum errors at 4:2:2 are "
            "at the edges of the coloured patches, where the chroma is subsampled.</p>"
            "<p>The results were the same on FFmpeg 6.1.6, 9.0.2 and a 9.1 development build, except "
            "<i>Default encode + colour options</i>, which is only right from 7.1 (before that it matches the default "
            "encode), and libswscale's full-range result, which changed in 8.0. See "
            "<a href='../../FFmpegChanges.html' target='_top'>FFmpeg Version Changes</a> and "
            "<a href='../../ColorPreservation.html' target='_top'>RGB to YCbCr Conversion</a>. "
            "Generated by <a href='../chip-color-test.py' target='_top'>tests/chip-color-test.py</a>.</p>"),
    }
    with open(TEMPLATE) as f:
        html = f.read().replace("/*DATA*/null", json.dumps(data, indent=1))
    with open(os.path.join(root, "compare.html"), "w") as f:
        f.write(html)
    print("Written", os.path.join(root, "compare.html"))


if __name__ == "__main__":
    main()
