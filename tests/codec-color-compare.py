"""
Compare the colors of each codec, bit depth and chroma layout, for tests/codec-color-compare/compare.html.

The encodes use the same settings as the browser compatibility page (enctests/test_wedge_configs/codec_web_tests.yml):
H.264, HEVC, VP9 and AV1 at 8, 10 and 12-bit, in Y'CbCr 4:2:0, 4:2:2 and 4:4:4 (converted with zscale) and in RGB.
The page shows each result two ways:
  * Measured: the file decoded by FFmpeg (zscale, BT.709), so you can see what the file itself contains.
  * Your browser: the .mp4 itself, played by the browser viewing the page, with no screenshot or capture in
    between. Comparing the two shows whether a color shift comes from the encode or from the browser's decoder.
Run from the tests folder, with the ffmpeg to test on the PATH (it needs zscale, --enable-libzimg):
    python codec-color-compare.py [--outdir ./codec-color-compare]
The output (compare.html and about 23MB of movies) is not committed or published; open compare.html from the local
Jekyll server (bundle exec jekyll serve --config _config_local.yml, then /tests/codec-color-compare/compare.html).
"""
import argparse
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
import yuvcompare as yc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "..", "enctests", "test_wedge_configs", "codec_web_tests.yml")
# Half a second at 24 fps, looped by the page: enough for a player to settle, small enough to keep the page light.
INPUT = "ffmpeg -y -loop 1 -framerate 24 -i {src} -frames:v 12"

CODEC_NAMES = {'libx264': 'H.264', 'libx264rgb': 'H.264', 'libx265': 'HEVC', 'vp9': 'VP9',
               'libsvtav1': 'AV1', 'libaom-av1': 'AV1'}
CODEC_ORDER = ['H.264', 'HEVC', 'VP9', 'AV1']
LAYOUTS = {'420': ("4:2:0", 'limited', False), '422': ("4:2:2", 'limited', False),
           '444': ("4:4:4", 'limited', False), 'rgb': ("RGB", 'full', True)}


def variants_from_config():
    """One variant per wedge of codec_web_tests.yml, grouped by bit depth."""
    with open(CONFIG) as f:
        config = yaml.safe_load(f)
    groups = {}
    for test_name, test in config.items():
        _, bits, layout_key = test_name.split("_")          # test_10_422
        bits = int(bits)
        layout_label, rng, rgb = LAYOUTS[layout_key]
        for wedge, args in test['wedges'].items():
            codec = CODEC_NAMES[wedge]
            flags = " ".join(f"{k} {v}" for k, v in args.items())
            groups.setdefault(bits, []).append({
                'id': f"{codec.replace('.', '').lower()}_{layout_key}_{bits}",
                'label': f"{codec} {layout_label}",
                'description': (f"{codec} ({args['-c:v']}), {bits}-bit {layout_label}"
                                + (", stored as RGB with no Y′CbCr conversion" if rgb else
                                   ", converted from RGB with zscale (BT.709, limited range)")
                                + ", with the settings of the browser compatibility page."),
                'flags': flags,
                'encode': f"{INPUT} {flags} {{out}}",
                'layout': {'chroma': '444' if rgb else layout_key, 'range': rng, 'bits': bits, 'rgb': rgb},
                'sort': (list(LAYOUTS).index(layout_key), CODEC_ORDER.index(codec)),
            })
    out = []
    for bits in sorted(groups):
        entries = sorted(groups[bits], key=lambda e: e['sort'])
        out.append((f"{bits}-bit", entries))
    return out


STATS = [
    {'key': 'mean', 'label': 'Mean', 'short': 'Mean', 'digits': 2},
    {'key': 'p99', 'label': '99th pct', 'short': '99th', 'digits': 1},
    {'key': 'max', 'label': 'Max', 'short': 'Max', 'digits': 1},
]


