---
layout: default
title: RGB to Y'CbCr Conversion
nav_order: 3
parent: Encoding Overview

---

# RGB to Y'CbCr Conversion <a name="yuv"></a>

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

{: .note }
> This is the starting point for the color conversion pages. For the converter we recommend and its options, see
> [FFmpeg zscale Filter](EncodeZscale.html); for 4:2:2 and 4:2:0, [Chroma Siting](ChromaSiting.html); for the tags that
> tell players how to display the result, [Color Metadata and Web Color Preservation](WebColorPreservation.html); and
> if `zscale` is not available, [FFmpeg swscale Filter](EncodeSwsScale.html).

We would like ffmpeg to do as little as possible in terms of color space conversion. i.e. what comes in, goes out. The problem is that most of the codecs prefer to convert from RGB to Y'CbCr (often called YUV). Do be aware that a number of codecs do support native RGB encoding (including H.264, hevc, vp9, av1), but they are not typically supported in web browsers; see [RGB Encoding](RGBEncoding.html).

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

Separately, Y'CbCr video normally uses limited range (16-235 for Y' at 8-bit), which can cause banding at 8-bit. Encoding at 10-bit avoids this; see [TV vs. Full range](#tvfull).

Even if you are sticking to 8-bits encodes, if your source media is able to have a higher bit-depth (e.g. you are able to write out 16-bit PNG's to do the encode) it will help with the accuracy of the RGB to Y'CbCr conversion. Use zscale for it: libswscale's errors are larger with 10-bit and 16-bit sources (see below).

For more information, see: [https://trac.ffmpeg.org/wiki/colorspace](https://trac.ffmpeg.org/wiki/colorspace)

For examples comparing these see the [conversion comparison page](tests/chip-chart-yuvconvert/compare.html).

## Comparison

We measured each filter converting a 16-bit RGB DPX of the SMPTE RP 219 color bars to BT.709 limited-range
Y'CbCr (4:4:4), against the ideal conversion, on FFmpeg 6.0 and 9.0, using the example commands below. Errors are
the worst case over the patches, in code values, as Y'/Cb/Cr; 10-bit white should be 940.

| Filter | 10-bit white | 10-bit error | 8-bit error | Notes |
| :--- | :--- | :--- | :--- | :--- |
| [zscale](#zscale-filter) | 940 | 0 / 0 / 0 | 0 / 0 / 0 | Recommended |
| [scale (libswscale)](#libswscale-filter) | 943 | 3 / 2 / 2 | 2 / 1 / 1 | Also centres 4:2:2/4:2:0 chroma |
| [scale with `flags=unstable`](#the-new-libswscale-code-flagsunstable) (8.1+) | 940 | 1 / 1 / 1 | 1 / 1 / 1 | 4:4:4 only; 4:2:2/4:2:0 are the same as `scale` |
| [colorspace](#older-filters-colorspace-and-colormatrix) | 943 | 3 / 2 / 2 | 2 / 1 / 1 | libswscale does the RGB conversion before it |
| [colormatrix](#older-filters-colorspace-and-colormatrix) | 940 | 10 / 5 / 4 | 3 / 1 / 1, 25 / 13 / 8 on 9.0 | 8-bit only; converts twice from 7.1 |

The `flags=unstable` row is from FFmpeg 8.1, 9.0.2 and 9.1. For the white level at every bit depth, see
[FFmpeg swscale Filter](EncodeSwsScale.html#color-conversion-use-zscale).

## zscale filter

```console
-vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1"
```

[zscale](https://github.com/sekrit-twc/zimg) is an alternative to libswscale. **This is the recommended filter for RGB to Y'CbCr conversion.** It is required to be explicitly compiled into ffmpeg (`--enable-libzimg`); the Docker builds and the Conan recipe in this repository both enable it.

`matrix=709` and `range=limited` describe the output; zscale tags its output frames with the matrix and range. The
input is read from the frames (RGB is always full range, JPEG and video use their tags), so leave it alone unless
the source has no tags; see [Sources without tags](EncodeZscale.html#sources-without-tags). `filter=lanczos` is the filter used for 4:2:2/4:2:0 chroma. `setparams` adds the
primaries and transfer function tags, which zscale leaves alone. For all the options, see
[FFmpeg zscale Filter](EncodeZscale.html).

We previously recommended libswscale here on the basis that it looked very slightly better. More careful
measurement against a reference implementation shows the opposite: libswscale gets the white level wrong in its
full-range to limited-range conversion when the source is 10-bit or higher (943 instead of 940 at 10-bit, 3774
instead of 3760 at 12-bit), while zscale matches the specification exactly. The error is small in absolute terms,
but it is systematic and it accumulates across round trips. libswscale also centres the chroma when subsampling to
4:2:2 or 4:2:0, where professional formats and H.264/HEVC expect it co-sited; zscale co-sites it. For the full
measurements see [FFmpeg swscale Filter](EncodeSwsScale.html#color-conversion-use-zscale) and
[Chroma Siting](ChromaSiting.html).

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
ffmpeg -y -i inputfile.png \
   -pix_fmt yuv444p10le -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   outputfile.mp4
```

## libswscale filter

```console
-vf "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709:range=tv"
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
ffmpeg -y -i inputfile.png \
   -pix_fmt yuv444p10le \
   -vf "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709:range=tv" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   outputfile.mp4
```

Note, there are a lot of other flags often used with the swscale filter (such as -sws_flags spline+full_chroma_int+accurate_rnd ) which really have minimal impact in the RGB to Y'CbCr conversion, if you are not resizing the image. For more details on this see [SWS Flags](EncodeSwsScale.html) section.

### The new libswscale code (`flags=unstable`) {#the-new-libswscale-code-flagsunstable}

libswscale is being rewritten. From FFmpeg 8.1 the new conversion code can be turned on with the `unstable` flag
("allow experimental new code"), set on the filter itself:

```console
-vf "scale=out_color_matrix=bt709:out_range=tv:flags=unstable,setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709:range=tv"
```

For 4:4:4 output it puts white where it should be (940 at 10-bit, 3760 at 12-bit), within one code value of
`zscale` (FFmpeg 8.1, 9.0.2 and 9.1). For 4:2:2 and 4:2:0, which most delivery formats use, it makes no difference
yet: the output is identical to plain `scale`, white level and centered chroma included. The global
`-sws_flags unstable` has no effect on this, and on 9.1 some format pairs (for example 10-bit RGB to 12-bit Y'CbCr)
log "No backend found for operations" and silently fall back to the old code.

It is not ready to replace `zscale`, but it is where libswscale is heading; once the new code is the default, and
covers subsampled formats, we expect to revisit this recommendation. The test configs for it are in
`enctests/test_configs/color_tests.yml`.

## Older filters: colorspace and colormatrix {#older-filters-colorspace-and-colormatrix}

FFmpeg also has two older filters that change the matrix of Y'CbCr video, `colorspace` and `colormatrix`. You will
find them in older command lines, but we do not recommend either for RGB sources:

* **Neither converts from RGB.** Both only convert between Y'CbCr matrices, so FFmpeg inserts libswscale before
  them to convert the RGB to Y'CbCr first, and the result has at least libswscale's errors (white at 943 at 10-bit).
* **`colormatrix` is 8-bit only**, so a 10-bit encode goes through 8-bit (errors of up to 10 code values at 10-bit),
  and from FFmpeg 7.1 the `-colorspace bt709` flag makes libswscale convert to BT.709 first, so it converts twice
  (up to 25 code values out at 8-bit on 9.0).
* **They tag the output their own way.** `colorspace` tags the BT.709 transfer function, which from FFmpeg 7.1
  `-color_trc` cannot override; `colormatrix` sets neither primaries nor transfer function.

Use `zscale` instead. If you are converting video that is already Y'CbCr from one matrix to another,
`zscale=matrix=709` does that too.

<details markdown="block">
  <summary>The tested commands for colorspace and colormatrix</summary>

These commands are kept so the test suite keeps checking the errors above.

`colorspace=bt709` converts to, and tags, BT.709; `iall=bt601-6-625` treats all the input (matrix, primaries and
transfer function) as BT.601-6-625, and `fast=1` skips the gamma/primary conversion. See the
[colorspace documentation](https://ffmpeg.org/ffmpeg-filters.html#colorspace).

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
ffmpeg -y -i inputfile.png \
   -pix_fmt yuv444p10le -vf "colorspace=bt709:iall=bt601-6-625:fast=1" \
   -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
   -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
   outputfile.mp4
```

`colormatrix=bt470bg:bt709` converts from BT.601 (`bt470bg`) to BT.709. See the
[colormatrix documentation](https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix).

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
ffmpeg -y -i inputfile.png \
    -pix_fmt yuv444p10le -vf "colormatrix=bt470bg:bt709" \
    -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
    outputfile.mp4
```

</details>

## TV vs. Full range {#tvfull}

Y'CbCr video normally uses limited range (also called TV or legal range) rather than the full numeric range. At
8-bit, Y' runs from 16 to 235 and Cb and Cr from 16 to 240, with 128 as neutral; at 10-bit, Y' runs from 64 to 940
and Cb and Cr from 64 to 960, with 512 as neutral. Full range (also called PC range) uses every code value.

At 8-bit, limited range leaves only 219 levels for luminance, which can show as banding in smooth gradients such as
skies or shadows. At 10-bit there are 876, which is usually enough to remove the banding while staying in limited
range:

| Bit Depth | Range | Banding Risk | Notes |
| :--- | :--- | :--- | :--- |
| **8-bit** | **Limited (TV)** | **High** | Most prone to banding in gradients. |
| **8-bit** | **Full (PC)** | **Medium** | Better, but not always supported by hardware players. |
| **10-bit** | **Limited (TV)** | **Low** | Preferred for review. For browser support of 10-bit H.264, see [H.264 Bitdepth](Encodeh264.html#h264-bitdepth). |

{: .important }
We recommend 10-bit limited range over 8-bit full range. The file size is comparable, if not a little smaller than
8-bit, and it removes most of the quantization problems seen at 8-bit. Whichever you use, check playback on your
target players (e.g. browsers, VLC, RV, QuickTime Player).

If you have to stay at 8-bit, you can encode full range by setting the output range in the zscale filter:

```console
-vf "zscale=matrix=709:range=full:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1"
```

zscale tags the frames as full range. Also add `-color_range pc`: from FFmpeg 7.1, many encoders (including FFV1,
ProRes and DNxHR) only accept limited range, and without it `ffmpeg` silently converts the frames back to limited
range. `libx264` and `libx265` accept full range either way. See
[Some encoders only accept limited range](FFmpegChanges.html#limited-range-encoders-71).

A full example encode would look like:

<!---
name: test_fullrange
sources: 
- sourceimages/radialgrad.png.yml
comparisontest:
   - testtype: ycbcr
     range: pc
     # Limits (10-bit code values): just above the result of this command, FFmpeg 6.0 and 9.0, 2026-10-26.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 6
     - assert: less
       value: mean_error_10bit
       less: 1.3
     - assert: less
       value: max_error_10bit
       less: 12
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: iec61966-2-1
     - assert: stringmatch
       value: colr
       string: nclx 1/13/1 pc
-->
```console
ffmpeg -y -loop 1 -i inputfile.png \
    -pix_fmt yuv420p -vf "zscale=matrix=709:range=full:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
    -c:v libx264 -t 5 -crf 18 \
    -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 outputfile.mp4
```

We have seen the full range encoding work across all browsers, and a number of players including RV.

For more details see:

* [Comparing full range vs. limited (TV) range vs. dithering](tests/greyramp-fulltv/compare.html)
