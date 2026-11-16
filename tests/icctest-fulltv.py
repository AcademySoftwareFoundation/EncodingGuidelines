"""
Compare full-range and limited (TV) range encodes, and zscale's dither modes, for tests/greyramp-fulltv/compare.html.

Sources: a 256-step 8-bit grey ramp (made here), a continuous 16-bit ramp, the 8-bit radial gradient, a 16-bit
version of it (sourceimages/make_gradients_16bit.py) and part of the Marcie scan. Each variant is encoded the
way a web review file would be (libx264 -crf 18, as in ColorPreservation.md), with zscale for the conversion and
setparams for the primaries and transfer. The page shows each result two ways:

  * Measured: the file decoded by zscale, reading the range from the file (or limited, if the file does not say),
    as a player should. Errors against the source are in 8-bit code values, from a 16-bit decode; "White Y'" and the
    pixel probe read the planes stored in the file; "Y' levels" counts the different Y' values in the file.
  * Your browser: the .mp4 itself, played by whatever browser is viewing the page. That is the real test for web
    review, and it is why the videos are kept.

Run from the tests folder, with the ffmpeg to test on the PATH (it needs zscale, --enable-libzimg):
    python icctest-fulltv.py [--outdir ./greyramp-fulltv]
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
import yuvcompare as yc  # noqa: E402

SETPARAMS = "setparams=color_primaries=bt709:color_trc=iec61966-2-1"
INPUT = "ffmpeg -y -loop 1 -framerate 24 -i {src} -frames:v 24"
X264 = "-c:v libx264 -preset slow -crf 18"


def zscale(rng, dither=None):
    d = f":dither={dither}" if dither else ""
    return f"zscale=matrix=709:range={rng}:filter=lanczos{d},{SETPARAMS}"


def variant(id_, label, description, pix_fmt, vf, tags, codec=X264, layout=None, decode_range=None):
    flags = f'-pix_fmt {pix_fmt} -vf "{vf}" {tags}'.strip()
    v = {'id': id_, 'label': label, 'description': description, 'flags': flags,
         'encode': f"{INPUT} {flags} {codec} {{out}}", 'layout': layout}
    if decode_range:
        v['decode_range'] = decode_range
    return v


L420 = {'chroma': '420', 'range': 'limited', 'bits': 8, 'rgb': False}
F420 = dict(L420, range='full')

DITHER = {
    'ordered': "an ordered (Bayer) pattern, which spreads the rounding error in a fixed, fine grid",
    'random': "random noise, which hides banding but adds grain",
    'error_diffusion': "error diffusion, which carries each pixel's rounding error to its neighbours",
}


def dither_variants(prefix, bits_label, pix_fmt, layout):
    """The same limited-range encode with each zscale dither mode; prefix is the dither=none variant's id."""
    return [variant(f"{prefix}_{d}", f"{bits_label}, dither={d}",
                    f"As the dither=none encode, with zscale's {d} dither: {text}. The encode (-crf 18) may smooth "
                    "some of the dither away.",
                    pix_fmt, zscale('limited', d), '-color_range tv -colorspace bt709', layout=layout)
            for d, text in DITHER.items()]


GROUPS = [
    ('8-bit 4:2:0 limited range: zscale dither (plays in every browser)', [
        variant('tv', 'Limited range (normal), dither=none',
                "The usual encode: Y′ from 16 to 235, with zscale's default (no dither). A 256-step source has to fit "
                "into 220 steps, so some neighbouring values merge (look at Y′ levels on the grey ramp).",
                'yuv420p', zscale('limited'), '-color_range tv -colorspace bt709', layout=L420),
        *dither_variants('tv', '8-bit limited', 'yuv420p', L420),
    ]),
    ('8-bit 4:2:0 full range (plays in every browser)', [
        variant('full', 'Full range, tagged',
                "Y′ from 0 to 255, and the file says so (-color_range pc), so the decoder expands it correctly. Every "
                "8-bit source level keeps its own code.",
                'yuv420p', zscale('full'), '-color_range pc -colorspace bt709', layout=F420),
        variant('fullj', 'Full range, yuvj420p',
                "The older way of asking for full range, with the JPEG pixel format. FFmpeg is deprecating yuvj420p; "
                "it gives the same file as yuv420p with -color_range pc.",
                'yuvj420p', zscale('full'), '-color_range pc -colorspace bt709', layout=F420),
        variant('fulluntagged', 'Full range, labelled limited (wrong)',
                "Full-range pixels in a file that says limited range, so it is decoded as limited: blacks are "
                "crushed and whites clipped. Made here by relabelling zscale's full-range output as limited "
                "(setparams=range=tv). Older guides got this by accident with -color_range unknown: FFmpeg 6.1 then "
                "writes no full-range flag, while 9.0 keeps the frames' full-range tag.",
                'yuv420p', zscale('full') + ",setparams=range=tv", '-color_range tv -colorspace bt709',
                layout=F420, decode_range='limited'),
    ]),
    ('10-bit 4:2:0 limited range: zscale dither (H.264 High 10)', [
        variant('tv10', '10-bit limited, dither=none',
                "10-bit 4:2:0 (H.264 High 10). Four times as many steps, so limited range costs nothing visible.",
                'yuv420p10le', zscale('limited'), '-color_range tv -colorspace bt709',
                layout=dict(L420, bits=10)),
        *dither_variants('tv10', '10-bit limited', 'yuv420p10le', dict(L420, bits=10)),
    ]),
    ('Others (check which browsers play them)', [
        variant('full444', '8-bit 4:4:4, full range',
                "No chroma subsampling (H.264 High 4:4:4 Predictive). Not every browser plays it.",
                'yuv444p', zscale('full'), '-color_range pc -colorspace bt709',
                layout=dict(F420, chroma='444')),
        {'id': 'rgb', 'label': 'RGB (libx264rgb)',
         'description': "H.264 storing RGB directly, with no conversion and no range question. Browsers do not play it.",
         'flags': '-c:v libx264rgb',
         'encode': f"{INPUT} -pix_fmt rgb24 -vf {SETPARAMS} -c:v libx264rgb -preset slow -crf 18 {{out}}",
         'layout': {'chroma': '444', 'range': 'full', 'bits': 8, 'rgb': True}},
    ]),
]

