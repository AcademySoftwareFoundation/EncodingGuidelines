---
layout: default
title: Ffmpeg Scaling Options
nav_order: 5.6
parent: Encoding Overview
---

# SWS_Flags

As mentioned previously, **we recommend doing any image resizing outside of ffmpeg**, especially if your sources are OpenEXR and you are going to do a colorspace conversion, prior to encoding, this will ensure that the filtering is done in linear space, which will produce less artifacts. However the scaling algorithms can still get called when remapping chroma from 4:4:4 to 4:2:2 (or 4:2:0). For more information on chroma subsampling, see [frame.io: chroma -subsampling guide]([https://workflow.frame.io/guide/chroma-subsampling](https://workflow.frame.io/guide/chroma-subsampling)). 

There are two scaling libraries that can be used in ffmpeg, libswscale, and zscale. This guide is mainly focusing on the additional options of the libswscale library.


## libswscale Scaling Summary

For most cases, when converting from RGB to Y’CbCr the default options are fine, but if you are downsampling the image inside ffmpeg, you probably want to use the lanczos filter rather than the default bicubic


```
-sws_flags lanczos+accurate_rnd
```


For converting from 4:4:4 to RGB we recommend using:


```
-sws_flags spline+accurate_rnd
```


For converting from 4:2:2 or 4:2:0 to RGB (or another Y’CbCr) we recommend using:


```
-sws_flags spline+full_chroma_int+accurate_rnd
```


When converting to 4:2:2 or 4:2:0. This appears to convert with no artifacts, all the other scaling options have artifacts of some form.

Note, you could also be safe in simply enabling flags all the time, since they rarely will do much harm, an example of this is:


```
-sws_flags spline+full_chroma_int+accurate_rnd+full_chroma_inp
```


Especially if you already have done any resolution scaling outside of ffmpeg, are not harmful, and for Y’CbCr conversion to RGB would be beneficial.


### SWS_Flags options

The main flag that is defined is the scaling algorithm, (see later), but you can combine it with another of other flags.

E.g.


```
-sws_flags=lanczos+accurate_rnd+full_chroma_int:sws_dither=none:param0=5
```


Picks the lanczos filter, with a param0=5 which sets the filter size to 5 rather than default 3, turning off the dither, and enabling the accurate_rnd and full_chroma_int flags. NOTE, this is just an example of what you can do, not what we recommend doing.

Flags that can be used with the filters, include:


| accurate_rnd | allows more accurate rounding. This avoids using some [MMX optimizations](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and)  that might introduce rounding errors. In practice its unlikely to kick in, but it doesn't hurt. This only occurs if the source is 4:2:0 or 4:2:2, and the destination is RGB, articularly if you are dithering the result. The other case is if you are converting from one Y’CbCr format to another (e.g. 4:2:0 to 4:2:2). NOTE, we have yet to find a case where this currently makes a difference, it's possible it was important for earlier versions of ffmpeg, but with more recent versions (ffmpeg >= 5.x) it seems to have little impact. |
| full_chroma_int | Full Chroma Interpolation - is used for internal processing when rescaling. It enables the use of full Y’CbCr 4:4:4 for internal processing. This means the chroma plane is upsampled using actual scaling conversions before the Y’CbCr-to-RGB conversion is initiated. This can potentially deliver higher visual quality at a relatively small speed penalty. This does nothing for the RGB to Y’CbCr conversion, but does for the [YCrCb to RGB conversion](https://github.com/FFmpeg/FFmpeg/blob/08e97dae205d10806a0360bfc62f654d629dda93/libswscale/output.c#L2847), or between Y’CbCr formats. |
| full_chroma_inp | Full Chroma Input - This forces the scaler to assume the input is full chroma even for cases where the scaler thinks it's useless. This does nothing if the source format is an RGB, so really only applies if the source format is a [4:2:2 or 4:2:0](https://github.com/FFmpeg/FFmpeg/blob/08e97dae205d10806a0360bfc62f654d629dda93/libswscale/utils.c#L1493) format. If this is not defined, it will drop every other pixel for chroma calculation. It seems like full_chroma_int really does everything this does. |
| print_info | Outputs additional debug info for the scaler. |
| Bitexact | disabled SIMD operations that don’t generate exactly the same output as C, this ends up being quite similar to accurate_rnd. |
| sws_dither | Allows you to set (or disable) the dithering algorithm. By default it is set to “auto”, which will use the bayer algorithm unless the “full_chroma_int” flag is enabled, in which case it will use the “ed” (error diffusion) algorithm. This is due to the bayer algorithm not supporting the full_chroma_int flag. You can also disable it with “none”. It is recommended to leave it enabled, to help with the RGB to Y’CbCr rounding errors, particularly in 8-bit. (see [utils.c - initFilter line 1423](https://github.com/FFmpeg/FFmpeg/blob/a87a52ed0b561dc231e707ee94299561631085ee/libswscale/utils.c#L1423) |


## Deeper dive

Below we dig into when the different flags should be used for different occasions.


### Converting from RGB to Y’CbCr 422

In the testing (See link), for most cases, there is minimal difference between the swscale algorithm options for RGB to 422 conversion. Any of the bicubic, lanczos scalers will produce an identical result.

E.g.

```
-sws_flags accurate_rnd+lanczos+print_info -pix_fmt yuv422p10le -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

Zscale does produce a slightly different result, using the flags:

```
-vf "zscale=m=709:min=709:rangein=full:range=limited:filter=lanczos"
```

Its frankly hard to say between zscale and swscale which is better.

The one test pattern that creates errors for both of the scalers is the smpteHDbars, zscale is the worse of the two, but unless you use the “area” filter, the bars results are not great. If you have a fairly graphic look, and are converting to 422, you may want to try area, but do be aware that for other cases it may not create a great result.


### Converting from RGB to Y’CbCr 420

In the testing (See link), Unlike for the conversion to 422, since you are now sampling over a slightly bigger area, there is a bigger difference between the different filtering algorithms. We are recommending:

E.g.

```
-sws_flags accurate_rnd+lanczos+print_info -pix_fmt yuv420p10le -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```

Zscale does produce a slightly improved if occasionally softer result, using the flags:

```
-vf "zscale=m=709:min=709:rangein=full:range=limited:filter=lanczos"
```

Its frankly hard to say between zscale and swscale which is better.


### Exporting from Y’CbCr

If you are converting files from Y’CbCr, e.g. from Prores to MXF (or h264), particularly from 4:2:0 or 4:2:2, many of the above options are theoretically more important.

Additionally you should be aware of is the [chroma_sample_location](http://trac.ffmpeg.org/wiki/Scaling#Chromasamplelocation).Which can also be important when exporting 4:2:0 or 4:2:2 to RGB. &lt;TODO TEST>


## Scaling algorithms

Picking the scaling filter does depend on the type of imagery you are applying it to. If you are processing live-action then the consensus is typically the lanczos filter. Animation or motion graphics may suffer due to the ringing effects of lanczos, but you really should compare the results. 

 * [Comparison gallery of image scaling algorithms - Wikipedia](https://en.wikipedia.org/wiki/Comparison_gallery_of_image_scaling_algorithms)
 * [Cambridge in Color - resizing for web and email](https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm)
 * [ImageMagick Examples -- Resampling Filters](https://www.imagemagick.org/Usage/filter)

See also:

 * [https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and](https://stackoverflow.com/questions/70893502/why-does-ffmpeg-output-slightly-different-rgb-values-when-converting-to-gbrp-and)
 * [https://trac.ffmpeg.org/ticket/1582#comment:11](https://trac.ffmpeg.org/ticket/1582#comment:11)
 * [https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor](https://stackoverflow.com/questions/64729698/why-is-ffmpegs-conversion-to-yuv420-so-poor)


