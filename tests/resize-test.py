"""
Compare ways of downsizing an image by 4 (and the EXRs also by 2.133, as 4096 to 1920), for two pages:
tests/resize-compare/compare.html (the 8-bit sRGB sources) and tests/resize-hdr-compare/compare.html (the
scene-linear EXRs).

Each source is shrunk to a quarter of its width and height with FFmpeg's scale (libswscale) and zscale filters,
with oiiotool, and with both of those in linear light. The results are compared with a reference: each output
pixel is the average of its 4x4 block of source pixels in linear light, which is the physically right brightness
(averaging the gamma-encoded values instead makes fine detail too dark). The reference is not the sharpest possible
result, so sharper filters differ from it at edges; the errors mostly show brightness and aliasing.

Sources: a 1920x1080 8-bit zone plate made here (its rings reach the finest detail the full-size image can hold at
the corners, so after a 4x shrink the outer rings should become flat grey), the Bellnuit test chart and an animation
frame, all treated as sRGB-encoded; and an HDR frame, Netflix's Sparks (ACES2065-1 OpenEXR, highlights up to about
200x scene white), viewed through OCIO's ACES 2.0 SDR view for sRGB. For Sparks the reference is the 4x4 average in
scene-linear light, then the view transform; the other variants resize the display image that oiiotool makes from
it, and an extra group resizes before the view transform. Two more EXRs from the OpenEXR test images, treated as
ACES2065-1, get the same treatment: BrightRings (rings up to 1025 on grey, made for testing filters on HDR values) and
Desk (a photograph with a backlit stained-glass window, highlights up to about 230). The Sparks EXR is not committed: run enctests/sources/hdr_sources/download_media.sh
first. The OpenEXR images are read from ../../openexr-images (set OPENEXR_IMAGES to change it); a missing EXR is left
out.

The EXRs are also shrunk by 32/15 = 2.133 (Sparks from 4096 to 1920 wide), with the scene-linear variants only. Each
output pixel's footprint then cuts through source pixels, so the reference is the footprint's average with the edge
pixels weighted by how much of them it covers (tests/python/resizefootprint.py); for a whole factor that is the same
as the block average.

Run from the tests folder, with ffmpeg (with zscale) and oiiotool on the PATH:
    python resize-test.py [--outdir ./resize-compare] [--hdr-outdir ./resize-hdr-compare]
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
import yuvcompare as yc  # noqa: E402
from resizefootprint import area_resize  # noqa: E402

FF = 'ffmpeg -v error -y -i {src} -frames:v 1 -vf "{vf}" {out}'
OIIO_LIN = "--colorconvert srgb_tx lin_rec709 {resize} --colorconvert lin_rec709 srgb_tx"
Z709 = "primariesin=709:primaries=709"
SPARKS = "../enctests/sources/hdr_sources/sparks/SPARKS_ACES_06100.exr"
# github.com/AcademySoftwareFoundation/openexr-images, checked out next to this repository (or set OPENEXR_IMAGES)
OPENEXR_IMAGES = os.environ.get("OPENEXR_IMAGES", "../../openexr-images")
HDR_IDS = ['sparks', 'brightrings', 'desk']
FRACTION = 15 / 32     # the second size for the EXRs: 4096 to 1920, a factor of 2.133
HDR_IDS += [f"{i}_frac" for i in HDR_IDS]
# Absolute links, so the page also works when hosted on its own (it is too large to commit)
SITE = "https://academysoftwarefoundation.github.io/EncodingGuidelines"
REPO = "https://github.com/AcademySoftwareFoundation/EncodingGuidelines"
# The two pages link to each other where they are hosted (they are too large to commit)
SDR_PAGE = "https://encode.taurich.org/tests/resize-compare/compare.html"
HDR_PAGE = "https://encode.taurich.org/tests/resize-hdr-compare/compare.html"
DISPLAY, VIEW = "sRGB - Display", "ACES 2.0 - SDR 100 nits (Rec.709)"
OIIO_VIEW = f'--ociodisplay:from=ACES2065-1 "{DISPLAY}" "{VIEW}"'
# FFmpeg's ocio filter reads the config from $OCIO; ocio://default is OCIO 2.5's built-in config, the one oiiotool uses.
FF_OCIO = f"ocio=input=ACES2065-1:display={DISPLAY}:view={VIEW}:format=rgb48"
NUKE = "./resize-compare/nuke"   # written by tests/resize-nuke.py in Nuke; not committed
FF_EXR = 'OCIO=ocio://default ffmpeg -v error -y -i {exr} -frames:v 1 -vf "VF" {out}'
ZLIN = (f"zscale={Z709}:transferin=iec61966-2-1:transfer=linear,format=gbrpf32le,"
        f"zscale=w={{w}}:h={{h}}:filter=lanczos,zscale={Z709}:transferin=linear:transfer=iec61966-2-1,format=gbrp16le")
# oiiotool's --resize:highlightcomp=1 is IBA::rangecompress per channel, the resize, then IBA::rangeexpand
# (src/libOpenImageIO/imagebufalgo_pixelmath.cpp, SPI's coefficients): unchanged up to |x| = 0.18, then
# sign(x) * (a + b * ln(c * |x| + 1)), which meets the straight part with the same value and slope.
# rangecompress.clf is the same curve for values >= 0, for FFmpeg's ocio filter (below 0.18 it is a straight line,
# so it does not mirror the curve for values below -0.18 as OIIO does).
RC_CLF = "rangecompress.clf"
# The anti-ringing clamp in FFmpeg: lanczos, limited to the minimum and maximum of the source pixels under each output
# pixel. erosion/dilation (minimum/maximum) only work on integers, so the limits go through a log curve (log16.clf)
# into 16 bits and back. Each pass looks one pixel further (coordinates=255 all round, 11 up and left, 208 down and
# right), and zscale's point filter then picks pixel floor(c) for an output pixel centred at c in the source. The
# passes depend on the factor (ar_window, filled in per source as {ar_erosion} and {ar_dilation}).
# blend's lighten and darken are max and min, in float.
AR_CLF = "log16.clf"


def ar_window(f, src_w, w):
    """The erosion or dilation passes for a resize from src_w to w pixels across. For a whole factor k, exactly the
    k x k block around the pixel the point filter picks (4x: one pass all round, one up and left). Otherwise
    floor(s/2) + 1 passes all round, the smallest square around that pixel that always holds the footprint
    (5 x 5 at x2.133, where the footprint touches 3 or 4 pixels), so the limits are a little loose."""
    s = src_w / w
    k = round(s)
    if abs(s - k) < 1e-9:
        up, down = k // 2, k - 1 - k // 2
        passes = [255] * min(up, down) + [11] * (up - min(up, down)) + [208] * (down - min(up, down))
    else:
        passes = [255] * (int(s // 2) + 1)
    return ",".join(f"{f}=coordinates={c}" for c in passes)


def size_params(src_w, w):
    """Per-source values for the variant commands, beside {w} and {h}."""
    return {'ar_erosion': ar_window('erosion', src_w, w), 'ar_dilation': ar_window('dilation', src_w, w)}


def ff_antiring():
    def limit(f):
        return (f"{{ar_{f}}},zscale=w={{w}}:h={{h}}:filter=point,"
                f"format=gbrpf32le,ocio=filetransform={AR_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le")
    return ("split[a][b];[a]zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le[L];"
            f"[b]ocio=filetransform={AR_CLF}:format=gbrpf32le,format=gbrp16le,split[b][c];"
            f"[b]{limit('erosion')}[lo];[c]{limit('dilation')}[hi];"
            "[L][lo]blend=all_mode=lighten,format=gbrpf32le[t];[t][hi]blend=all_mode=darken,format=gbrpf32le")


def ff_log(space, lobes, config="ocio://default"):
    """FFmpeg: ACES2065-1 to a log space with the ocio filter, zscale lanczos with the given lobes (2 is Nuke's
    Lanczos4), then the view from the log space. Camera logs need OCIO's studio config; ocio://default has only
    ACEScct."""
    view = f"ocio=input={space}:display={DISPLAY}:view={VIEW}:format=rgb48"
    vf = (f"ocio=input=ACES2065-1:output={space}:format=gbrpf32le,format=gbrpf32le,"
          f"zscale=w={{w}}:h={{h}}:filter=lanczos:param_a={lobes},format=gbrpf32le,{view},format=rgb48le")
    return FF_EXR.replace("ocio://default", config).replace("VF", vf)


# Colors outside a log space's gamut have a negative channel, and the log curves are straight lines below zero, so
# they become very negative log values; lanczos's overshoot next to them can overflow to infinity in linear.
LOG_OVERFLOW = (" BrightRings' colors are outside this gamut: they become very negative log values (log curves do not "
                "compress values below zero), and lanczos's overshoot next to them overflows to infinity, which the "
                "view turns into stray pixels (black from FFmpeg's ocio filter, white from oiiotool). So BrightRings "
                "has no meaningful result here, nor in any log space we tried.")


def ff(vf):
    return FF.replace("{vf}", vf)


def scale(flags):
    vf = "scale={w}:{h}" + (f":flags={flags}" if flags else "") + ",format=rgb48be"
    return vf


def zs(filt):
    return "zscale=w={w}:h={h}" + (f":filter={filt}" if filt else "") + ",format=gbrp16le"


def v(id_, label, description, flags, command):
    return {'id': id_, 'label': label, 'description': description, 'flags': flags, 'command': command}


GROUPS = [
    ('FFmpeg scale (libswscale), on the encoded values', [
        v('scale_bicubic', 'scale, default (bicubic)', "FFmpeg's default resize. Works on the gamma-encoded values, "
          "so fine detail comes out darker than it should.", '-vf "scale=W:H"', ff(scale(""))),
        v('scale_lanczos', 'scale, lanczos', "Sharper than bicubic; can ring (halos) at hard edges.",
          '-vf "scale=W:H:flags=lanczos"', ff(scale("lanczos"))),
        v('scale_spline', 'scale, spline', "A sharp, smooth filter; between bicubic and lanczos.",
          '-vf "scale=W:H:flags=spline"', ff(scale("spline"))),
        v('scale_area', 'scale, area', "Averages the source pixels each output pixel covers: no ringing, but "
          "softer, and still on the gamma-encoded values.", '-vf "scale=W:H:flags=area"', ff(scale("area"))),
        v('scale_neighbor', 'scale, neighbor', "Picks one source pixel per output pixel: no filtering at all, so "
          "fine detail aliases badly. Shown for comparison.", '-vf "scale=W:H:flags=neighbor"', ff(scale("neighbor"))),
    ]),
    ('FFmpeg zscale, on the encoded values', [
        v('zscale_bilinear', 'zscale, default (bilinear)', "zscale's default filter: soft, and on the "
          "gamma-encoded values.", '-vf "zscale=w=W:h=H"', ff(zs(""))),
        v('zscale_lanczos', 'zscale, lanczos', "Sharp; on the gamma-encoded values.",
          '-vf "zscale=w=W:h=H:filter=lanczos"', ff(zs("lanczos"))),
        v('zscale_spline36', 'zscale, spline36', "Sharp and smooth; on the gamma-encoded values.",
          '-vf "zscale=w=W:h=H:filter=spline36"', ff(zs("spline36"))),
    ]),
    ('Linear light (the right way to resize)', [
        v('zscale_lanczos_linear', 'zscale, lanczos, linear light', "zscale converts to linear light, resizes "
          "with lanczos in float, and converts back: FFmpeg can resize correctly, it just does not by default.",
          '-vf "zscale=...:transfer=linear,format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,zscale=...:'
          'transfer=iec61966-2-1"', ff(ZLIN)),
        v('oiio_lanczos3_linear', 'oiiotool, lanczos3, linear light', "oiiotool converts sRGB to linear, resizes "
          "with lanczos3, and converts back.", '--colorconvert srgb_tx lin_rec709 --resize:filter=lanczos3 WxH '
          '--colorconvert lin_rec709 srgb_tx',
          "oiiotool {src} " + OIIO_LIN.format(resize="--resize:filter=lanczos3 {w}x{h}") + " -d uint16 -o {out}"),
        v('oiio_box_linear', 'oiiotool, box, linear light', "A box filter over exactly 4x4 pixels in linear light: "
          "the same method as the reference, done with oiiotool, as a check.",
          '--colorconvert srgb_tx lin_rec709 --resize:filter=box WxH --colorconvert lin_rec709 srgb_tx',
          "oiiotool {src} " + OIIO_LIN.format(resize="--resize:filter=box {w}x{h}") + " -d uint16 -o {out}"),
    ]),
    ('Resizing the EXR, before or after the view transform', [
        dict(v('hdr_ff_ocio_zscale', 'FFmpeg ocio, then zscale lanczos', "The view transform first, then zscale "
               "resizes the display-encoded values: the usual FFmpeg route, all in one command.",
               '-vf "ocio=...:format=rgb48,format=rgb48le,zscale=w=W:h=H:filter=lanczos"',
               FF_EXR.replace("VF", FF_OCIO + ",format=rgb48le,zscale=w={w}:h={h}:filter=lanczos,format=gbrp16le")),
             only=HDR_IDS),
        dict(v('hdr_oiio_scene_lanczos', 'oiiotool, lanczos3 in scene-linear, then OCIO', "Resizes the EXR in "
               "scene-linear light, then applies the ACES 2.0 view: the right order, and the brightness is closest to "
               "the reference. But lanczos's negative lobes ring hard around highlights a hundred or more times "
               "brighter than white, leaving dark halos around the sparks.",
               f'--resize:filter=lanczos3 WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=lanczos3 {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_oiio_scene_lanczos_clamp', 'oiiotool, lanczos3 in scene-linear, clamp negatives, then OCIO',
               "Lanczos as above, then --clamp:min=0 to remove the values its ringing pushed below zero. The halos "
               "become black rather than below black: less extreme, but still there, since the ring is darker than "
               "its surroundings either way. (The anti-ringing variant below clamps to the range of the pixels "
               "each output pixel covers instead, which removes them.)",
               f'--resize:filter=lanczos3 WxH --clamp:min=0 {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=lanczos3 {w}x{h} --clamp:min=0 " + OIIO_VIEW + " -d uint16 -o {out}"),
             only=HDR_IDS),
        dict(v('hdr_oiio_scene_lanczos_hc', 'oiiotool, lanczos3 in scene-linear with highlightcomp, then OCIO',
               "--resize:highlightcomp=1 compresses each channel with OIIO's rangecompress before filtering (values "
               "up to 0.18 are unchanged, above that a log curve takes 200 down to about 1.46) and expands the result "
               "with rangeexpand. That stops the ringing, but the averaging then happens on compressed values, so "
               "bright detail loses some of its light.",
               f'--resize:filter=lanczos3:highlightcomp=1 WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=lanczos3:highlightcomp=1 {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"),
             only=HDR_IDS),
        dict(v('hdr_py_scene_lanczos_hc_energy', "lanczos3 in scene-linear with highlightcomp, light restored, then OCIO",
               "Highlightcomp, with the light it loses put back. Each output pixel of the highlightcomp result is "
               "multiplied, per channel, by the ratio of two averages of the source pixels it covers (its 4×4 block "
               "at 4×): the average in scene-linear (the right brightness) over the same average done the "
               "highlightcomp way (compress, average, expand). In flat areas the ratio is 1; where bright and dark "
               "mix it scales the result back up, so BrightRings' discs are white again. At 4× the average never "
               "looks outside its block, so the correction does not spread a highlight into its neighbours. At "
               "×2.13 the output pixels cut through source pixels, and one that only just touches a highlight "
               "gets a large ratio, which also scales up lanczos's spill: the highlights come out somewhat too "
               "bright. Highlightcomp's mild halos remain. Done by tests/resize-highlightcomp.py with the "
               "OpenImageIO Python bindings.",
               'python resize-highlightcomp.py in.exr W H out.png',
               "python resize-highlightcomp.py {exr} {w} {h} {out}"), only=HDR_IDS),
        dict(v('hdr_py_scene_lanczos_hc_energy_clamp', "lanczos3 in scene-linear with highlightcomp, light restored, "
               "clamped to each block's range, then OCIO",
               "The same, then each output pixel is clamped to the range of the source pixels it covers (its 4×4 "
               "block at 4×; the anti-ringing clamp), which removes the halos highlightcomp leaves.",
               'python resize-highlightcomp.py in.exr W H out.png --clamp',
               "python resize-highlightcomp.py {exr} {w} {h} {out} --clamp"), only=HDR_IDS),
        dict(v('hdr_oiio_acescct_lanczos', 'oiiotool, lanczos3 in ACEScct (log), then OCIO', "Converts to ACEScct, "
               "a log encoding, resizes there, then applies the view, as Resolve does with a log timeline. Log "
               "compresses the highlights, so lanczos cannot ring far around them, but the averaging is on log "
               "values, which loses highlight energy." + LOG_OVERFLOW,
               f'--colorconvert ACES2065-1 ACEScct --resize:filter=lanczos3 WxH --ociodisplay:from=ACEScct ...',
               "oiiotool {exr} --colorconvert ACES2065-1 ACEScct --resize:filter=lanczos3 {w}x{h} "
               f'--ociodisplay:from=ACEScct "{DISPLAY}" "{VIEW}" -d uint16 -o {{out}}'), only=HDR_IDS),
        dict(v('hdr_oiio_scene_cubic', "oiiotool, cubic in scene-linear, then OCIO", "oiiotool's cubic filter: the "
               "same as Nuke's default Cubic (the Hermite cubic, no negative lobes).",
               f'--resize:filter=cubic WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=cubic {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_oiio_scene_box', 'oiiotool, box in scene-linear, then OCIO', "A box over exactly 4x4 pixels in "
               "scene-linear, then the view: the reference's method, done with oiiotool, as a check. At ×2.13 it "
               "is not quite the reference: oiiotool's box takes or leaves each source pixel whole instead of "
               "weighting the ones at its edges by how much of them it covers.",
               f'--resize:filter=box WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=box {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_ff_zscale_ocio', 'FFmpeg zscale lanczos in scene-linear, then ocio', "zscale resizes the "
               "half-float EXR directly, keeping the highlights, then the ocio filter applies the view.",
               '-vf "zscale=w=W:h=H:filter=lanczos,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le," + FF_OCIO + ",format=rgb48le")),
             only=HDR_IDS),
        dict(v('hdr_ff_zscale_hermite_ocio', "FFmpeg zscale cubic (b = c = 0, Nuke's Cubic) in scene-linear, then ocio",
               "zscale's bicubic with b = 0 and c = 0: the Hermite cubic, which has no negative lobes, so no ringing. "
               "It gives the same pixels as Nuke's default Reformat filter, Cubic, and oiiotool's cubic.",
               '-vf "zscale=w=W:h=H:filter=bicubic:param_a=0:param_b=0,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=bicubic:param_a=0:param_b=0,format=gbrpf32le," + FF_OCIO
                              + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_zscale_l4_ocio', "FFmpeg zscale lanczos, 2 lobes (Nuke's Lanczos4), in scene-linear, then ocio",
               "zscale's lanczos with param_a=2: two lobes each side, which Nuke calls Lanczos4 (Nuke counts the "
               "full width; zscale's default, 3 lobes, is Nuke's Lanczos6 and oiiotool's lanczos3). Its negative "
               "lobes are smaller, so it rings less around the highlights than lanczos3, but still rings. oiiotool "
               "has no 2-lobe lanczos.",
               '-vf "zscale=w=W:h=H:filter=lanczos:param_a=2,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=lanczos:param_a=2,format=gbrpf32le," + FF_OCIO
                              + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_acescct_l4_ocio', "FFmpeg zscale lanczos, 2 lobes (Nuke's Lanczos4), in ACEScct, then ocio",
               "The ocio filter converts to ACEScct, zscale resizes with a 2-lobe lanczos (param_a=2, Nuke's "
               "Lanczos4), and the ocio filter applies the view from ACEScct. ACEScct is the usual choice for CG; "
               "compare the oiiotool lanczos3 variant in ACEScct." + LOG_OVERFLOW,
               '-vf "ocio=input=ACES2065-1:output=ACEScct:format=gbrpf32le,format=gbrpf32le,'
               'zscale=w=W:h=H:filter=lanczos:param_a=2,format=gbrpf32le,ocio=input=ACEScct:...:format=rgb48"',
               ff_log("ACEScct", 2)), only=HDR_IDS),
        dict(v('hdr_ff_rwg_l4_ocio', "FFmpeg zscale lanczos, 2 lobes (Nuke's Lanczos4), in Log3G10/REDWideGamutRGB, "
               "then ocio",
               "The same in RED's Log3G10 encoding and REDWideGamutRGB gamut, which needs OCIO's studio config "
               "(OCIO=ocio://studio-config-latest; ocio://default has only ACEScct). Facilities resize plates in the "
               "camera's own log, and use a very wide gamut log such as this one (or ARRI LogC4/Wide Gamut 4, which "
               "gives nearly the same results) for ACES2065-1 plates with colors outside the ACEScct gamut. Desk "
               "has five times fewer negative pixels here than in ACEScct." + LOG_OVERFLOW,
               'OCIO=ocio://studio-config-latest ffmpeg ... -vf "ocio=input=ACES2065-1:output=Log3G10 '
               'REDWideGamutRGB:...,zscale=w=W:h=H:filter=lanczos:param_a=2,...,ocio=input=Log3G10 '
               'REDWideGamutRGB:...:format=rgb48"',
               ff_log("Log3G10 REDWideGamutRGB", 2, "ocio://studio-config-latest")), only=HDR_IDS),
        dict(v('hdr_ff_ocio_hc_ocio', 'FFmpeg zscale lanczos in scene-linear with highlightcomp (OCIO CLF), then ocio',
               "oiiotool's highlightcomp in FFmpeg: OIIO's rangecompress curve (a + b ln(c x + 1) above 0.18) as a CLF Log "
               "node (cameraLinToLog, base e: logSideSlope = b, "
               "logSideOffset = a, linSideSlope = c, linSideOffset = 1, linSideBreak = 0.18) applied by the ocio "
               "filter, and inverted with inverse=1. Below the break OCIO's curve is a "
               "straight line, so values below -0.18 are not compressed (OIIO mirrors the curve for negative "
               "values). None of these sources goes below -0.18 (Desk's lowest value is -0.012), but lanczos's "
               "undershoot can, so the two versions can differ slightly next to the brightest highlights.",
               f'-vf "ocio=filetransform={RC_CLF}:format=gbrpf32le,format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,'
               f'ocio=filetransform={RC_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", f"ocio=filetransform={RC_CLF}:format=gbrpf32le,format=gbrpf32le,"
                              "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le,"
                              f"ocio=filetransform={RC_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le,"
                              + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_antiring_ocio', "FFmpeg zscale lanczos in scene-linear, clamped to each block's range "
               "(anti-ringing), then ocio",
               "The anti-ringing clamp in one FFmpeg command. zscale's lanczos gives the picture. The limits are the "
               "minimum and maximum of the source pixels under each output pixel (its 4×4 block at 4×): erosion and dilation find "
               "them, but only work on integers, so the limits (not the picture) go through a log curve "
               f"({AR_CLF}) into 16 bits and back. blend's lighten and darken modes, which keep float, then clamp "
               "the picture to them. It gives the same result as tests/resize-antiring.py (exact limits) to a small fraction of a code "
               "value on average. The limits are about 1% loose (FFmpeg's float to 16-bit conversion). The "
               "erosion/dilation passes depend on the factor: at 4× they make exactly the 4×4 block; at ×2.13 they "
               "make a 5×5 square, a little wider than the 3 or 4 pixels the output pixel covers, because a fixed "
               "window cannot follow a footprint that changes from pixel to pixel.",
               f'-vf "split[a][b];[a]zscale=w=W:h=H:filter=lanczos,format=gbrpf32le[L];'
               f'[b]ocio=filetransform={AR_CLF}:format=gbrpf32le,format=gbrp16le,split[b][c];'
               '[b]erosion=coordinates=255,erosion=coordinates=11 (at 4x),zscale=w=W:h=H:filter=point,'
               f'format=gbrpf32le,ocio=filetransform={AR_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le[lo];'
               '[c]dilation=... (the same) ...[hi];[L][lo]blend=all_mode=lighten,format=gbrpf32le[t];'
               '[t][hi]blend=all_mode=darken,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", ff_antiring() + "," + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_f32_trap', 'FFmpeg format=gbrpf32le, then zscale (wrong)', "zscale lanczos in "
               "scene-linear, then ocio, with format=gbrpf32le first. It looks harmless, but FFmpeg converts the half-float EXR with libswscale, which clamps every "
               "value to 0-1 (FFmpeg 8.0 and later), so the highlights are lost before the resize.",
               '-vf "format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "format=gbrpf32le,zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le," + FF_OCIO
                              + ",format=rgb48le")), only=HDR_IDS),
    ]),
    ('Nuke Reformat in scene-linear, then OCIO (Sparks only; from tests/resize-nuke.py)', [
        dict(v('nuke_cubic', 'Nuke, Cubic (the default)', "Nuke's default Reformat filter. It has no negative "
               "lobes, so no ringing even around the brightest highlights; zscale (bicubic, b = c = 0) and oiiotool "
               "(cubic) give the same pixels.", 'Reformat filter=Cubic',
               "oiiotool " + NUKE + "/nuke-cubic.exr " + OIIO_VIEW + " -d uint16 -o {out}"), only=['sparks']),
        dict(v('nuke_lanczos4', 'Nuke, Lanczos4', "Nuke's Lanczos (four taps, a lanczos2): rings around the "
               "highlights, less than Lanczos6. zscale's lanczos with param_a=2 is close to it, not identical.", 'Reformat filter=Lanczos4',
               "oiiotool " + NUKE + "/nuke-lanczos4.exr " + OIIO_VIEW + " -d uint16 -o {out}"), only=['sparks']),
        dict(v('nuke_lanczos6', 'Nuke, Lanczos6', "Six taps: the same as oiiotool's lanczos3, with the same halos.",
               'Reformat filter=Lanczos6',
               "oiiotool " + NUKE + "/nuke-lanczos6.exr " + OIIO_VIEW + " -d uint16 -o {out}"), only=['sparks']),
        dict(v('nuke_lanczos6_clamp', 'Nuke, Lanczos6 with clamp', "Reformat's clamp sets negative intermediate and "
               "final results to zero, so it also clamps between the horizontal and vertical passes. That helps more "
               "than clamping only the final result, but does not remove the halos.",
               'Reformat filter=Lanczos6 clamp',
               "oiiotool " + NUKE + "/nuke-lanczos6-clamp.exr " + OIIO_VIEW + " -d uint16 -o {out}"), only=['sparks']),
    ]),
    ('oiiotool, on the encoded values', [
        v('oiio_default', 'oiiotool, default', "oiiotool --resize with no filter: lanczos3 for downsizing (the same "
          "pixels as lanczos3 on OIIO 3.1), on the gamma-encoded values.", '--resize WxH',
          "oiiotool {src} --resize {w}x{h} -d uint16 -o {out}"),
    ]),
]

STATS = [
    {'key': 'mean', 'label': 'Mean', 'short': 'Mean', 'digits': 2},
    {'key': 'p99', 'label': '99th pct', 'short': '99th', 'digits': 1},
    {'key': 'max', 'label': 'Max', 'short': 'Max', 'digits': 1},
    {'key': 'bias', 'label': 'Brightness', 'short': 'Bright', 'digits': 2, 'signed': True, 'warn': 0.5,
     'title': "Mean signed difference from the reference: negative is darker. Resizing gamma-encoded values makes "
              "fine detail darker than it should be."},
]


def zone_plate(w=1920, h=1080):
    """Rings whose spatial frequency rises with radius, reaching the Nyquist limit at the corners."""
    y, x = np.mgrid[0:h, 0:w].astype(float)
    r2 = (x - (w - 1) / 2) ** 2 + (y - (h - 1) / 2) ** 2
    rmax = np.hypot(w / 2, h / 2)
    v = 0.5 + 0.5 * np.cos(np.pi * 0.5 * r2 / rmax)      # frequency = 0.5 * r / rmax cycles per pixel
    return np.repeat(v[..., None], 3, 2)


def linear_box_reference(img, k=4):
    lin = yc.srgb_to_linear(img)
    h, w = img.shape[0] // k, img.shape[1] // k
    block = lin[:h * k, :w * k].reshape(h, k, w, k, 3).mean((1, 3))
    return yc.linear_to_srgb(block)


def scene_linear_reference(exr, w, h):
    """The scene-linear EXR averaged over each output pixel's footprint (for a whole factor, its block), then OCIO's
    ACES 2.0 SDR view for sRGB (as display values)."""
    import OpenImageIO as oiio
    lin = np.array(oiio.ImageBuf(exr).get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)
    block = area_resize(lin, w, h).astype(np.float32)
    shown = oiio.ImageBufAlgo.ociodisplay(oiio.ImageBuf(np.ascontiguousarray(block)), DISPLAY, VIEW,
                                          fromspace="ACES2065-1")
    if shown.has_error:
        sys.exit(shown.geterror())
    return np.clip(np.array(shown.get_pixels(oiio.FLOAT))[..., :3].astype(np.float64), 0, 1), block


def brightest_window(lin, w, h):
    """(x, y, w, h) of the w x h window (on an 8-pixel grid) holding the most scene-linear values above 1."""
    over = np.pad((lin.max(-1) > 1).astype(np.int64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    best, pos = -1, (0, 0)
    for y in range(0, lin.shape[0] - h + 1, 8):
        for x in range(0, lin.shape[1] - w + 1, 8):
            n = over[y + h, x + w] - over[y, x + w] - over[y + h, x] + over[y, x]
            if n > best:
                best, pos = n, (x, y)
    return (pos[0], pos[1], w, h)


def worst_pixel(result, reference):
    e = np.abs(result - reference).max(-1)
    y, x = np.unravel_index(np.argmax(e), e.shape)
    return [float(x / e.shape[1]), float(y / e.shape[0])]


def timing_table(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "resize-timing-results.json")):
    """The timing table, from tests/resize-timing.py's results (None if it has not been run)."""
    import json
    if not os.path.exists(path):
        print(f"No {os.path.relpath(path)} (run tests/resize-timing.py): leaving out the timing table")
        return None
    with open(path) as fh:
        data = json.load(fh)
    first, last = data['frames']
    n = last - first + 1
    modes = data['modes']
    values = {}
    for name, key in (("default", "fps"), ("parallel-frames", "fps_par")):
        for id_, r in modes.get(name, {}).get('results', {}).items():
            values.setdefault(id_, {})[key] = n / r['total']
            if name == "default":
                values[id_]['s'] = r['total']
    d = modes.get("default") or next(iter(modes.values()))
    about = (f"Sparks frames {first}-{last} ({n} frames of 4096×2160 half-float EXR) to a 1024×540 ProRes 422 HQ "
             f"QuickTime, timed by tests/resize-timing.py with {d['ffmpeg']} and oiiotool {d['oiiotool']} on "
             f"{d['machine']} ({d['date']}). FFmpeg variants are one ffmpeg command; oiiotool variants write 16-bit "
             "TIFFs, then ffmpeg encodes them, and the time is the sum.")
    extra = {
        'label': 'Timing: the Sparks sequence to ProRes',
        'note': about + " <b>fps, par.</b> is oiiotool with <code>--parallel-frames</code> (several frames at once).",
        'columns': [
            {'key': 's', 'short': 'Time (s)', 'label': 'Time', 'digits': 1,
             'title': f"Wall-clock seconds for all {n} frames, EXR to QuickTime (oiiotool one frame at a time)"},
            {'key': 'fps', 'short': 'fps', 'label': 'Frames/s', 'digits': 1,
             'title': "Frames per second, end to end (oiiotool one frame at a time, using all cores per frame)"},
            {'key': 'fps_par', 'short': 'fps, par.', 'label': 'Frames/s, --parallel-frames', 'digits': 1,
             'title': "oiiotool with --parallel-frames (several frames at once), then the same ProRes encode"},
        ],
        'values': values,
    }
    return extra


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="./resize-compare", help="the page for the 8-bit sRGB sources")
    parser.add_argument("--hdr-outdir", default="./resize-hdr-compare", help="the page for the EXRs")
    args = parser.parse_args()
    root = args.outdir
    os.makedirs(root, exist_ok=True)
    os.makedirs(args.hdr_outdir, exist_ok=True)
    zp = os.path.join(root, "zoneplate-1080.png")
    yc.write_raw_png(np.round(zone_plate() * 255).astype(np.uint8), zp)
    sources = [
        {'id': 'zoneplate', 'label': 'Zone plate', 'path': zp,
         'description': '1920×1080 8-bit zone plate, shrunk to 480×270'},
        {'id': 'chart', 'label': 'Test chart', 'path': '../sourceimages/bellnuitHDTestchart.tif',
         'description': 'Bellnuit HD test chart, 1920×1080 8-bit, shrunk to 480×270'},
        {'id': 'animation', 'label': 'Animation', 'path': '../sourceimages/animation_cc.png',
         'description': 'Animation frame (Wing It!, Blender Studio, CC-BY), 1920×1080 8-bit, shrunk to 480×270'},
    ]
    for s in sources:
        s['reference'] = linear_box_reference(yc.read_rgb(s['path']))
        s['description'] += ". The reference is each 4×4 block averaged in linear light."
    # The EXR sources, all ACES2065-1: for each, the display image the display-referred variants start from, and a
    # scene-linear reference. Temporary files (the display images, the prepared Desk) are deleted afterwards.
    temps = []
    desk = os.path.join(OPENEXR_IMAGES, "ScanLines/Desk.exr")
    desk_rgb = os.path.join(args.hdr_outdir, "desk-rgb.exr")
    exrs = [
        {'id': 'sparks', 'label': 'Sparks (HDR EXR)', 'exr': SPARKS, 'window': (512, 270),
         'description': "Netflix's Sparks, frame 6100: 4096×2160 half-float ACES2065-1 OpenEXR with highlights up to "
                        "about 200× scene white, shrunk to SIZE; shown and measured is the 512×270 part with the "
                        "most highlights."},
        {'id': 'brightrings', 'label': 'BrightRings (EXR)', 'exr': os.path.join(OPENEXR_IMAGES, "TestImages/BrightRings.exr"),
         'description': "BrightRings.exr from the OpenEXR test images: 800×800 half-float, rings with values up to 1025 "
                        "on a grey background (0.5), made for testing how filters with negative lobes react to HDR "
                        "values. Treated as ACES2065-1. Shrunk to SIZE."},
        {'id': 'desk', 'label': 'Desk (EXR)', 'exr': desk_rgb,
         'prepare': (desk, desk_rgb, "--ch R,G,B --cut 644x872+0+0"),
         'description': "Desk.exr from the OpenEXR test images: a 644×874 half-float photograph of a desk in front of a "
                        "backlit stained-glass window, with highlights up to about 230. Treated as ACES2065-1 (the file has no chromaticities). 874 rows "
                        "is not a multiple of 4, so the bottom two rows are cut, and the alpha channel (all 1) is "
                        "dropped: oiiotool Desk.exr --ch R,G,B --cut 644x872+0+0 -o desk-rgb.exr. Shrunk to SIZE."},
    ]
    displays = {}
    for e in exrs:
        if 'prepare' in e:
            src, dst, prep = e.pop('prepare')
            if not os.path.exists(src):
                print(f"{src} not found (set OPENEXR_IMAGES): leaving out {e['label']}")
                continue
            yc.run(f"oiiotool {src} {prep} -d half -o {dst}")
            temps.append(dst)
        if not os.path.exists(e['exr']):
            print(f"{e['exr']} not found: leaving out {e['label']}")
            continue
        display = os.path.join(args.hdr_outdir, f"{e['id']}-display.png")
        yc.run(f"oiiotool {e['exr']} {OIIO_VIEW} -d uint16 -o {display}")
        temps.append(display)
        window = e.pop('window', None)
        sw, sh = yc.read_rgb(display).shape[1::-1]
        # Each EXR twice: a quarter of the size (4x4 blocks), and by 2.133 (4096 to 1920), scene-linear variants only
        for frac in (False, True):
            w, h = (round(sw * FRACTION), round(sh * FRACTION)) if frac else (sw // 4, sh // 4)
            ref, lin = scene_linear_reference(e['exr'], w, h)
            if frac:
                d = dict(e, id=e['id'] + "_frac", label=e['label'].replace(" (", f", ×{sw / w:.2f} ("),
                         listed_only=True)
                how = (f"The reference is the average of the {sw / w:.2f} × {sh / h:.2f} source pixels each output pixel "
                       "covers, with the ones at its edges weighted by how much of them it covers, in scene-linear "
                       "light, then the view transform. Only the variants that resize in scene-linear are run.")
            else:
                d = dict(e)
                how = (f"The display-referred variants resize the display image oiiotool makes from it "
                       f"({e['id']}-display.png). The reference is each 4×4 block averaged in scene-linear light, "
                       "then the view transform.")
            sources.append(dict(d, path=display, reference=ref, params=size_params(sw, w),
                                **({'crop': brightest_window(lin, *window)} if window else {}),
                                description=e['description'].replace("SIZE", f"{w}×{h}") +
                                f" Viewed through OCIO's {VIEW} view for sRGB. " + how))
    version = yc.ffmpeg_version()
    oiio = subprocess.run(["oiiotool", "--version"], capture_output=True, text=True).stdout.strip()
    nuke = os.path.exists(os.path.join(NUKE, "nuke-cubic.exr"))
    if not nuke:
        print(f"No Nuke results in {NUKE} (run tests/resize-nuke.py in Nuke): leaving out the Nuke variants")
    sdr_sources = [s for s in sources if 'exr' not in s]
    hdr_sources = [s for s in sources if 'exr' in s]
    sdr_groups = [g for g in GROUPS if not g[0].startswith(("Resizing the EXR", "Nuke"))]
    # The EXR page also resizes the display image, as an SDR pipeline would (quarter size only): FFmpeg's default
    # and lanczos in display-linear light, beside the EXR variants.
    by_id = {e['id']: e for _, es in GROUPS for e in es}
    quarter = [s['id'] for s in hdr_sources if not s.get('listed_only')]
    display_group = ('Resizing the display image (after the view transform)', [
        dict(by_id['scale_bicubic'], only=quarter, label='scale, default (bicubic), on the display image',
             description="FFmpeg's default resize, on the display image that the view transform makes: the "
             "highlights have already been tone mapped, and the values are gamma-encoded."),
        dict(by_id['zscale_lanczos_linear'], only=quarter, label='zscale lanczos, display-linear light',
             description="The display image converted to linear light (the sRGB curve), resized with lanczos and "
             "converted back. Right for an SDR image, but the highlights have already been tone mapped, so it is "
             "still too dark around them."),
    ])
    hdr_groups = [display_group] + [g for g in GROUPS if g[0].startswith("Resizing the EXR")
                                    or (nuke and g[0].startswith("Nuke"))]
    footer = (f"<p>Made with {version} and oiiotool {oiio}. Every result is a 16-bit RGB image; nothing is encoded, "
              "so the only difference is the resize. The images shown are 8-bit copies.</p>")
    common = {'unit': '8-bit code values', 'unitName': '8-bit code', 'unitMax': 255, 'stats': STATS,
              'rankKey': 'mean', 'rowLabel': 'Resize', 'sourceLabel': 'Reference'}
    hdr_root = args.hdr_outdir

    # The SDR page
    srcs, grps, items = yc.run_images(root, sdr_sources, sdr_groups)
    yc.print_table(f"{version}, OIIO {oiio}", srcs, grps, items, STATS)
    edge = worst_pixel(yc.read_rgb(os.path.join(root, "animation-scale_lanczos.png")),
                       yc.read_rgb(os.path.join(root, "animation-reference.png")))
    yc.write_page(root, dict(common, **{
        'pageTitle': "Resize Compare",
        'title': "Resizing: FFmpeg, oiiotool and linear light",
        'lede': ("Each image shrunk to a quarter of its size by FFmpeg (<code>scale</code> and <code>zscale</code>) "
                 "and by <code>oiiotool</code>, on the gamma-encoded values and in linear light. The <b>reference</b> "
                 "averages each 4×4 block of pixels in linear light, which gives fine detail its right brightness. "
                 "Errors are against the reference, in 8-bit code values. For scene-linear OpenEXR sources, see the "
                 f"<a href='{HDR_PAGE}' target='_top'>EXR resize comparison</a>."),
        'tableNote': ("Error against the reference in 8-bit code values. <b>Bright</b> is the mean signed difference: "
                      "negative means darker than the reference, which is what resizing gamma-encoded values does to "
                      "fine detail. The reference is a plain average, so sharper filters also differ from it at edges."),
        'groups': grps, 'items': items,
        'sourceOption': 'Reference (4×4 average in linear light)',
        'sourceNote': ("Each pixel is the average of its 4×4 block of source pixels, in linear light: the right "
                       "brightness. It is not the sharpest result, and a plain average still lets some fine detail "
                       "alias (the zone plate's outer rings), so it is a reference for brightness, not an ideal "
                       "filter."),
        'defaults': {'src': 'zoneplate', 'a': 'source', 'b': 'scale_bicubic'},
        'presets': [
            {'label': 'Zone plate: FFmpeg default vs reference', 'src': 'zoneplate', 'a': 'source',
             'b': 'scale_bicubic', 'mode': 'wipe',
             'title': 'The outer rings should turn flat grey; resizing the encoded values leaves them darker'},
            {'label': 'Same filter, gamma vs linear light', 'src': 'zoneplate', 'a': 'zscale_lanczos',
             'b': 'zscale_lanczos_linear', 'mode': 'toggle'},
            {'label': 'Lanczos ringing on animation, 4×', 'src': 'animation', 'a': 'scale_area', 'b': 'scale_lanczos',
             'mode': 'toggle', 'zoom': 4, 'focus': edge},
            {'label': 'FFmpeg vs oiiotool, linear light', 'src': 'chart', 'a': 'zscale_lanczos_linear',
             'b': 'oiio_lanczos3_linear', 'mode': 'diff'},
        ],
        'footer': footer + (
            "<p>All sources are treated as sRGB-encoded, and the linear-light versions use the sRGB curve both "
            f"ways.</p><p>See <a href='{SITE}/Resizing.html' target='_top'>Downscaling</a> and the "
            f"<a href='{HDR_PAGE}' target='_top'>EXR resize comparison</a>. Generated by "
            f"<a href='{REPO}/blob/main/tests/resize-test.py' target='_top'>tests/resize-test.py</a>.</p>"),
    }), srcs)

    # The EXR page
    srcs, grps, items = yc.run_images(hdr_root, hdr_sources, hdr_groups)
    for f in temps:
        os.remove(f)
    yc.print_table(f"{version}, OIIO {oiio}", srcs, grps, items, STATS)
    def worst(src):
        return worst_pixel(yc.read_rgb(os.path.join(hdr_root, f"{src}-hdr_oiio_scene_lanczos.png")),
                           yc.read_rgb(os.path.join(hdr_root, f"{src}-reference.png")))
    ring, ring_frac, rings = worst("sparks"), worst("sparks_frac"), worst("brightrings")
    extra = timing_table()
    yc.write_page(hdr_root, dict(common, **{
        **({'extra': extra} if extra else {}),
        'pageTitle': "EXR Resize Compare",
        'title': "Resizing scene-linear EXRs: FFmpeg, oiiotool and OCIO",
        'lede': ("Three ACES2065-1 OpenEXR images (Sparks, BrightRings and Desk), shrunk to a quarter of their size "
                 "and viewed through OCIO's ACES 2.0 SDR view: resized after the view transform, as an SDR "
                 "pipeline would, or before it, in scene-linear light (or log), where highlights far brighter than "
                 "white make filters with negative lobes ring. The <b>reference</b> averages each 4×4 block in "
                 "scene-linear light, then applies the view. The EXRs are also shrunk by 2.13 (Sparks from 4096 to "
                 "1920 wide), where output pixels no longer line up with source pixels; there the reference averages "
                 "the source pixels each output pixel covers, weighting the ones at its edges by how much of them it "
                 "covers. Errors are against the reference, in 8-bit code values. For 8-bit sRGB sources, see the "
                 f"<a href='{SDR_PAGE}' target='_top'>resize comparison</a>."),
        'tableNote': ("Error against the reference in 8-bit code values. <b>Bright</b> is the mean signed difference: "
                      "negative means darker than the reference. The reference is a plain average, so sharper filters "
                      "also differ from it at edges."),
        'groups': grps, 'items': items,
        'sourceOption': 'Reference (4×4 average in scene-linear light)',
        'sourceNote': ("Each pixel is the average of its 4×4 block of source pixels (at ×2.13, of the source pixels "
                       "it covers), in scene-linear light, then the view transform: the right brightness. It is not "
                       "the sharpest result, and a plain average still lets some fine detail alias (moiré in "
                       "BrightRings' discs at ×2.13), so it is a reference for brightness, not an ideal filter."),
        'defaults': {'src': 'sparks', 'a': 'source', 'b': 'hdr_ff_ocio_hc_ocio'},
        'presets': [
            {'label': 'Resize the display image vs scene-linear', 'src': 'sparks', 'a': 'hdr_ff_ocio_zscale',
             'b': 'hdr_oiio_scene_cubic', 'mode': 'wipe'},
            {'label': 'Lanczos rings around highlights, 8×', 'src': 'sparks', 'a': 'hdr_oiio_scene_lanczos',
             'b': 'hdr_oiio_scene_cubic', 'mode': 'toggle', 'zoom': 8, 'focus': ring,
             'title': 'Lanczos in scene-linear leaves dark halos around very bright highlights; the cubic has none'},
            {'label': 'BrightRings: lanczos vs cubic in scene-linear, 4×', 'src': 'brightrings',
             'a': 'hdr_oiio_scene_lanczos', 'b': 'hdr_oiio_scene_cubic', 'mode': 'toggle', 'zoom': 4, 'focus': rings,
             'title': "Lanczos's negative lobes ring around values over 1000; the Hermite cubic has none"},
            {'label': 'FFmpeg lanczos without and with highlightcomp, 8×', 'src': 'sparks',
             'a': 'hdr_ff_zscale_ocio', 'b': 'hdr_ff_ocio_hc_ocio', 'mode': 'toggle', 'zoom': 8, 'focus': ring,
             'title': "OIIO's rangecompress/rangeexpand around zscale's lanczos, as a CLF, removes the halos"},
            {'label': 'highlightcomp vs anti-ringing clamp, 8×', 'src': 'sparks',
             'a': 'hdr_oiio_scene_lanczos_hc', 'b': 'hdr_ff_antiring_ocio', 'mode': 'toggle', 'zoom': 8,
             'focus': ring, 'title': "Both remove the halos; highlightcomp also dims the sparks, the clamp keeps "
             "their light"},
            {'label': 'BrightRings: highlightcomp without and with its light restored, 4×', 'src': 'brightrings',
             'a': 'hdr_oiio_scene_lanczos_hc', 'b': 'hdr_py_scene_lanczos_hc_energy', 'mode': 'toggle', 'zoom': 4,
             'title': "Highlightcomp dims the discs' fine rings until their colour shows; restoring the light "
             "makes them white again"},
            {'label': 'Anti-ringing clamp vs highlightcomp with its light restored, 8×', 'src': 'sparks',
             'a': 'hdr_ff_antiring_ocio', 'b': 'hdr_py_scene_lanczos_hc_energy', 'mode': 'toggle', 'zoom': 8,
             'focus': ring},
            {'label': 'BrightRings: clamp negatives vs anti-ringing clamp, 4×', 'src': 'brightrings',
             'a': 'hdr_oiio_scene_lanczos_clamp', 'b': 'hdr_ff_antiring_ocio', 'mode': 'toggle', 'zoom': 4,
             'focus': rings, 'title': "Clamping negatives leaves the halos black; clamping to each block's range "
             "removes them"},
            {'label': 'Sparks ×2.13: lanczos vs highlightcomp, light restored and clamped', 'src': 'sparks_frac',
             'a': 'hdr_oiio_scene_lanczos', 'b': 'hdr_py_scene_lanczos_hc_energy_clamp', 'mode': 'toggle', 'zoom': 4,
             'focus': ring_frac, 'title': "At 4096 to 1920 lanczos still leaves halos; the restored, clamped "
             "highlightcomp has none"},
            {'label': 'BrightRings ×2.13: reference vs cubic', 'src': 'brightrings_frac', 'a': 'source',
             'b': 'hdr_oiio_scene_cubic', 'mode': 'toggle', 'zoom': 2,
             'title': "At a fractional factor the plain average shows moiré in the discs' rings; the cubic "
             "smooths them"},
            {'label': 'highlightcomp: oiiotool vs FFmpeg', 'src': 'sparks', 'a': 'hdr_oiio_scene_lanczos_hc',
             'b': 'hdr_ff_ocio_hc_ocio', 'mode': 'diff'},
            {'label': "Lanczos6 vs Lanczos4 in scene-linear, 8×", 'src': 'sparks', 'a': 'hdr_ff_zscale_ocio',
             'b': 'hdr_ff_zscale_l4_ocio', 'mode': 'toggle', 'zoom': 8, 'focus': ring,
             'title': "Two lobes (Nuke's Lanczos4) ring less than three (Lanczos6, lanczos3), but still ring"},
            {'label': "Lanczos4: zscale vs Nuke", 'src': 'sparks', 'a': 'nuke_lanczos4', 'b': 'hdr_ff_zscale_l4_ocio',
             'mode': 'diff', 'title': "zscale's lanczos with param_a=2 is close to Nuke's Lanczos4, not identical"},
            {'label': "Desk: ACEScct lanczos3 vs Log3G10/REDWideGamutRGB Lanczos4", 'src': 'desk',
             'a': 'hdr_oiio_acescct_lanczos', 'b': 'hdr_ff_rwg_l4_ocio', 'mode': 'toggle', 'zoom': 2,
             'title': "Nearly the same; the camera log is slightly closer to the reference"},
            {'label': "BrightRings in log: overflowed pixels, 4×", 'src': 'brightrings', 'a': 'source',
             'b': 'hdr_ff_acescct_l4_ocio', 'mode': 'toggle', 'zoom': 4, 'focus': rings,
             'title': "Colors outside the log's gamut overflow to infinity next to lanczos's overshoot"},
        ],
        'footer': footer + (
            "<p>BrightRings and Desk are from the <a href='https://github.com/AcademySoftwareFoundation/openexr-images' "
            "target='_top'>OpenEXR test images</a>; Sparks is from Netflix's open content. All are treated as "
            "ACES2065-1.</p>"
            f"<p>See <a href='{SITE}/Resizing.html#scene-linear-openexrs' target='_top'>Downscaling: "
            f"scene-linear OpenEXRs</a> and the <a href='{SDR_PAGE}' target='_top'>resize comparison</a> for "
            f"8-bit sRGB sources. Generated by <a href='{REPO}/blob/main/tests/resize-test.py' "
            "target='_top'>tests/resize-test.py</a>.</p>"),
    }), srcs)

if __name__ == "__main__":
    main()
