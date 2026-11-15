"""
Compare ways of downsizing an image by 4, for tests/resize-compare/compare.html.

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

Run from the tests folder, with ffmpeg (with zscale) and oiiotool on the PATH:
    python resize-test.py [--outdir ./resize-compare]
"""
import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "python"))
import yuvcompare as yc  # noqa: E402

FF = 'ffmpeg -v error -y -i {src} -frames:v 1 -vf "{vf}" {out}'
OIIO_LIN = "--colorconvert srgb_tx lin_rec709 {resize} --colorconvert lin_rec709 srgb_tx"
Z709 = "primariesin=709:primaries=709"
SPARKS = "../enctests/sources/hdr_sources/sparks/SPARKS_ACES_06100.exr"
# github.com/AcademySoftwareFoundation/openexr-images, checked out next to this repository (or set OPENEXR_IMAGES)
OPENEXR_IMAGES = os.environ.get("OPENEXR_IMAGES", "../../openexr-images")
HDR_IDS = ['sparks', 'brightrings', 'desk']
# Absolute links, so the page also works when hosted on its own (it is too large to commit)
SITE = "https://academysoftwarefoundation.github.io/EncodingGuidelines"
REPO = "https://github.com/AcademySoftwareFoundation/EncodingGuidelines"
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
RC_X1, RC_A, RC_B, RC_C = 0.18, -0.54576885700225830078, 0.18351669609546661377, 284.3577880859375
# The same curve for values >= 0, as a CLF for the ocio filter (below 0.18 it is a straight line, so it does not
# mirror the curve for values below -0.18 as OIIO does).
RC_CLF = "rangecompress.clf"


def rangecompress(v):
    return f"if(lte(abs({v}),{RC_X1}),{v},sgn({v})*({RC_A}+{RC_B}*log({RC_C}*abs({v})+1)))"


def rangeexpand(v):
    return f"if(lte(abs({v}),{RC_X1}),{v},sgn({v})*(exp((abs({v})-({RC_A}))/{RC_B})-1)/{RC_C})"