STATS = [
    {'key': 'mean', 'label': 'Mean', 'short': 'Mean', 'digits': 2},
    {'key': 'p99', 'label': '99th pct', 'short': '99th', 'digits': 1},
    {'key': 'max', 'label': 'Max', 'short': 'Max', 'digits': 1},
    {'key': 'white', 'label': 'White Y′', 'short': 'White', 'digits': 1, 'signed': True, 'warn': 1,
     'title': "Y′ of the source's 100% white as stored, minus its specification value (235 limited, 255 full; "
              "940 and 1023 at 10-bit)"},
    {'key': 'cambi', 'label': 'Banding (CAMBI)', 'short': 'CAMBI', 'digits': 1,
     'title': "Netflix's CAMBI banding index (libvmaf), on the file alone: 0 is no banding, higher is more visible "
              "banding. Compare with the source's own score on its card."},
    {'key': 'levels', 'label': 'Y′ levels', 'short': 'Levels', 'digits': 0,
     'title': "How many different Y′ values (G for RGB) the file uses. The 256-step grey ramp can use at most 220 "
              "in 8-bit limited range."},
]


def make_greyramp(path, colwidth=4, height=150):
    """256 grey steps, each colwidth pixels wide: 8-bit RGB with no colour chunks."""
    row = np.repeat(np.arange(256, dtype=np.uint8), colwidth)
    img = np.repeat(np.repeat(row[None, :, None], height, 0), 3, 2)
    yc.write_raw_png(np.ascontiguousarray(img), path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="./greyramp-fulltv")
    args = parser.parse_args()
    root = args.outdir
    os.makedirs(root, exist_ok=True)
    ramp = os.path.join(root, "greyscale-raw.png")
    make_greyramp(ramp)
    # A 640x360 part of the Marcie scan (face and hair), at 1:1, to keep the page's files small.
    marcie = os.path.join(root, "marcie-crop.png")
    yc.run(f"ffmpeg -v error -y -i ../sourceimages/Digital_LAD_raw.png -vf crop=640:360:300:200 -pix_fmt rgb48be "
           f"-frames:v 1 {marcie}")
    sources = [
        {'id': 'greyscale', 'label': 'Grey ramp (8-bit)', 'path': ramp,
         'description': '256 grey steps, 8-bit RGB PNG: shows which levels survive'},
        {'id': 'greyramp16', 'label': 'Grey ramp (16-bit)', 'path': '../sourceimages/greyramp-16bit.png',
         'description': 'a continuous 16-bit ramp, no steps of its own (sourceimages/make_gradients_16bit.py)'},
        {'id': 'radialgrad', 'label': 'Radial gradient (8-bit)', 'path': '../sourceimages/radialgrad.png',
         'description': '8-bit RGB PNG, as in the ColorPreservation example'},
        {'id': 'radialgrad16', 'label': 'Radial gradient (16-bit)', 'path': '../sourceimages/radialgrad-16bit.png',
         'description': 'the same gradient made at 16-bit (sourceimages/make_gradients_16bit.py)'},
        {'id': 'marcie', 'label': 'Marcie', 'path': marcie,
         'description': '640×360 of the 16-bit Kodak Digital LAD scan (sourceimages/Digital_LAD_raw.png), as stored'},
    ]
    version = yc.ffmpeg_version()
    srcs, grps, items = yc.run_comparison(root, sources, GROUPS, 255, keep_videos=True, ideal_bits=8, error_maps=False,
                                          banding=True)
    yc.print_table(version, srcs, grps, items, STATS)

    yc.write_page(root, {
        'pageTitle': "Range and Dither Compare",
        'title': "Full range vs. limited (TV) range vs. dithering",
        'lede': ("The same images encoded for web review at limited range (Y′ 16 to 235) and at full range (0 to 255), "
                 "each of zscale's dither modes, and some alternatives. <b>Measured</b> shows each file decoded by <code>zscale</code>, reading the "
                 "range from the file, with errors against the source in 8-bit code values. <b>Your browser</b> plays "
                 "the actual video files, which is the real test of whether a browser handles full range."),
        'tableNote': ("Error against the source in 8-bit code values (lossy encodes, -crf 18). <b>White</b> is how far "
                      "100% white lands from its specification value in the file. <b>Levels</b> is how many different "
                      "Y′ values the file uses: on the 8-bit grey ramp, limited range cannot keep all 256. "
                      "<b>CAMBI</b> is Netflix's banding index (0 is none); each source's own score is on its card. "
                      "Dither raises the plain error slightly and lowers the banding."),
        'unit': '8-bit code values', 'unitName': '8-bit code', 'unitMax': 255,
        'stats': STATS, 'rankKey': 'mean', 'groups': grps, 'items': items, 'videos': True,
        'rowLabel': 'Encode',
        'defaults': {'a': 'tv', 'b': 'full'},
        'presets': [
            {'label': 'Your browser: limited vs full', 'src': 'radialgrad', 'a': 'tv', 'b': 'full', 'show': 'browser',
             'title': 'Both should look the same as the source; if full range looks washed out or crushed, this '
                      'browser ignores the range tag'},
            {'label': 'Your browser: full range labelled limited', 'src': 'radialgrad', 'a': 'full',
             'b': 'fulluntagged', 'show': 'browser', 'mode': 'toggle'},
            {'label': 'Grey ramp steps, difference', 'src': 'greyscale', 'a': 'source', 'b': 'tv', 'mode': 'diff',
             'title': 'Where limited range merges neighbouring grey levels'},
            {'label': '8-bit dither: none vs random, 16-bit gradient', 'src': 'radialgrad16', 'a': 'tv',
             'b': 'tv_random', 'mode': 'toggle', 'zoom': 2, 'focus': [0.5, 0.7],
             'title': 'Without dither the gradient bands (CAMBI 22.4); random dither swaps the bands for fine grain '
                      '(5.6)'},
            {'label': '8-bit dither: ordered vs random', 'src': 'radialgrad16', 'a': 'tv_ordered', 'b': 'tv_random',
             'mode': 'toggle', 'zoom': 4, 'focus': [0.5, 0.7],
             'title': 'Ordered dither leaves a regular pattern; random reads as grain'},
            {'label': 'yuvj420p vs yuv420p full', 'src': 'radialgrad', 'a': 'full', 'b': 'fullj', 'mode': 'diff',
             'title': 'Identical: black everywhere'},
        ],
        'footer': (
            f"<p>Made with {version}. Every file is encoded with <code>libx264 -preset slow -crf 18</code>, 24 frames "
            "of the still image, so the measured errors include some compression. <i>Measured</i> decodes the first "
            "frame with <code>zscale</code> as BT.709, at the range the file is tagged with (limited if it is not "
            "tagged, as players assume). <i>Your browser</i> plays the .mp4 files themselves; the source is the PNG. "
            "We have seen full range work in Chrome, Safari and Firefox, and in RV.</p>"
            "<p>zscale's dither (none by default) matters at 8-bit. By CAMBI, ordered and random cut the banding on "
            "every gradient by half or more; random did best on the radial gradients, ordered on the plain ramps, "
            "and error diffusion helped least. Dither slightly raises the per-pixel error, and it survives -crf 18. "
            "From a 16-bit source, 10-bit needs no dither. CAMBI reads the stored values, so it does not see a range "
            "mislabel. All results were the same on FFmpeg 6.1.6 and 9.0.2.</p>"
            "<p>See <a href='../../Quickstart.html#tv-vs-full-range-' target='_top'>TV vs. Full range</a> and "
            "<a href='../../ColorPreservation.html' target='_top'>RGB to YCbCr Conversion</a>. "
            "Generated by <a href='../icctest-fulltv.py' target='_top'>tests/icctest-fulltv.py</a>.</p>"),
    }, srcs)


if __name__ == "__main__":
    main()
