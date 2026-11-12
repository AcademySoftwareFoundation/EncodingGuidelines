"""
Compare ways of converting RGB to Y'CbCr with ffmpeg, for tests/chip-chart-yuvconvert/compare.html.

Two sources: the chip chart (16-bit RGB PNG) and Resolve's colour bars (10-bit RGB DPX, see
sourceimages/README.md). Each conversion is encoded losslessly with libx264 (-qp 0) at 4:2:2 or 4:4:4 10-bit, then
decoded back to 16-bit RGB with zscale, reading it as BT.709 the way a player would for HD. Every result is decoded
the same way, so only the encode differs. Errors are measured on R, G and B against the source, in 10-bit code
values, from the 16-bit decode; "White Y'" and the pixel probe read the planes stored in the file.

The page is an A/B viewer; see tests/python/yuvcompare.py and yuvcompare_template.html.

Run from the tests folder, with the ffmpeg to test on the PATH (it needs zscale, --enable-libzimg):
    python chip-color-test.py [--outdir ./chip-chart-yuvconvert] [--keep-videos]
"""
import argparse
import os
import sys

import numpy as np
import OpenImageIO as oiio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
import yuvcompare as yc  # noqa: E402

SOURCES = [
    {'id': 'chip', 'label': 'Chip chart', 'path': '../sourceimages/chip-chart-1080-16bit-noicc.png',
     'description': '16-bit RGB PNG, untagged'},
    {'id': 'bars', 'label': 'Colour bars', 'path': '../sourceimages/rp219/smptehdbars_10_resolve.dpx',
     'description': '10-bit full-range RGB DPX from DaVinci Resolve, untagged'},
]

# setparams sets primaries and transfer on the frames (-color_primaries and -color_trc are ignored from FFmpeg 7.1),
# and the encoder and MP4 muxer copy them into the stream and the colr atom. -colorspace and -color_range also set the
# matrix and range of the conversion FFmpeg inserts (7.1 and later).
SETPARAMS = "setparams=color_primaries=bt709:color_trc=iec61966-2-1"
SWS = "-sws_flags spline+accurate_rnd+full_chroma_int"

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