def make_sources(root):
    import OpenImageIO as oiio
    from PIL import Image
    # The color bars of the browser compatibility page, without the layout label, so every variant can share them.
    bars = np.array(Image.open(os.path.join(HERE, "..", "sourceimages", "test444.png")).convert("RGB"))
    bars[95:190] = bars[60]
    bars_path = os.path.join(root, "colorbars.png")
    yc.write_raw_png(np.ascontiguousarray(bars), bars_path)
    # The 16-bit chip chart used for the color tests, at half size (960x540) to keep the movies small.
    buf = oiio.ImageBufAlgo.resize(oiio.ImageBuf(os.path.join(HERE, "..", "sourceimages",
                                                              "chip-chart-1080-16bit-noicc.png")),
                                   roi=oiio.ROI(0, 960, 0, 540, 0, 1, 0, 3))
    chart_path = os.path.join(root, "chipchart-960.png")
    yc.write_png16(np.array(buf.get_pixels(oiio.FLOAT))[..., :3], chart_path)
    return [
        {'id': 'bars', 'label': 'Color bars', 'path': bars_path,
         'description': '75% color bars, gray and a ramp: the image of the browser compatibility page (8-bit)'},
        {'id': 'chart', 'label': 'Chip chart', 'path': chart_path,
         'description': 'the 16-bit chip chart of the color tests (sourceimages/chip-chart-1080-16bit-noicc.png), '
                        'at 960×540'},
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="./codec-color-compare")
    args = parser.parse_args()
    root = args.outdir
    os.makedirs(root, exist_ok=True)
    sources = make_sources(root)
    groups = variants_from_config()
    version = yc.ffmpeg_version()
    srcs, grps, items = yc.run_comparison(root, sources, groups, 255, keep_videos=True, ideal_bits=None)
    yc.print_table(version, srcs, grps, items, STATS)
    yc.write_page(root, {
        'pageTitle': "Codec Color Compare",
        'title': "Codec colors by bit depth and layout",
        'lede': ("The browser compatibility movies (H.264, HEVC, VP9 and AV1; 8, 10 and 12-bit; 4:2:0, 4:2:2, 4:4:4 and "
                 "RGB) on two images. <b>Your browser</b> plays the actual video files, so what you see is this "
                 "browser's decoder with nothing captured in between. <b>Measured</b> shows the same files decoded by "
                 "FFmpeg, with errors against the source in 8-bit code values: if a result looks wrong in your browser "
                 "but right when measured, the browser is decoding it wrongly. Pick A and B from the same bit depth "
                 "to switch between codecs."),
        'tableNote': ("Error against the source in 8-bit code values, from FFmpeg's decode of each file (lossy "
                      "encodes, as on the browser compatibility page). These say what is in the file, not what a "
                      "browser shows; for that, switch Show to Your browser."),
        'unit': '8-bit code values', 'unitName': '8-bit code', 'unitMax': 255,
        'stats': STATS, 'rankKey': 'mean', 'groups': grps, 'items': items, 'videos': True,
        'rowLabel': 'Encode',
        'defaults': {'src': 'bars', 'a': 'source', 'b': 'h264_444_8', 'show': 'browser'},
        'presets': [
            {'label': '8-bit RGB: H.264 vs HEVC', 'src': 'bars', 'a': 'h264_rgb_8', 'b': 'hevc_rgb_8',
             'show': 'browser', 'mode': 'toggle',
             'title': 'Safari ignores the RGB matrix tag and shows these pink'},
            {'label': '10-bit RGB: VP9 vs HEVC', 'src': 'bars', 'a': 'vp9_rgb_10', 'b': 'hevc_rgb_10',
             'show': 'browser', 'mode': 'toggle',
             'title': 'Safari and Firefox show RGB HEVC pink; Chrome shows both correctly'},
            {'label': '12-bit 4:4:4: VP9 vs HEVC', 'src': 'bars', 'a': 'vp9_444_12', 'b': 'hevc_444_12',
             'show': 'browser', 'mode': 'toggle', 'zoom': 4,
             'title': 'Firefox shows HEVC 4:4:4 with its chroma halved across, as 4:2:2: look at the bar edges'},
            {'label': '8-bit: 4:2:0 vs 4:4:4 (H.264)', 'src': 'chart', 'a': 'h264_420_8', 'b': 'h264_444_8',
             'show': 'browser', 'mode': 'toggle'},
            {'label': 'Source vs 12-bit VP9 4:2:0', 'src': 'chart', 'a': 'source', 'b': 'vp9_420_12',
             'show': 'browser', 'mode': 'wipe'},
        ],
    }, srcs)


if __name__ == "__main__":
    main()
