---
layout: default
title: RGB to YCbCr Conversion
nav_order: 3
parent: Encoding Overview

---



# RGB to YCbCr Conversion <a name="yuv"></a>

We would like ffmpeg to do as little as possible in terms of color space conversion. i.e. what comes in, goes out. The problem is that most of the codecs prefer to convert from RGB to YUV conversion (technically YCbCr). Do be aware that a number of codecs do support native RGB encoding (including h264, hevc, vp9, av1), but they are not typically supported in web browsers.

The main problem is that ffmpeg by default assumes that any unknown still image format has a color space of [rec601](https://en.wikipedia.org/wiki/Rec._601) which is very unlikely to be the color space your source media was generate in. So unless you tell it otherwise it will attempt to convert from that colorspace producing a color shift.

Separately, all the video formats typically do not use the full numeric range [0-255] but instead the Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantization artifacts for 8-bit encoding (the standard for web playback). This fortunately is something you can change, [see TV vs. Full range](Quickstart.html#tv-vs-full-range-). below. The other option is to use higher bit depth, e.g. 10-bit or 12 bit for formats such as [ProRes](Encoding.html#prores-).

Even if you are sticking to 8-bits encodes, if your source media is able to have a higher bit-depth (e.g. you are able to write out 16-bit PNG's to do the encode) it will help with the accuracy of the RGB to YUV conversion, particularly if you are using libswscale (see below).

For more information, see: [https://trac.ffmpeg.org/wiki/colorspace](https://trac.ffmpeg.org/wiki/colorspace)

For examples comparing these see: [here](https://academysoftwarefoundation.github.io/EncodingGuidelines/tests/chip-chart-yuvconvert/compare.html)

## colormatrix filter

```console
-vf "colormatrix=bt470bg:bt709"
```

This is the most basic colorspace filtering. bt470bg is essentially part of the bt601 spec.  See: [https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix](https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix)

Example:

<!---
name: test_colormatch_raw
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
wedges:
   rawcolor:
      -c:v: libx264
      -pix_fmt: yuv444p10le
      -preset: placebo
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       between: 0.37125, 0.37126
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
    -pix_fmt yuv444p10le -vf "colormatrix=bt470bg:bt709" \
    -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
    ./chip-chart-yuvconvert/spline444colormatrix2.mp4
```

There are a couple of issues with this filter:

* only supports 8bpc (8-bit per component) pixel formats
* Its slower than the alternatives.

## colorspace filter

```console
 -vf "colorspace=bt709:iall=bt601-6-625:fast=1"
 ```

Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too.  The second part `-vf "colorspace=bt709:iall=bt601-6-625:fast=1"` encodes for the output being bt709, rather than the default bt601 matrix. iall=bt601-6-625 says to treat all the input (colorspace, primaries and transfer function) with the bt601-6-625 label). fast=1 skips gamma/primary conversion in a mathematically correct way.  See:  [https://ffmpeg.org/ffmpeg-filters.html#colorspace](https://ffmpeg.org/ffmpeg-filters.html#colorspace)

Example:

<!---
name: test_colormatch_colorspace
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le -vf "colorspace=bt709:iall=bt601-6-625:fast=1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1  \
   ./chip-chart-yuvconvert/spline444colorspace.mp4
```

## zscale filter

```console
-vf "zscale=m=709:min=709:rangein=full:range=limited"
```

[zscale](https://github.com/sekrit-twc/zimg) is an alternative to libswscale. **This is the recommended filter for RGB to YCbCr conversion.** It is required to be explicitly compiled into ffmpeg (`--enable-libzimg`); the Docker builds and the Conan recipe in this repository both enable it.

We previously recommended libswscale here on the basis that it looked very slightly better. More careful measurement against a reference implementation shows the opposite: libswscale has a systematic bias in its full-range to limited-range conversion, placing white above the specification value at every bit depth, while zscale matches the specification exactly.

| Bit depth | scale (libswscale) | zscale | BT.709 specification |
| :--- | :--- | :--- | :--- |
| 8-bit | 236 | 235 | 235 |
| 10-bit | 943 | 940 | 940 |
| 12-bit | 3774 | 3760 | 3760 |

The error is luma only and grows with brightness; black and chroma are correct. It is small in absolute terms — one code value at 8-bit is not visible in a single pass — but it is systematic, it accumulates across round trips, and it grows in absolute terms as you move to higher bit depths. For the full measurements, including the reverse YCbCr to RGB direction, see [Colour range accuracy](EncodeSwsScale.html#colour-range-accuracy-prefer-zscale-for-range-conversions).

More detailed docs are: [here](http://underpop.online.fr/f/ffmpeg/help/zscale.htm.gz)

Example:

<!---
name: test_colormatch_zscale
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le -vf "zscale=m=709:min=709:rangein=full:range=limited" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1  \
   ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```

## libswscale filter

```console
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.  [https://www.ffmpeg.org/ffmpeg-filters.html#scale-1](https://www.ffmpeg.org/ffmpeg-filters.html#scale-1)

This is the most widely available filter, since libswscale is always compiled in, and it is what you will find in most existing command lines. However it carries the range-conversion bias described in the [zscale](#zscale-filter) section above, so we now recommend zscale where it is available. If you are stuck with libswscale, note that the bias applies whenever the output is limited range — which includes leaving the range unspecified, since that is the default for YCbCr output. Using `out_range=full` avoids it, at the cost of producing full-range video.

Example:

<!---
name: test_colormatch_libswscale
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le \
   -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1  \
   ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```

Note, there are a lot of other flags often used with the swscale filter (such as -sws_flags spline+full_chroma_int+accurate_rnd ) which really have minimal impact in the RGB to YCbCr conversion, if you are not resizing the image. For more details on this see [SWS Flags](EncodeSwsScale.html) section.