VARIANTS = [
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

STATS = [
    {'key': 'mean', 'label': 'Mean', 'short': 'Mean', 'digits': 2},
    {'key': 'p99', 'label': '99th pct', 'short': '99th', 'digits': 1},
    {'key': 'max', 'label': 'Max', 'short': 'Max', 'digits': 1},
    {'key': 'white', 'label': 'White Y′', 'short': 'White', 'digits': 1, 'signed': True, 'warn': 1,
     'title': "Y′ of the source's 100% white as stored, minus 940 (1023 at full range)"},
]


def groups():
    out = []
    for glabel, pix_fmt, entries in VARIANTS:
        rows = []
        for id_, label, vf, sws, tags, description in entries:
            full = ':range=full' in vf or 'out_range=full' in vf
            flags = []
            if sws:
                flags.append(SWS + ("+full_chroma_inp" if sws == 'inp' else ""))
            filters = [f for f in (vf, SETPARAMS if tags else '') if f]
            if filters:
                flags.append('-vf "%s"' % ",".join(filters))
            if tags:
                flags.append(f"-color_range {'pc' if full else 'tv'} -colorspace bt709")
            flags = " ".join(flags)
            rows.append({
                'id': id_, 'label': label, 'description': description, 'flags': flags,
                'encode': f'ffmpeg -y -i {{src}} -frames:v 1 {flags} -c:v libx264 -preset placebo -qp 0 '
                          f'-pix_fmt {pix_fmt} {{out}}',
                'layout': {'chroma': '422' if '422' in pix_fmt else '444', 'range': 'full' if full else 'limited',
                           'bits': 10, 'rgb': False}})
        out.append((glabel, rows))
    return out


def worst_pixel(path):
    """Where an error map is largest, as fractions of the width and height (to focus a preset on it)."""
    e = np.abs(np.array(oiio.ImageBuf(path).get_pixels(oiio.UINT8)).astype(int) - 128).max(-1)
    y, x = np.unravel_index(np.argmax(e), e.shape)
    return [float(x / e.shape[1]), float(y / e.shape[0])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="./chip-chart-yuvconvert")
    parser.add_argument("--keep-videos", action="store_true",
                        help="keep the encoded .mp4 files (the page only needs the decoded images)")
    args = parser.parse_args()
    root = args.outdir
    version = yc.ffmpeg_version()
    sources, grps, items = yc.run_comparison(root, SOURCES, groups(), 1023, args.keep_videos, ideal_bits=10)
    yc.print_table(version, sources, grps, items, STATS)
    edge = worst_pixel(os.path.join(root, "chip-splinecolormatrix-err.png"))

    yc.write_page(root, {
        'pageTitle': "Y'CbCr Conversion Compare",
        'title': "Comparing RGB to Y'CbCr conversions",
        'lede': ("Each result is an RGB image converted to Y'CbCr by <code>ffmpeg</code>, encoded losslessly, then "
                 "decoded back the same way for all of them. Pick two results, <b>A</b> and <b>B</b>, and wipe or flip "
                 "between them. Errors are against the source, in 10-bit code values."),
        'tableNote': ("Error against the source in 10-bit code values. <b>White</b> is how far the source's 100% white "
                      "lands from its specification value in the file (Y′ 940, or 1023 at full range): libswscale puts "
                      "it too high from 10-bit and higher sources."),
        'unit': '10-bit code values', 'unitName': '10-bit code', 'unitMax': 1023,
        'stats': STATS, 'rankKey': 'mean', 'groups': grps, 'items': items,
        'defaults': {'a': 'source', 'b': 'basic'},
        'presets': [
            {'label': 'Default encode vs zscale', 'src': 'chip', 'a': 'basic', 'b': 'zscale',
             'title': 'The colour shift of a plain encode, against the recommended command'},
            {'label': 'libswscale vs zscale, difference', 'src': 'bars', 'a': 'splinecolormatrix', 'b': 'zscale',
             'mode': 'diff', 'title': 'The bright lines are the bar edges, where the 4:2:2 chroma is placed '
                                      'differently. The white level error (943 instead of 940) is clipped when '
                                      'decoded to RGB; use the probe or the table to see it.'},
            {'label': '4:2:2 chroma edge, 8×', 'src': 'chip', 'a': 'splinecolormatrix', 'b': 'zscale',
             'mode': 'toggle', 'zoom': 8, 'focus': edge,
             'title': 'libswscale centres 4:2:2 chroma; zscale co-sites it, as 4:2:2 formats expect'},
            {'label': 'colormatrix (8-bit) vs zscale, 4:4:4', 'src': 'bars', 'a': 'spline444colormatrix2',
             'b': 'zscale444', 'mode': 'diff'},
        ],
        'footer': (
            f"<p>Made with {version}. Every file is encoded with <code>libx264 -preset placebo -qp 0</code> "
            "(lossless) and decoded with <code>zscale</code> as BT.709, so the only difference is the conversion. "
            "The errors come from the 16-bit decode; the images shown are 8-bit copies, and <i>Difference</i> uses "
            "error maps made from the 16-bit decode. The probe shows the Y′CbCr values stored in each file. The large "
            "maximum errors at 4:2:2 are at the edges of the coloured patches, where the chroma is subsampled.</p>"
            "<p>The results were the same on FFmpeg 6.1.6, 9.0.2 and a 9.1 development build, except "
            "<i>Default encode + colour options</i>, which is only right from 7.1 (before that it matches the default "
            "encode), and libswscale's full-range result, which changed in 8.0. See "
            "<a href='../../FFmpegChanges.html' target='_top'>FFmpeg Version Changes</a> and "
            "<a href='../../ColorPreservation.html' target='_top'>RGB to YCbCr Conversion</a>. "
            "Generated by <a href='../chip-color-test.py' target='_top'>tests/chip-color-test.py</a>.</p>"),
    }, sources)


if __name__ == "__main__":
    main()
