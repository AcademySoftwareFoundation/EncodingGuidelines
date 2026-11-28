---
layout: default
title: FFmpeg swscale Filter
nav_order: 3.6
parent: Encoding Overview
---

# FFmpeg swscale Filter

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

FFmpeg has two scalers: the built-in `scale` filter (libswscale), and `zscale` (zimg), which needs an FFmpeg built
with `--enable-libzimg` (the Docker builds and the Conan recipe in this repository enable it). This page covers
libswscale: where its color conversion goes wrong, how to replace it with `zscale`, and its options for when you do
use it.

- **Color conversion** (RGB to and from Y'CbCr, range, and chroma subsampling to 4:2:2 or 4:2:0): use `zscale`.
  libswscale puts 10-bit white at 943 instead of 940 ([below](#color-conversion-use-zscale)),
  centres the chroma when subsampling, and up to FFmpeg 9.0 assumes it is centered when converting back to RGB
  ([Chroma Siting](ChromaSiting.html#reading-back-to-rgb)). For the `zscale` options, see
  [FFmpeg zscale Filter](EncodeZscale.html).
- **Resizing**: see [Resizing](Resizing.html). Do it outside FFmpeg, or in linear light; the scaler matters much less
  than that.

## Color conversion: use zscale

{: .warning }
> libswscale has a systematic bias when converting between full range and limited (studio) range from 10-bit and
> higher sources: the result is slightly too bright. Use `zscale` for range and matrix conversions. This is not fixed
> in any release up to and including FFmpeg 9.1.

This is the detailed table; the other pages give the 10-bit figure and link here. Converting full-range RGB white
to limited-range Y'CbCr, `scale` puts white above the value the specification calls for whenever the source is
more than 8 bits, at every output bit depth. The 100% white patch of the SMPTE RP 219 bars, on every version from
6.0 to 9.1:

| Source | Output | `scale` | `scale=...:flags=unstable` (8.1+) | `zscale` | BT.709 specification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 8-bit | 8-bit | 235 | 235 | 235 | 235 |
| 8-bit | 10-bit | 940 | 940 | 940 | 940 |
| 16-bit | 8-bit | 235 | 235 | 235 | 235 |
| 10-bit | 10-bit | **943** | 940 (4:4:4 only) | 940 | 940 |
| 16-bit | 10-bit | **943** | 940 (4:4:4 only) | 940 | 940 |
| 10-bit | 12-bit | **3770** | 3760 (4:4:4 only) | 3760 | 3760 |
| 16-bit | 12-bit | **3774** | 3760 (4:4:4 only) | 3760 | 3760 |

- **The error is a gain error**, not rounding noise: one-sided, largest in luma and growing with brightness; black
  is correct. The worst errors from a 16-bit source are 3 / 2 / 2 code values (Y'/Cb/Cr) at 10-bit and 14 / 7 / 7
  at 12-bit. libswscale derives the scale factor as a ratio of full scale rather than as the bit-shifted
  narrow-range span.
- **8-bit sources are not affected**, which is why tests with 8-bit images do not show it. Neither
  `-sws_flags spline+accurate_rnd+full_chroma_int` nor any other flag changes it.
- **It works in both directions**: limited-range Y'CbCr white (940 at 10-bit) comes back as 65283 in 16-bit RGB
  with `scale`, where the specification calls for 65535 (`zscale` gives 65472, the difference being how a 10-bit
  value is expanded to 16 bits).
- **It applies whenever the output is limited range**, including when the range is left unset, because FFmpeg
  defaults to limited range for Y'CbCr output.
- **Full range depends on the version**: RGB to full-range Y'CbCr (`out_range=full`) was exact up to FFmpeg 7.1,
  but from 8.0 it is about 3 code values too bright at 10-bit; see
  [FFmpeg Version Changes](FFmpegChanges.html#libswscale-full-range-80).
- **`flags=unstable`** (libswscale's new conversion code, 8.1 and later) corrects it for 4:4:4 only; for 4:2:2 and
  4:2:0, which most delivery formats use, the output is identical to plain `scale`. It has to be set on the
  filter, as `scale=...:flags=unstable`; the global `-sws_flags unstable` has no effect. See
  [RGB to Y'CbCr Conversion](ColorPreservation.html#the-new-libswscale-code-flagsunstable).

One code value is below the threshold of visibility in a single pass, but the error is systematic, it accumulates
over round trips, and it grows with bit depth. You can see it in the
[Y'CbCr conversion comparison](tests/chip-chart-yuvconvert/compare.html#src=bars&a=splinecolormatrix&b=zscale&mode=wipe&zoom=0)
with the pixel probe on the 100% white patch. The measurements were taken against a float64 reference
implementation of the BT.709 conversion with
[`tests/rgb2ycbcr_accuracy.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/rgb2ycbcr_accuracy.py),
and cross-checked against uncompressed reference renders from Nuke. Every combination, by version and subsampling, is in
[RGB to Y'CbCr Accuracy by Version](FFmpegChangesRGBToYCbCr.html).

## What scale can do that zscale cannot

`zscale` is the better converter, but it is not a drop-in replacement for every use of `scale`. Keep `scale` (or
another filter) for:

- **Fitting and padding.** `scale` has `force_original_aspect_ratio` (fit inside or fill a size) and
  `force_divisible_by` (round to an even size, for encoders that need one), and is usually combined with `pad` for
  letterboxing. `zscale` only takes a width and height.
- **Pixel aspect ratio.** `scale` can reset the sample aspect ratio (`reset_sar`) when squeezing anamorphic
  material; with `zscale`, add `setsar` yourself.
- **Interlaced material.** `scale` can scale each field separately (`interl=1`).
- **Sizes that change mid-stream**, with `eval=frame`.
- **Any pixel format.** libswscale reads and writes packed, semi-planar and paletted formats; `zscale` only planar
  ones, and FFmpeg silently adds libswscale around it for the rest (see
  [Make sure zscale is doing the conversion](EncodeZscale.html#make-sure-zscale-is-doing-the-conversion)).
- **Availability and hardware.** libswscale is in every FFmpeg build, `zscale` needs `--enable-libzimg`, and there
  are hardware versions of `scale` (`scale_vt`, `scale_cuda`, `scale_vaapi` and others) that keep frames on the GPU.

None of these needs `scale` to do the color conversion: let `zscale` convert the color and `scale` (or `pad`,
`setsar`) handle the geometry, for example
`-vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1,zscale=matrix=709:range=limited:filter=lanczos,format=yuv420p10le,setparams=color_primaries=bt709:color_trc=iec61966-2-1"`.
Resizing on the RGB frames, before the conversion, is the order we use; on resizing itself, see
[Downscaling](Resizing.html).

## libswscale options

For when you use `scale`: an FFmpeg without `zscale`, or a resize where speed matters more than brightness (see
[Downscaling](Resizing.html)).

### Recommended flags

If you are resizing inside FFmpeg with `scale`, you probably want the lanczos filter rather than the default bicubic:

```console
-sws_flags lanczos+accurate_rnd
```

For converting from 4:4:4 Y'CbCr to RGB:

```console
-sws_flags spline+accurate_rnd
```

For converting from 4:2:2 or 4:2:0 to RGB (or to another Y'CbCr format):

```console
-sws_flags spline+full_chroma_int+accurate_rnd
```

This avoids visible artifacts, but in our measurements these flags did not make the Y'CbCr to RGB conversion more
accurate (for 4:2:2 ProRes they were worse than no flags; see [ProRes](EncodeProres.html#prores_ks)), and libswscale
assumes the chroma is centered whatever the flags. `zscale` is the better choice for this direction too; see
[Reading back to RGB](ChromaSiting.html#reading-back-to-rgb).

You can also enable the flags all the time, since they rarely do much harm:

```console
-sws_flags spline+full_chroma_int+accurate_rnd+full_chroma_inp
```

### SWS_Flags options

The main flag is the scaling algorithm (see [Choosing a filter](Resizing.html#choosing-a-filter)), but you can combine it with a
number of other flags, for example:

```console
-vf "scale=flags=lanczos+accurate_rnd+full_chroma_int:sws_dither=none:param0=5"
```

picks the lanczos filter with `param0=5`, which sets the filter size to 5 rather than the default 3, turns off the
dither, and enables `accurate_rnd` and `full_chroma_int`. This is an example of what you can do, not a
recommendation.

| Flag | Description |
| --- | --- |
| accurate_rnd | Allows more accurate rounding, avoiding some [MMX optimizations](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and) that might introduce rounding errors. This only occurs if the source is 4:2:0 or 4:2:2 and the destination is RGB, particularly when dithering, or when converting between Y'CbCr formats (for example 4:2:0 to 4:2:2). We have yet to find a case where it makes a difference with FFmpeg 5 and later; it may have mattered for earlier versions. |
| full_chroma_int | Full Chroma Interpolation, used for internal processing when rescaling: the chroma planes are upsampled to 4:4:4 with the scaling filter before the Y'CbCr-to-RGB conversion, rather than each chroma sample being repeated. It does nothing for RGB to Y'CbCr, but does for [Y'CbCr to RGB](https://github.com/FFmpeg/FFmpeg/blob/08e97dae205d10806a0360bfc62f654d629dda93/libswscale/output.c#L2847) and between Y'CbCr formats. It does not change where libswscale assumes the chroma is. |
| full_chroma_inp | Full Chroma Input: forces the scaler to use the full-resolution input for the chroma calculation. Without it, for RGB input converted to 4:2:2 or 4:2:0, libswscale averages each pair of pixels into one chroma value before filtering, which throws away the chroma siting: a line on an even column and one on the following odd column give identical chroma. **It matters for RGB input**, contrary to earlier versions of this page, and `full_chroma_int` does not do the same thing. Together with `out_chroma_loc=left` it is needed for co-sited chroma from `scale`; see [Chroma Siting](ChromaSiting.html). |
| print_info | Outputs additional debug information for the scaler. |
| bitexact | Disables SIMD operations that do not give exactly the same output as the C code; similar in effect to accurate_rnd. |
| sws_dither | Sets (or disables) the dithering algorithm. The default, "auto", uses the bayer algorithm unless `full_chroma_int` is set, in which case it uses "ed" (error diffusion), since bayer does not support `full_chroma_int`. "none" disables it. It is recommended to leave it on, to help with the RGB to Y'CbCr rounding, particularly at 8-bit (see [utils.c - initFilter line 1423](https://github.com/FFmpeg/FFmpeg/blob/a87a52ed0b561dc231e707ee94299561631085ee/libswscale/utils.c#L1423)). For `zscale`'s dither, see [Dithering](EncodeZscale.html#dithering). |

### Chroma subsampling with scale

For RGB to 4:2:2 or 4:2:0, the choice of libswscale filter makes little difference to the chroma: bicubic and
lanczos give nearly identical results, and `zscale` differs slightly, softer in places. Which looks better depends
on the material. The range and siting are not a close call, though: `scale` puts white at 943 instead of 940 at
10-bit and centres the chroma, so use `zscale`. In earlier tests, SMPTE HD bars were the one pattern that gave both
scalers trouble at 4:2:2; the `area` filter did best on them, but is not a good general choice.

When converting files that are already Y'CbCr (for example ProRes to DNxHR or H.264), note that libswscale centres
the chroma when it subsamples to 4:2:2 or 4:2:0, where professional 4:2:2 and H.264/HEVC 4:2:0 expect it co-sited,
and that converting 4:2:0 or 4:2:2 back to RGB it assumes the chroma is centered whatever the file says, on every
release up to 9.0; see [Chroma Siting](ChromaSiting.html).

## See also

- [https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and)
- [https://trac.ffmpeg.org/ticket/1582#comment:11](https://trac.ffmpeg.org/ticket/1582#comment:11)
- [https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor](https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor)
