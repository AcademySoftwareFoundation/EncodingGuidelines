# SMPTE RP 219 reference bars for the colour tests, straight from the spec's Y'CbCr tables.
#
# Unlike the plugin's examples there is no edge-shaping blur and no 4:2:2 resize, so every
# patch is an exact 4:4:4 code value. iq=0 (100% white in row 2, despite the plugin README
# listing the iq values the other way round) / subblack=0 / superwhite=0 keeps the patches
# inside the RGB gamut, apart from the -2% PLUGE patch, so a full-range RGB chart (e.g.
# Resolve's DPX) can match it.
#
# The references are stored as lossless FFV1 (.mkv), tagged BT.709 limited range. See ../README.md
# for how these were generated and validated. From this folder:
#
#   vspipe -c y4m -a bits=10 rp219_reference.vpy - | ffmpeg -i - \
#       -vf "setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709" \
#       -c:v ffv1 -level 3 -slicecrc 1 rp219_yuv444p10.mkv
#   (and the same with bits=12 / rp219_yuv444p12.mkv)
#
# ../generate.sh can turn them back into .y4m if a tool needs that.
import os
import vapoursynth as vs
from vapoursynth import core

core.std.LoadPlugin(os.path.expanduser("~/git/vapoursynth-colorbars/.libs/libcolorbars.dylib"))

bits = int(globals().get("bits", 10))
fmt = {10: vs.YUV444P10, 12: vs.YUV444P12}[bits]

c = core.colorbars.ColorBars(resolution=3, format=fmt, iq=0, subblack=0, superwhite=0)
c = core.std.SetFrameProps(c, _Matrix=1, _Primaries=1, _Transfer=1, _Range=1)
c.set_output()
