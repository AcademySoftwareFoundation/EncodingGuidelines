---
layout: default
title: FFmpeg Scaling Options
nav_order: 5.6
parent: Encoding Overview
---

# SWS_Flags

As mentioned previously, **we recommend doing any image resizing outside of ffmpeg**, especially if your sources are OpenEXR and you are going to do a colorspace conversion, prior to encoding, this will ensure that the filtering is done in linear space, which will produce less artifacts. However the scaling algorithms can still get called when remapping chroma from 4:4:4 to 4:2:2 (or 4:2:0). For more information on chroma subsampling, see [frame.io: chroma -subsampling guide](https://workflow.frame.io/guide/chroma-subsampling).

There are two scaling libraries that can be used in ffmpeg, libswscale, and zscale. This guide is mainly focusing on the additional options of the libswscale library.

{: .note }
> For converting RGB image sequences to Y'CbCr we now recommend `zscale`, see [zscale Conversion](EncodeZscale.html). libswscale gets the white level wrong for 10-bit and higher sources (below), and centres the chroma for 4:2:2 and 4:2:0 where professional formats expect it co-sited (see [Chroma Siting](ChromaSiting.html)). It remains useful for resizing, and where `zscale` is not available.

## Colour range accuracy: prefer zscale for range conversions

{: .warning }
> libswscale has a systematic bias when converting between full range and limited (studio) range from high bit depth sources. If your source is 10-bit or more and your command line sets `out_range=tv`, or converts RGB to Y'CbCr without specifying a range, the result will be slightly too bright. Use `zscale` for range and matrix conversions. This is not fixed in any release up to and including FFmpeg 9.0: the opt-in `scale=…:flags=unstable` (8.1 and later) fixes it for 4:4:4 output only. These new changes are still under development, so you may want to wait until a future FFmpeg release where the library is considered complete. It is worth pointing out that the new library when it comes should have some significant performance advantages over both zscale and the older library.

Converting full-range RGB white to limited-range Y'CbCr from a 10-bit or 16-bit source, `scale` puts white above the value the specification calls for, at every output bit depth (8-bit sources are not affected; see [FFmpeg Version Changes](FFmpegChanges.html#libswscale-white-level-for-high-bit-depth-input)):

| Bit depth | scale (libswscale) | zscale | BT.709 specification |
| :--- | :--- | :--- | :--- |
| 8-bit | 236 | 235 | 235 |
| 10-bit | 943 | 940 | 940 |
| 12-bit | 3774 | 3760 | 3760 |

The error is one-sided and affects luma only, growing with brightness — black is correct, and chroma is unaffected. It is a gain error rather than rounding noise: libswscale derives the scale factor as a ratio of full scale rather than as the bit-shifted narrow-range span, plus a rounding step. `zscale` matches the specification exactly.

The same bias appears in the other direction. Converting limited-range Y'CbCr white (Y=940 at 10-bit) back to 16-bit RGB gives 65283 with `scale`, where the specification calls for 65535. `zscale` gives 65472, the remaining difference being how the 10-bit value is expanded to 16 bits rather than an error in the conversion.

This is worth knowing rather than alarming. One code value at 8-bit is below the threshold of visibility in a single pass. It matters because it is *systematic* — it is simply wrong against the specification, it accumulates across round trips, and it grows in absolute terms with bit depth, which is the direction these guidelines recommend moving in.

### What is and is not affected

- **Affected**: any conversion that produces limited range. That includes `out_range=tv`, and it includes leaving the range unset, because FFmpeg defaults to limited range for Y'CbCr output.
- **Not affected**: `in_range=full:out_range=full`. With no narrow-range squeeze there is no bias, and `scale` returns the correct value.
- **Not a workaround**: the `unstable` flag ("allow experimental new code") corrects the range scaling, but only for 4:4:4 formats. For 4:2:2 and 4:2:0 — which is what most delivery formats use — it makes no difference. Note it has to be set on the filter itself, as `scale=…:flags=unstable`; passing it as the global `-sws_flags unstable` has no effect on this.

### Recommended replacement

Where a command line uses `scale` for a matrix or range conversion:

```console
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

the `zscale` equivalent is:

```console
-vf "zscale=matrixin=709:matrix=709:rangein=full:range=limited"
```

`zscale` requires an FFmpeg built with `--enable-libzimg`. The Docker builds in this repository enable it, and the Conan build now enables it by default.

Note that `zscale` is not a drop-in replacement for every use of `scale`. It does not do padding or aspect-ratio fitting, so command lines that combine scaling with `pad`, `force_original_aspect_ratio` or `setsar` need the colour conversion separated from the geometry operations rather than simply swapped.

These measurements were taken against a float64 reference implementation of the BT.709 conversion, and cross-checked against uncompressed reference renders from Nuke. The behaviour is identical on FFmpeg 8.1 and on a 9.1 development build, so the libswscale rewrite in FFmpeg 9 does not change it.

## libswscale Scaling Summary

For most cases, when converting from RGB to Y’CbCr the default options are fine, but if you are downsampling the image inside ffmpeg, you probably want to use the lanczos filter rather than the default bicubic

```console
-sws_flags lanczos+accurate_rnd
```

For converting from 4:4:4 to RGB we recommend using:

```console
-sws_flags spline+accurate_rnd
```

For converting from 4:2:2 or 4:2:0 to RGB (or another Y’CbCr) we recommend using:

```console
-sws_flags spline+full_chroma_int+accurate_rnd
```

When converting to 4:2:2 or 4:2:0. This appears to convert with no artifacts, all the other scaling options have artifacts of some form.

Note, you could also be safe in simply enabling flags all the time, since they rarely will do much harm, an example of this is:

```console
-sws_flags spline+full_chroma_int+accurate_rnd+full_chroma_inp
```

Especially if you already have done any resolution scaling outside of ffmpeg, are not harmful, and for Y’CbCr conversion to RGB would be beneficial.

### SWS_Flags options

The main flag that is defined is the scaling algorithm, (see later), but you can combine it with another of other flags.

E.g.

```console
-sws_flags=lanczos+accurate_rnd+full_chroma_int:sws_dither=none:param0=5
```

Picks the lanczos filter, with a param0=5 which sets the filter size to 5 rather than default 3, turning off the dither, and enabling the accurate_rnd and full_chroma_int flags. NOTE, this is just an example of what you can do, not what we recommend doing.

Flags that can be used with the filters, include:

| accurate_rnd | allows more accurate rounding. This avoids using some [MMX optimizations](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and)  that might introduce rounding errors. In practice its unlikely to kick in, but it doesn't hurt. This only occurs if the source is 4:2:0 or 4:2:2, and the destination is RGB, articularly if you are dithering the result. The other case is if you are converting from one Y’CbCr format to another (e.g. 4:2:0 to 4:2:2). NOTE, we have yet to find a case where this currently makes a difference, it's possible it was important for earlier versions of ffmpeg, but with more recent versions (ffmpeg >= 5.x) it seems to have little impact. |
| full_chroma_int | Full Chroma Interpolation - is used for internal processing when rescaling. It enables the use of full Y’CbCr 4:4:4 for internal processing. This means the chroma plane is upsampled using actual scaling conversions before the Y’CbCr-to-RGB conversion is initiated. This can potentially deliver higher visual quality at a relatively small speed penalty. This does nothing for the RGB to Y’CbCr conversion, but does for the [YCbCr to RGB conversion](https://github.com/FFmpeg/FFmpeg/blob/08e97dae205d10806a0360bfc62f654d629dda93/libswscale/output.c#L2847), or between Y’CbCr formats. |
| full_chroma_inp | Full Chroma Input - This forces the scaler to use the full resolution input for the chroma calculation. Without it, for RGB input converted to 4:2:2 or 4:2:0, libswscale averages each pair of pixels into one chroma value before filtering, which throws away the chroma siting: a line on an even column and one on the following odd column give identical chroma. **It matters for RGB input**, contrary to earlier versions of this page, and `full_chroma_int` does not do the same thing. Together with `out_chroma_loc=left` it is needed for co-sited chroma from `scale`; see [Chroma Siting](ChromaSiting.html). |
| print_info | Outputs additional debug info for the scaler. |
| Bitexact | disabled SIMD operations that don’t generate exactly the same output as C, this ends up being quite similar to accurate_rnd. |
| sws_dither | Allows you to set (or disable) the dithering algorithm. By default it is set to “auto”, which will use the bayer algorithm unless the “full_chroma_int” flag is enabled, in which case it will use the “ed” (error diffusion) algorithm. This is due to the bayer algorithm not supporting the full_chroma_int flag. You can also disable it with “none”. It is recommended to leave it enabled, to help with the RGB to Y’CbCr rounding errors, particularly in 8-bit. (see [utils.c - initFilter line 1423](https://github.com/FFmpeg/FFmpeg/blob/a87a52ed0b561dc231e707ee94299561631085ee/libswscale/utils.c#L1423) |

## Deeper dive

Below we dig into when the different flags should be used for different occasions.

### Converting from RGB to Y’CbCr 422

In the testing (See link), for most cases, there is minimal difference between the swscale algorithm options for RGB to 422 conversion. Any of the bicubic, lanczos scalers will produce an identical result.

E.g.

```console
-sws_flags accurate_rnd+lanczos+print_info -pix_fmt yuv422p10le -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

Zscale does produce a slightly different result, using the flags:

```console
-vf "zscale=m=709:min=709:rangein=full:range=limited:filter=lanczos"
```

On chroma resampling quality the two are close, and which looks better depends on the material. On the range conversion itself they are not close: `scale` places white at 943 rather than 940 at 10-bit, where `zscale` is exact. See [Colour range accuracy](#colour-range-accuracy-prefer-zscale-for-range-conversions) above. For that reason we now recommend `zscale` here.

The one test pattern that creates errors for both of the scalers is the smpteHDbars, zscale is the worse of the two, but unless you use the “area” filter, the bars results are not great. If you have a fairly graphic look, and are converting to 422, you may want to try area, but do be aware that for other cases it may not create a great result.

### Converting from RGB to Y’CbCr 420

In the testing (See link), Unlike for the conversion to 422, since you are now sampling over a slightly bigger area, there is a bigger difference between the different filtering algorithms. We are recommending:

E.g.

```console
-sws_flags accurate_rnd+lanczos+print_info -pix_fmt yuv420p10le -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

Zscale does produce a slightly improved if occasionally softer result, using the flags:

```console
-vf "zscale=m=709:min=709:rangein=full:range=limited:filter=lanczos"
```

As with 4:2:2, the chroma resampling is a close call and the range conversion is not — `zscale` is exact where `scale` is systematically bright. We recommend `zscale` for this conversion.

### Exporting from Y’CbCr

If you are converting files from Y’CbCr, e.g. from Prores to MXF (or h264), particularly from 4:2:0 or 4:2:2, many of the above options are theoretically more important.

Additionally you should be aware of chroma siting ([chroma_sample_location](http://trac.ffmpeg.org/wiki/Scaling#Chromasamplelocation)). When converting to 4:2:2 or 4:2:0, libswscale centres the chroma by default, where professional 4:2:2 and H.264/HEVC 4:2:0 expect it co-sited; see [Chroma Siting](ChromaSiting.html) for measurements and fixes. What FFmpeg assumes when converting 4:2:0 or 4:2:2 back to RGB has not been tested yet.

## Scaling algorithms

Picking the scaling filter does depend on the type of imagery you are applying it to. If you are processing live-action then the consensus is typically the lanczos filter. Animation or motion graphics may suffer due to the ringing effects of lanczos, but you really should compare the results.

* [Comparison gallery of image scaling algorithms - Wikipedia](https://en.wikipedia.org/wiki/Comparison_gallery_of_image_scaling_algorithms)
* [Cambridge in Color - resizing for web and email](https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm)
* [ImageMagick Examples -- Resampling Filters](https://www.imagemagick.org/Usage/filter)

See also:

* [https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and)
* [https://trac.ffmpeg.org/ticket/1582#comment:11](https://trac.ffmpeg.org/ticket/1582#comment:11)
* [https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor](https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor)
