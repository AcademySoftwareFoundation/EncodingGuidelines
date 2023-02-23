---
layout: default
title: Color Preservation
nav_order: 3
parent: Encoding Overview

---



# RGB to YCrCb Conversion <a name="yuv"></a>
We would like ffmpeg to do as little as possible in terms of color space conversion. i.e. what comes in, goes out. The problem is that most of the codecs are doing some sort of RGB to YUV conversion (technically YCrCb). The notable exception is x264rgb (see below).

The main problem is that ffmpeg by default assumes that any unknown still image format has a color space of [rec601](https://en.wikipedia.org/wiki/Rec._601) which is very unlikely to be the color space your source media was generate in. So unless you tell it otherwise it will attempt to convert from that colorspace producing a color shift.

Separately, all the video formats typically do not use the full numeric range [0-255] but instead the Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantisation artifacts for 8-bit encoding (the standard for web playback). This fortunately is something you can change, [see TV vs. Full range](Quickstart.html#tv-vs-full-range-). below. The other option is to use higher bit depth, e.g. 10-bit or 12 bit for formats such as [ProRes](Encoding.html#prores-).

For more information, see: [https://trac.ffmpeg.org/wiki/colorspace](https://trac.ffmpeg.org/wiki/colorspace)

TODO -- Review the SWS_Flags.

For examples comparing these see: [here](https://academysoftwarefoundation.github.io/EncodingGuidelines/tests/chip-chart-yuvconvert/compare.html)

## colormatrix filter
```
-vf "colormatrix=bt470bg:bt709"
```
This is the most basic colorspace filtering. bt470bg is essentially part of the bt601 spec.  See: [https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix]()
This is the most basic colorspace filtering. bt470bg is essentially part of the bt601 spec.  See: [https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix]()
e.g.

<!---
name: test_colormatch_raw
sources: 
- sourceimages/chip-chart-1080-noicc.png.yml
wedges:
   rawcolor:
      -c:v: libx264
      -pix_fmt: yuv444p10le
      -preset: placebo
-->
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
    -sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" \
    -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
    ./chip-chart-yuvconvert/spline444colormatrix2.mp4
```

## colorspace filter
```
 -vf "colorspace=bt709:iall=bt601-6-625:fast=1"
 ```
Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too.  The second part `-vf "colorspace=bt709:iall=bt601-6-625:fast=1"` encodes for the output being bt709, rather than the default bt601 matrix. iall=bt601-6-625 says to treat all the input (colorspace, primaries and transfer function) with the bt601-6-625 label). fast=1 skips gamma/primary conversion in a mathematically correct way.  See:  [https://ffmpeg.org/ffmpeg-filters.html#colorspace](https://ffmpeg.org/ffmpeg-filters.html#colorspace)
e.g.

<!---
name: test_colormatch_colorspace
sources: 
- sourceimages/chip-chart-1080-noicc.png.yml
-->
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709  \
   ./chip-chart-yuvconvert/spline444colorspace.mp4
```

## libswscale filter

```
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```
Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.  [https://www.ffmpeg.org/ffmpeg-filters.html#scale-1](https://www.ffmpeg.org/ffmpeg-filters.html#scale-1)

This is the recommended filter.
e.g.

<!---
name: test_colormatch_libswscale
sources: 
- sourceimages/chip-chart-1080-noicc.png.yml
-->
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709  \
   ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```
