---
layout: default
title: RGB to YCbCr Conversion
nav_order: 3
parent: Encoding Overview

---

# RGB to YCbCr Conversion <a name="yuv"></a>

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

We would like ffmpeg to do as little as possible in terms of color space conversion. i.e. what comes in, goes out. The problem is that most of the codecs prefer to convert from RGB to YUV conversion (technically YCbCr). Do be aware that a number of codecs do support native RGB encoding (including h264, hevc, vp9, av1), but they are not typically supported in web browsers.

Without a filter that sets the matrix, FFmpeg's conversion depends on the version. Before FFmpeg 7.1 it converts
any untagged still image (which is most of them) with the [rec601](https://en.wikipedia.org/wiki/Rec._601) matrix,
which is very unlikely to be the color space your source media was generated in, producing a color shift. From 7.1,
the `-colorspace` flag sets the matrix it converts with, but the conversion is done by libswscale, with the problems
described below. Either way, we recommend converting explicitly with the zscale filter; see
[FFmpeg Version Changes](FFmpegChanges.html) for what changed in 7.1.

From 7.1, keep three things apart: the `-pix_fmt`, `-colorspace` and `-color_range` flags *convert* to what they
ask for, filters such as `zscale` *transform* the pixels and set the tags, and `setparams` *relabels* without
touching the pixels. So `-colorspace` on a file that is already Y'CbCr changes its pixels rather than fixing its
tag; to fix a wrong tag, use `setparams`. See [Relabelling a file](FFmpegChanges.html#relabelling-a-file).

Separately, all the video formats typically do not use the full numeric range [0-255] but instead the Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantization artifacts for 8-bit encoding (still the most widely supported for web playback). This fortunately is something you can change, see [TV vs. Full range](Quickstart.html#tvfull). The other option is to use higher bit depth, e.g. 10-bit or 12 bit for formats such as [ProRes](EncodeProres.html).

Even if you are sticking to 8-bits encodes, if your source media is able to have a higher bit-depth (e.g. you are able to write out 16-bit PNG's to do the encode) it will help with the accuracy of the RGB to YUV conversion. Use zscale for it: libswscale's errors are larger with 10-bit and 16-bit sources (see below).

For more information, see: [https://trac.ffmpeg.org/wiki/colorspace](https://trac.ffmpeg.org/wiki/colorspace)

For examples comparing these see the [conversion comparison page](tests/chip-chart-yuvconvert/compare.html).

## Comparison

We measured each filter converting a 16-bit RGB DPX of the SMPTE RP 219 colour bars to BT.709 limited-range
Y'CbCr (4:4:4), against the ideal conversion, on FFmpeg 6.0 and 9.0, using the example commands below. Errors are
the worst case over the patches, in code values, as Y'/Cb/Cr; 10-bit white should be 940.

| Filter | 10-bit white | 10-bit error | 8-bit error | Notes |
| :--- | :--- | :--- | :--- | :--- |
| [zscale](#zscale-filter) | 940 | 0 / 0 / 0 | 0 / 0 / 0 | Recommended |
| [scale (libswscale)](#libswscale-filter) | 943 | 3 / 2 / 2 | 2 / 1 / 1 | Also centres 4:2:2/4:2:0 chroma |
| [colorspace](#colorspace-filter) | 943 | 3 / 2 / 2 | 2 / 1 / 1 | libswscale does the RGB conversion before it |
| [colormatrix](#colormatrix-filter) | 940 | 10 / 5 / 4 | 3 / 1 / 1, 25 / 13 / 8 on 9.0 | 8-bit only; converts twice from 7.1 |

## zscale filter

```console
-vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1"
```

[zscale](https://github.com/sekrit-twc/zimg) is an alternative to libswscale. **This is the recommended filter for RGB to YCbCr conversion.** It is required to be explicitly compiled into ffmpeg (`--enable-libzimg`); the Docker builds and the Conan recipe in this repository both enable it.

`matrix=709` and `range=limited` describe the output; zscale tags its output frames with the matrix and range. The
input is read from the frames (RGB is always full range, JPEG and video use their tags), so leave it alone unless
the source has no tags; see [Sources without tags](EncodeZscale.html#sources-without-tags). `filter=lanczos` is the filter used for 4:2:2/4:2:0 chroma. `setparams` adds the
primaries and transfer function tags, which zscale leaves alone. For all the options, see
[zscale Conversion](EncodeZscale.html).

We previously recommended libswscale here on the basis that it looked very slightly better. More careful measurement against a reference implementation shows the opposite: libswscale gets the white level wrong in its full-range to limited-range conversion when the source is 10-bit or higher, while zscale matches the specification exactly. The 100% white patch of the RP 219 bars, on every version from 6.0 to 9.0:

| Source | Output | scale (libswscale) | zscale | BT.709 specification |
| :--- | :--- | :--- | :--- | :--- |
| 8-bit | 8-bit | 235 | 235 | 235 |
| 10-bit | 10-bit | 943 | 940 | 940 |
| 16-bit | 10-bit | 943 | 940 | 940 |
| 10-bit | 12-bit | 3770 | 3760 | 3760 |
| 16-bit | 12-bit | 3774 | 3760 | 3760 |

The error is largest in luma, but not limited to it: from a 16-bit source the worst errors are 3 / 2 / 2 code values (Y'/Cb/Cr) at 10-bit and 14 / 7 / 7 at 12-bit. It is small in absolute terms, but it is systematic and it accumulates across round trips. libswscale also centres the chroma when subsampling to 4:2:2 or 4:2:0, where professional formats and H.264/HEVC expect it co-sited; zscale co-sites it. For the full measurements see [Colour range accuracy](EncodeSwsScale.html#colour-range-accuracy-prefer-zscale-for-range-conversions) and [Chroma Siting](ChromaSiting.html).

More detailed docs are in the [FFmpeg filter documentation](https://ffmpeg.org/ffmpeg-filters.html#zscale).

Example:

<!---
name: test_colormatch_zscale
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error
       between: [-0.5, 0.5]
     - assert: less
       value: max_error
       less: 1
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: iec61966-2-1
     - assert: stringmatch
       value: colr
       string: nclx 1/13/1 tv
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```

## libswscale filter

```console
-vf "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=iec61966-2-1"
```

Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.  [https://www.ffmpeg.org/ffmpeg-filters.html#scale-1](https://www.ffmpeg.org/ffmpeg-filters.html#scale-1)

This is the most widely available filter, since libswscale is always compiled in, and it is what you will find in most existing command lines. However it carries the white level error described in the [zscale](#zscale-filter) section above whenever the source is 10-bit or higher, and it centres 4:2:2/4:2:0 chroma, so we now recommend zscale where it is available. Encoding full range (`out_range=full`) does not avoid the errors: on 9.0 it was up to 4 code values out at 10-bit.

On 9.0, `scale` tags its output with the matrix and range, but not the primaries and transfer function, so keep the `setparams`; on 6.0 it does not tag the matrix either, so keep `-colorspace bt709` as well.

Leave `in_color_matrix` and `in_range` at their default (`auto`, which uses the frame's tags). Older command lines,
including earlier versions of this page, set `in_range=full:in_color_matrix=bt709`. That makes no difference for
RGB sources, but decodes JPEG sequences (which are BT.601) with the wrong matrix and limited-range video as full
range. Untagged video is the one case to say what the source is; see
[Sources without tags](EncodeZscale.html#sources-without-tags).

Example:

<!---
name: test_colormatch_libswscale
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     # Pins libswscale's known white level error (+3 at 10-bit), so a change in FFmpeg shows up.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error
       between: [3, 4]
     - assert: less
       value: max_error
       less: 5
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le \
   -vf "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```

Note, there are a lot of other flags often used with the swscale filter (such as -sws_flags spline+full_chroma_int+accurate_rnd ) which really have minimal impact in the RGB to YCbCr conversion, if you are not resizing the image. For more details on this see [SWS Flags](EncodeSwsScale.html) section.

## colorspace filter

```console
 -vf "colorspace=bt709:iall=bt601-6-625:fast=1"
 ```

The colorspace filter is a better quality filter than colormatrix, with SIMD so faster too, and supports 10-bit. `colorspace=bt709` converts to, and tags, BT.709. `iall=bt601-6-625` says to treat all the input (colorspace, primaries and transfer function) as BT.601-6-625, and `fast=1` skips the gamma/primary conversion. See: [https://ffmpeg.org/ffmpeg-filters.html#colorspace](https://ffmpeg.org/ffmpeg-filters.html#colorspace)

It only converts between Y'CbCr formats, so it does not avoid libswscale: FFmpeg inserts libswscale before it to convert the RGB to BT.601 Y'CbCr, and colorspace then re-matrixes that to BT.709. The result has libswscale's errors (white at 943 at 10-bit), so we do not recommend it for RGB sources. It also tags its output with the BT.709 transfer function, which from FFmpeg 7.1 `-color_trc` cannot override: on 9.0 the example below is tagged `bt709` rather than sRGB.

Example:

<!---
name: test_colormatch_colorspace
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     # Pins the known error from the libswscale conversion before the colorspace filter.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error
       between: [3, 4]
     - assert: less
       value: max_error
       less: 5
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
   -pix_fmt yuv444p10le -vf "colorspace=bt709:iall=bt601-6-625:fast=1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   ./chip-chart-yuvconvert/spline444colorspace.mp4
```

## colormatrix filter

```console
-vf "colormatrix=bt470bg:bt709"
```

This is the most basic colorspace filtering, and we do not recommend it. bt470bg is essentially part of the bt601 spec.  See: [https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix](https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix)

There are a few issues with this filter:

* It only supports 8bpc (8-bit per component) pixel formats, so a 10-bit encode goes through 8-bit; in our tests that left errors of up to 10 code values at 10-bit.
* It assumes it is given BT.601 Y'CbCr, which it relies on libswscale to produce from RGB first. From FFmpeg 7.1, the `-colorspace bt709` flag in the example below makes libswscale convert to BT.709 instead, so colormatrix converts a second time: on 9.0 the 8-bit result was up to 25 code values out.
* It does not set the primaries or transfer function, and from FFmpeg 7.1 `-color_primaries` and `-color_trc` are ignored, so on 9.0 the example below has neither tag.
* It is slower than the alternatives.

Example:

<!---
name: test_colormatch_raw
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     # Pins colormatrix's known error at 10-bit (10 code values).
   - testtype: assertresults
     tests:
     - assert: between
       value: max_error
       between: [8, 12]
-->
```console
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png \
    -pix_fmt yuv444p10le -vf "colormatrix=bt470bg:bt709" \
    -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
    ./chip-chart-yuvconvert/spline444colormatrix2.mp4
```
