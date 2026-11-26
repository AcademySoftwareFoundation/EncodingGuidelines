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
> in any release up to and including FFmpeg 9.0. The opt-in `scale=…:flags=unstable` (8.1 and later) fixes it for
> 4:4:4 output only; that new code is still under development, and should eventually be faster than both `zscale`
> and the current libswscale.

Converting full-range RGB white to limited-range Y'CbCr from a 10-bit or 16-bit source, `scale` puts white above the
value the specification calls for, at every output bit depth (8-bit sources are not affected; see
[FFmpeg Version Changes](FFmpegChanges.html#libswscale-white-level-for-high-bit-depth-input)):

| Output bit depth (16-bit source) | scale (libswscale) | zscale | BT.709 specification |
| :--- | :--- | :--- | :--- |
| 8-bit | 236 | 235 | 235 |
| 10-bit | 943 | 940 | 940 |
| 12-bit | 3774 | 3760 | 3760 |

The error is one-sided and largest in luma, growing with brightness; black is correct. The chroma gain is slightly
too high as well (up to 2 code values at 10-bit; see [RGB to Y'CbCr Conversion](ColorPreservation.html#zscale-filter)).
It is a gain error, not rounding noise: libswscale derives the scale factor as a ratio of full scale rather than as
the bit-shifted narrow-range span. The same bias appears in the other direction: limited-range Y'CbCr white (940 at
10-bit) comes back as 65283 in 16-bit RGB with `scale`, where the specification calls for 65535 (`zscale` gives
65472, the difference being how a 10-bit value is expanded to 16 bits). One code value is below the threshold of
visibility in a single pass, but the error is systematic, it accumulates over round trips, and it grows with bit
depth. You can see it in the [Y'CbCr conversion comparison](tests/chip-chart-yuvconvert/compare.html#src=bars&a=splinecolormatrix&b=zscale&mode=wipe&zoom=0)
with the pixel probe on the 100% white patch.

- **Affected**: any conversion that produces limited range. That includes `out_range=tv`, and it includes leaving
  the range unset, because FFmpeg defaults to limited range for Y'CbCr output.
- **Full range depends on the version**: RGB to full-range Y'CbCr (`out_range=full`) was exact up to FFmpeg 7.1, but
  from 8.0 it is about 3 code values too bright at 10-bit; see
  [FFmpeg Version Changes](FFmpegChanges.html#libswscale-full-range-80).
- **Not a workaround**: the `unstable` flag ("allow experimental new code") corrects the range scaling, but only for
  4:4:4 formats; for 4:2:2 and 4:2:0, which most delivery formats use, it makes no difference. It has to be set on the
  filter itself, as `scale=…:flags=unstable`; the global `-sws_flags unstable` has no effect on this.

These measurements were taken against a float64 reference implementation of the BT.709 conversion, and cross-checked
against uncompressed reference renders from Nuke. The behavior is the same on FFmpeg 8.1 and on 9.1, so the libswscale rewrite in FFmpeg 9 does not change it.

### Replacing scale with zscale

Where a command line uses `scale` for a matrix or range conversion:

```console
-vf "scale=out_color_matrix=bt709:out_range=tv"
```

the `zscale` equivalent is:

```console
-vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1"
```

`zscale` is not a drop-in replacement for every use of `scale`: it does not pad or fit to an aspect ratio; see
[Geometry](EncodeZscale.html#geometry).

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
