---
layout: default
nav_order: 4.8
title: MJPEG Encoding
parent: Codec Comparisons
---

# MJPEG - Motion JPEG

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

[Motion JPEG](https://en.wikipedia.org/wiki/Motion_JPEG) has historically been quite common in the VFX industry, and is part of the default Quicktime codecs, so is well supported on players, although not typically supported in web browsers.

While it does compress quickly, and maintains its quality fairly well, we would recommend other codecs at higher bit-depths such as vp9, h264 or h265 (or even Prores or DNxHD), which will also compress better than mjpeg.

## MJPEG

mjpeg has a limited range of pixel formats:
yuvj420p yuvj422p yuvj444p yuv420p yuv422p yuv444p

Example encoding:

<!---
name: test_mjpeg
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     matrix: bt470bg
     range: pc
     # MJPEG is full range BT.601 by default.
     # Limits (10-bit code values): just above the result of this command, FFmpeg 6.0 and 9.0, 2026-10-26.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-2.5, 2.5]
     - assert: less
       value: p99_error_10bit
       less: 6
     - assert: less
       value: mean_error_10bit
       less: 2.5
     - assert: less
       value: max_error_10bit
       less: 16
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: iec61966-2-1
     - assert: stringmatch
       value: colr
       string: nclc 1/13/5
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 \
   -vf "setparams=color_primaries=bt709:color_trc=iec61966-2-1" -colorspace bt470bg \
   -c:v mjpeg -qscale:v 2 outputfile.mov
```

`setparams` sets the primaries and transfer function, and `-colorspace bt470bg` states the BT.601 matrix that MJPEG
uses anyway; it does not change the pixels. Both are needed for the MOV to get a `colr` atom: without `-colorspace`
the muxer leaves out the primaries and transfer as well, and without `setparams` the file has neither (tested on
6.1.6, 7.1.5 and 9.0.2). The JPEG data itself always says full range BT.601.

Leave `-pix_fmt` off, as above, or use a `yuvj` format such as `-pix_fmt yuvj444p`. Both give correct full range
files on 6.1.6, 7.0, 7.1.5, 8.1, 9.0.2 and a 9.1 development build. On 7.0 and earlier, a plain `-pix_fmt yuv444p` does not encode, and adding `-color_range pc` to make it
encode writes limited range pixels into a file tagged full range. From 7.1 it is converted correctly.

## Recommended Flags

| Flag | Description |
| --- | --- |
| **-qscale:v 2** | This is the compression factor, which goes from 2 to 31 where 2 is the best quality. See the [alternative approach](#alternative-approach) for higher quality. |

### qscale:v Comparison

Below is a comparison of different Qscale rates

| ![](enctests/reference-results/mjpeg-qscale-tests-encode_time.png)  This is showing qscale:v values against encoding time. |
| ![](enctests/reference-results/mjpeg-qscale-tests-filesize.png) This is showing qscale:v values against file size. |
| ![](enctests/reference-results/mjpeg-qscale-tests-vmaf_harmonic_mean.png) This is showing qscale:v values against VMAF harmonic mean |
| ![](enctests/reference-results/mjpeg-qscale-tests-psnr_y_harmonic_mean.png) This is showing qscale:v values against PSNR-Y harmonic mean |

## Alternative approach

You can generate the individual jpeg files using another tool, and then use ffmpeg to stitch them together. For example, to convert a series of png frames to jpeg, you can use oiiotool:

```console
oiiotool -v --parallel-frames -i PNGFILES.%05d.png --compression jpeg:95 -o JPEGFILES.%05d.jpg
```

and then stitch them together with:

```console
ffmpeg -f image2 -r 24 -i JPEGFILES.%05d.jpg -vcodec copy outputfile.mov
```

This gives you more fine grain control over the quality setting, although it gives you less control over the jpeg compression, since it will always be YUV420, where you do get more control with ffmpeg.
It's actually hard to get an exact mapping between the ffmpeg -qscale setting and the jpeg quality. The highest ffmpeg setting is 2, and that roughly maps to a jpeg quality setting of 86%.
So if you require higher quality than 86% then use this approach. Settings below 95% do produce artifacts, so this is the recommended approach if you *have* to do this, a 10-bit encoder would be better though.

Below shows a comparison of jpeg compression to filesize for a HD sized image sequence of 200 frames.
![](enctests/reference-results/mjpeg-compression-tests-filesize.png)