def geq_rgb(fn):
    """geq applying fn to each of R, G and B. geq works in float (gbrpf32le) and does not clip."""
    return "geq=" + ":".join(f"{p}='{fn(p + '(X,Y)')}'" for p in "rgb")


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
    ('HDR sources: resizing before or after the view transform (EXR sources only)', [
        dict(v('hdr_ff_ocio_zscale', 'FFmpeg ocio, then zscale lanczos', "The view transform first, then zscale "
               "resizes the display-encoded values: the usual FFmpeg route, all in one command.",
               '-vf "ocio=...:format=rgb48,format=rgb48le,zscale=w=W:h=H:filter=lanczos"',
               FF_EXR.replace("VF", FF_OCIO + ",format=rgb48le,zscale=w={w}:h={h}:filter=lanczos,format=gbrp16le")),
             only=HDR_IDS),
        dict(v('hdr_ff_ocio_zscale_displaylinear', 'FFmpeg ocio, then zscale lanczos in display-linear', "The view "
               "transform first, then zscale converts the display image to linear light (the sRGB curve, which the "
               "ACES configs' sRGB display uses), resizes and converts back. That fixes the gamma part, but the "
               "highlights were compressed to near white by the view transform before the resize, so their energy is "
               "already gone.",
               '-vf "ocio=...:format=rgb48,format=rgb48le,zscale=...:transferin=iec61966-2-1:transfer=linear,'
               'format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,zscale=...:transferin=linear:transfer=iec61966-2-1"',
               FF_EXR.replace("VF", FF_OCIO + f",format=rgb48le,zscale={Z709}:transferin=iec61966-2-1:transfer=linear,"
                              "format=gbrpf32le,zscale=w={w}:h={h}:filter=lanczos,"
                              f"zscale={Z709}:transferin=linear:transfer=iec61966-2-1,format=gbrp16le")),
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
               "its surroundings either way.",
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
        dict(v('hdr_oiio_acescct_lanczos', 'oiiotool, lanczos3 in ACEScct (log), then OCIO', "Converts to ACEScct, "
               "a log encoding, resizes there, then applies the view, as Resolve does with a log timeline. Log values "
               "are bounded, so lanczos cannot ring far, but the averaging is on log values, which loses highlight "
               "energy.",
               f'--colorconvert ACES2065-1 ACEScct --resize:filter=lanczos3 WxH --ociodisplay:from=ACEScct ...',
               "oiiotool {exr} --colorconvert ACES2065-1 ACEScct --resize:filter=lanczos3 {w}x{h} "
               f'--ociodisplay:from=ACEScct "{DISPLAY}" "{VIEW}" -d uint16 -o {{out}}'), only=HDR_IDS),
        dict(v('hdr_oiio_scene_cubic', "oiiotool, cubic in scene-linear, then OCIO", "oiiotool's cubic filter: the "
               "same as Nuke's default Cubic (the Hermite cubic, no negative lobes).",
               f'--resize:filter=cubic WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=cubic {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_oiio_scene_mitchell', 'oiiotool, mitchell in scene-linear, then OCIO', "A softer filter with "
               "only small negative lobes, so less ringing around very bright highlights than lanczos.",
               f'--resize:filter=mitchell WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=mitchell {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_oiio_scene_gaussian', 'oiiotool, gaussian in scene-linear, then OCIO', "A filter with no negative "
               "lobes: no ringing at all, but softer.",
               f'--resize:filter=gaussian WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=gaussian {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_oiio_scene_box', 'oiiotool, box in scene-linear, then OCIO', "A box over exactly 4x4 pixels in "
               "scene-linear, then the view: the reference's method, done with oiiotool, as a check.",
               f'--resize:filter=box WxH {OIIO_VIEW}',
               "oiiotool {exr} --resize:filter=box {w}x{h} " + OIIO_VIEW + " -d uint16 -o {out}"), only=HDR_IDS),
        dict(v('hdr_ff_zscale_ocio', 'FFmpeg zscale lanczos in scene-linear, then ocio', "zscale resizes the "
               "half-float EXR directly, keeping the highlights, then the ocio filter applies the view.",
               '-vf "zscale=w=W:h=H:filter=lanczos,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le," + FF_OCIO + ",format=rgb48le")),
             only=HDR_IDS),
        dict(v('hdr_ff_zscale_mitchell_ocio', 'FFmpeg zscale mitchell in scene-linear, then ocio', "zscale's bicubic "
               "with b = c = 1/3 is the mitchell filter: the same as oiiotool's, done in FFmpeg.",
               '-vf "zscale=w=W:h=H:filter=bicubic:param_a=1/3:param_b=1/3,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=bicubic:param_a=0.3333333:param_b=0.3333333,"
                              "format=gbrpf32le," + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_zscale_hermite_ocio', "FFmpeg zscale cubic (b = c = 0, Nuke's Cubic) in scene-linear, then ocio",
               "zscale's bicubic with b = 0 and c = 0: the Hermite cubic, which has no negative lobes, so no ringing. "
               "It gives the same pixels as Nuke's default Reformat filter, Cubic, and oiiotool's cubic.",
               '-vf "zscale=w=W:h=H:filter=bicubic:param_a=0:param_b=0,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=bicubic:param_a=0:param_b=0,format=gbrpf32le," + FF_OCIO
                              + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_zscale_bicubic_ocio', 'FFmpeg zscale bicubic in scene-linear, then ocio', "zscale's bicubic "
               "with its default parameters, b = 0, c = 0.5 (Catmull-Rom; the same pixels as setting them explicitly), "
               "then the view. Sharper than mitchell, with moderate negative lobes, so some ringing around the "
               "brightest highlights, though less than lanczos.",
               '-vf "zscale=w=W:h=H:filter=bicubic,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=bicubic,format=gbrpf32le," + FF_OCIO + ",format=rgb48le")),
             only=HDR_IDS),
        dict(v('hdr_ff_zscale_clamp_ocio', 'FFmpeg zscale lanczos in scene-linear, clamp negatives, then ocio',
               "As the oiiotool clamp: geq sets anything below zero to zero, in float, so the highlights survive. "
               "(The limiter filter does not take float input, so FFmpeg would convert to integer and lose the "
               "image; colorlevels runs, but does not clamp float values.)",
               '-vf "zscale=w=W:h=H:filter=lanczos,format=gbrpf32le,geq=r=\'max(r(X\\,Y)\\,0)\':...,ocio=..."',
               FF_EXR.replace("VF", "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le,"
                              "geq=r='max(r(X\\,Y)\\,0)':g='max(g(X\\,Y)\\,0)':b='max(b(X\\,Y)\\,0)',"
                              "format=gbrpf32le," + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_zscale_hc_ocio', 'FFmpeg zscale lanczos in scene-linear with highlightcomp (geq), then ocio',
               "oiiotool's highlightcomp in FFmpeg: geq applies OIIO's rangecompress curve to each channel, zscale "
               "resizes, and a second geq applies rangeexpand. geq matches oiiotool's curves to float precision, so "
               "this differs from oiiotool only by the small differences between zscale's lanczos and oiiotool's "
               "lanczos3. The first zscale (no size) converts the half-float EXR to float without clamping; geq "
               "does not take half float, and format=gbrpf32le alone would clamp (see the last variant). geq is "
               "slow, about 0.2 s per 4K frame.",
               "-vf \"zscale,format=gbrpf32le,geq=r='" + rangecompress("r(X,Y)") + "':g=...:b=...,"
               "zscale=w=W:h=H:filter=lanczos,format=gbrpf32le,geq=r='" + rangeexpand("r(X,Y)") + "':g=...:b=...,"
               "ocio=...:format=rgb48\"",
               FF_EXR.replace("VF", "zscale,format=gbrpf32le," + geq_rgb(rangecompress) + ","
                              "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le," + geq_rgb(rangeexpand) + ","
                              "format=gbrpf32le," + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_ocio_hc_ocio', 'FFmpeg zscale lanczos in scene-linear with highlightcomp (OCIO CLF), then ocio',
               "The same, with the rangecompress curve as a CLF Log node (cameraLinToLog, base e: logSideSlope = b, "
               "logSideOffset = a, linSideSlope = c, linSideOffset = 1, linSideBreak = 0.18) applied by the ocio "
               "filter, and inverted with inverse=1. Far faster than geq. Below the break OCIO's curve is a "
               "straight line, so values below -0.18 are not compressed (OIIO mirrors the curve for negative "
               "values). None of these sources goes below -0.18 (Desk's lowest value is -0.012), but lanczos's "
               "undershoot can, so the two versions can differ slightly next to the brightest highlights.",
               f'-vf "ocio=filetransform={RC_CLF}:format=gbrpf32le,format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,'
               f'ocio=filetransform={RC_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le,ocio=...:format=rgb48"',
               FF_EXR.replace("VF", f"ocio=filetransform={RC_CLF}:format=gbrpf32le,format=gbrpf32le,"
                              "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le,"
                              f"ocio=filetransform={RC_CLF}:inverse=1:format=gbrpf32le,format=gbrpf32le,"
                              + FF_OCIO + ",format=rgb48le")), only=HDR_IDS),
        dict(v('hdr_ff_acescct_ocio', 'FFmpeg ocio to ACEScct, zscale lanczos, then ocio', "The log-space route in "
               "FFmpeg: the ocio filter converts to ACEScct, zscale resizes the log values, and a second ocio filter "
               "applies the view. The format filter between ocio and zscale is needed: without it the filter graph "
               "fails (8.1, 9.0.2 and 9.1-dev).",
               '-vf "ocio=input=ACES2065-1:output=ACEScct:format=gbrpf32le,format=gbrpf32le,zscale=w=W:h=H:filter=lanczos,'
               'ocio=input=ACEScct:display=...:view=..."',
               FF_EXR.replace("VF", "ocio=input=ACES2065-1:output=ACEScct:format=gbrpf32le,format=gbrpf32le,"
                              "zscale=w={w}:h={h}:filter=lanczos,format=gbrpf32le,"
                              f"ocio=input=ACEScct:display={DISPLAY}:view={VIEW}:format=rgb48,format=rgb48le")),
             only=HDR_IDS),
        dict(v('hdr_ff_f32_trap', 'FFmpeg format=gbrpf32le, then zscale (wrong)', "The same, with format=gbrpf32le "
               "first. It looks harmless, but FFmpeg converts the half-float EXR with libswscale, which clamps every "
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
               "highlights, less than Lanczos6.", 'Reformat filter=Lanczos4',
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


def scene_linear_reference(exr, k=4):
    """4x4 block average of the scene-linear EXR, then OCIO's ACES 2.0 SDR view for sRGB (as display values)."""
    import OpenImageIO as oiio
    lin = np.array(oiio.ImageBuf(exr).get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)
    h, w = lin.shape[0] // k, lin.shape[1] // k
    block = lin[:h * k, :w * k].reshape(h, k, w, k, 3).mean((1, 3)).astype(np.float32)
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
    parser.add_argument("--outdir", default="./resize-compare")
    args = parser.parse_args()
    root = args.outdir
    os.makedirs(root, exist_ok=True)
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
    desk_rgb = os.path.join(root, "desk-rgb.exr")
    exrs = [
        {'id': 'sparks', 'label': 'Sparks (HDR EXR)', 'exr': SPARKS, 'window': (512, 270),
         'description': "Netflix's Sparks, frame 6100: 4096×2160 half-float ACES2065-1 OpenEXR with highlights up to "
                        "about 200× scene white, shrunk to 1024×540; shown and measured is the 512×270 part with the "
                        "most highlights."},
        {'id': 'brightrings', 'label': 'BrightRings (EXR)', 'exr': os.path.join(OPENEXR_IMAGES, "TestImages/BrightRings.exr"),
         'description': "BrightRings.exr from the OpenEXR test images: 800×800 half-float, rings with values up to 1025 "
                        "on a grey background (0.5), made for testing how filters with negative lobes react to HDR "
                        "values. Treated as ACES2065-1. Shrunk to 200×200."},
        {'id': 'desk', 'label': 'Desk (EXR)', 'exr': desk_rgb,
         'prepare': (desk, desk_rgb, "--ch R,G,B --cut 644x872+0+0"),
         'description': "Desk.exr from the OpenEXR test images: a 644×874 half-float photograph of a desk in front of a "
                        "backlit stained-glass window, with highlights up to about 230. Treated as ACES2065-1 (the file has no chromaticities). 874 rows "
                        "is not a multiple of 4, so the bottom two rows are cut, and the alpha channel (all 1) is "
                        "dropped: oiiotool Desk.exr --ch R,G,B --cut 644x872+0+0 -o desk-rgb.exr. Shrunk to 161×218."},
    ]
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
        display = os.path.join(root, f"{e['id']}-display.png")
        yc.run(f"oiiotool {e['exr']} {OIIO_VIEW} -d uint16 -o {display}")
        temps.append(display)
        ref, lin = scene_linear_reference(e['exr'])
        window = e.pop('window', None)
        sources.append(dict(e, path=display, reference=ref,
                            **({'crop': brightest_window(lin, *window)} if window else {}),
                            description=e['description'] + f" Viewed through OCIO's {VIEW} view for sRGB. The "
                            f"display-referred variants resize the display image oiiotool makes from it "
                            f"({e['id']}-display.png). The reference is each 4×4 block averaged in scene-linear "
                            "light, then the view transform."))
    version = yc.ffmpeg_version()
    oiio = subprocess.run(["oiiotool", "--version"], capture_output=True, text=True).stdout.strip()
    groups = GROUPS
    if not os.path.exists(os.path.join(NUKE, "nuke-cubic.exr")):
        print(f"No Nuke results in {NUKE} (run tests/resize-nuke.py in Nuke): leaving out the Nuke variants")
        groups = [g for g in GROUPS if not g[0].startswith("Nuke")]
    srcs, grps, items = yc.run_images(root, sources, groups)
    for f in temps:
        os.remove(f)
    yc.print_table(f"{version}, OIIO {oiio}", srcs, grps, items, STATS)
    ring = worst_pixel(yc.read_rgb(os.path.join(root, "sparks-hdr_oiio_scene_lanczos.png")),
                       yc.read_rgb(os.path.join(root, "sparks-reference.png")))
    rings = worst_pixel(yc.read_rgb(os.path.join(root, "brightrings-hdr_oiio_scene_lanczos.png")),
                        yc.read_rgb(os.path.join(root, "brightrings-reference.png")))
    edge = worst_pixel(yc.read_rgb(os.path.join(root, "animation-scale_lanczos.png")),
                       yc.read_rgb(os.path.join(root, "animation-reference.png")))

    extra = timing_table()

    yc.write_page(root, {
        **({'extra': extra} if extra else {}),
        'pageTitle': "Resize Compare",
        'title': "Resizing: FFmpeg, oiiotool, linear light and HDR",
        'lede': ("Each image shrunk to a quarter of its size by FFmpeg (<code>scale</code> and <code>zscale</code>) and by <code>oiiotool</code>, on the gamma-encoded values and in linear light. The <b>reference</b> averages each 4×4 block of pixels in linear light, which gives fine detail its right brightness; for the EXR sources (Sparks, BrightRings and Desk, treated as ACES2065-1), in scene-linear light before OCIO's ACES 2.0 view, with extra variants that resize before or after the view transform. Errors are against the reference, in 8-bit code values."),
        'tableNote': ("Error against the reference in 8-bit code values. <b>Bright</b> is the mean signed difference: "
                      "negative means darker than the reference, which is what resizing gamma-encoded values does to "
                      "fine detail. The reference is a plain average, so sharper filters also differ from it at edges."
),
        'unit': '8-bit code values', 'unitName': '8-bit code', 'unitMax': 255,
        'stats': STATS, 'rankKey': 'mean', 'groups': grps, 'items': items, 'rowLabel': 'Resize',
        'sourceOption': 'Reference (4×4 average in linear light)', 'sourceLabel': 'Reference',
        'sourceNote': ("Each pixel is the average of its 4×4 block of source pixels, in linear light: the right "
                       "brightness. It is not the sharpest result, and a plain average still lets some fine detail "
                       "alias (the zone plate's outer rings), so it is a reference for brightness, not an ideal "
                       "filter."),
        'defaults': {'a': 'source', 'b': 'scale_bicubic'},
        'presets': [
            {'label': 'Zone plate: FFmpeg default vs reference', 'src': 'zoneplate', 'a': 'source',
             'b': 'scale_bicubic', 'mode': 'wipe',
             'title': 'The outer rings should turn flat grey; resizing the encoded values leaves them darker'},
            {'label': 'Same filter, gamma vs linear light', 'src': 'zoneplate', 'a': 'zscale_lanczos',
             'b': 'zscale_lanczos_linear', 'mode': 'toggle'},
            {'label': 'Lanczos ringing on animation, 4×', 'src': 'animation', 'a': 'scale_area', 'b': 'scale_lanczos',
             'mode': 'toggle', 'zoom': 4, 'focus': edge},
            {'label': 'HDR: resize the display image vs scene-linear', 'src': 'sparks', 'a': 'zscale_lanczos',
             'b': 'hdr_oiio_scene_mitchell', 'mode': 'wipe'},
            {'label': 'HDR: lanczos rings around highlights, 8×', 'src': 'sparks', 'a': 'hdr_oiio_scene_lanczos',
             'b': 'hdr_oiio_scene_mitchell', 'mode': 'toggle', 'zoom': 8, 'focus': ring,
             'title': 'Lanczos in scene-linear leaves dark halos around very bright highlights; mitchell much less'},
            {'label': 'BrightRings: lanczos vs cubic in scene-linear, 4×', 'src': 'brightrings',
             'a': 'hdr_oiio_scene_lanczos', 'b': 'hdr_oiio_scene_cubic', 'mode': 'toggle', 'zoom': 4, 'focus': rings,
             'title': "Lanczos's negative lobes ring around values over 1000; the Hermite cubic has none"},
            {'label': 'HDR: FFmpeg lanczos without and with highlightcomp, 8×', 'src': 'sparks',
             'a': 'hdr_ff_zscale_ocio', 'b': 'hdr_ff_zscale_hc_ocio', 'mode': 'toggle', 'zoom': 8, 'focus': ring,
             'title': "OIIO's rangecompress/rangeexpand around zscale's lanczos, done with geq, removes the halos"},
            {'label': 'highlightcomp: oiiotool vs FFmpeg', 'src': 'sparks', 'a': 'hdr_oiio_scene_lanczos_hc',
             'b': 'hdr_ff_zscale_hc_ocio', 'mode': 'diff'},
            {'label': 'FFmpeg vs oiiotool, linear light', 'src': 'chart', 'a': 'zscale_lanczos_linear',
             'b': 'oiio_lanczos3_linear', 'mode': 'diff'},
        ],
        'footer': (
            f"<p>Made with {version} and oiiotool {oiio}. Every result is a 16-bit RGB image; nothing is encoded, so "
            "the only difference is the resize. The images shown are 8-bit copies. All sources are treated as "
            "sRGB-encoded, and the linear-light versions use the sRGB curve both ways.</p>"
            "<p>BrightRings and Desk are from the <a href='https://github.com/AcademySoftwareFoundation/openexr-images' "
            "target='_top'>OpenEXR test images</a>; Sparks is from Netflix's open content.</p>"
            f"<p>See <a href='{SITE}/Resizing.html' target='_top'>Resizing</a>. Generated by "
            f"<a href='{REPO}/blob/main/tests/resize-test.py' target='_top'>tests/resize-test.py</a>.</p>"),
    }, srcs)


if __name__ == "__main__":
    main()
