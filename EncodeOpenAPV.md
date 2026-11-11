---
layout: default
nav_order: 4.9
title: OpenAPV Encoding
parent: Codec Comparisons
---
# OpenAPV

## Overview

[OpenAPV](https://github.com/AcademySoftwareFoundation/openapv) provides professional grade visually lossless video suitable as a raw video format, designed and developed by Samsung. It is free and open source and this implementation was contributed by Samsung to the ASWF.

The codec specification allows:

* Perceptually lossless video quality.  
* Support for high bit rate and resolution content (e.g. 8k)  
* Support for multiple decoding and re-encoding without severe visual quality degradation.  
* Support for up to 16-bit encoding.  
* Frame tiling for immersive content and for enabling parallel encoding and decoding.  
* Support multi-view video and auxiliary video like depth, alpha and preview.

There are three implementations:

* OpenAPV library - [https://github.com/AcademySoftwareFoundation/OpenAPV](https://github.com/AcademySoftwareFoundation/OpenAPV) - which can encode a YCbCr stream to the apv format.  
* Native ffmpeg - FFmpeg has implemented their own decoder as part of the core ffmpeg app, they also have their own encoder using the OpenAPV library.  
* Android Open Source Project (AOSP) 16 - Android has added support of APV in v16. [Android 16](https://developer.android.com/about/versions/16/features#apv).

### Related specification

* APV Codec (bitstream): [https://datatracker.ietf.org/doc/draft-lim-apv/](https://datatracker.ietf.org/doc/draft-lim-apv/)  
* APV ISO based media file format: [APV-ISOBMFF](https://github.com/AcademySoftwareFoundation/openapv/blob/main/readme/apv_isobmff.md)  
* APV RTP payload format: [https://datatracker.ietf.org/doc/draft-lim-rtp-apv/](https://datatracker.ietf.org/doc/draft-lim-rtp-apv/)

## OpenAPV library

This [implementation](https://github.com/AcademySoftwareFoundation/OpenAPV) of the APV codec supports the following features:

* 422 and 444 10-bit and 12 bit encoding/decoding.  
* Low complexity by optimization for ARM NEON and x86(64bit) SSE/AVX CPU  
* Supports tile-based multi-threading  
* Supports Various metadata including HDR10/10+ and user-defined format  
* Constant QP (CQP), average bitrate (ABR), and constant rate factor (CRF) are supported  
* Support for high bit rate and resolution content (e.g. 8k)  
* Support for multiple decoding and re-encoding without severe visual quality degradation

Possibly the easiest way to use it is to make a y4m file with ffmpeg and then use that as input to the oapv_app_enc  
E.g.

```console
ffmpeg -i INPUTFILE -pix_fmt yuv422p12le -strict -1 Y4MFILE.y4m  
oapv_app_enc -i Y4MFILE.y4m -o OUTPUTFILE.apv -qp 20
```

Note, the y4m format only works with 422, but it does give you access to some of the other options. This is not really recommended, since you don't really have control over the colorspace, nor wrapping the result in a mp4 or mov file, which ffmpeg can do below.

## FFmpeg

OpenAPV is included in FFmpeg from version 8.0.

There is a decoder which is impressively fast, and does support 422, 444 and 4444 at 10 and 12 bits.
The encoder uses the OpenAPV library, and currently supports 422, 444 and 4444 at 10 and 12 bits.

## Example Encoding

```console
ffmpeg -start_number 2500 -i "INPUT.%05d.dpx" -frames:v 200 -c:v liboapv -qp 20 \
     -preset fast -pix_fmt yuv444p12le -oapv-params "profile=444-12" \
     -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
     -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
     -y "OUTPUT.mov"
```

Flags include:

| Flag | Description |
| :---- | :---- |
| -qp 20 | Quantization parameter, 0-63 (default 32), lower is higher quality. For visually lossless you probably want 20 or lower at 10-bit, or about 30 or lower at 12-bit; see [QP](#qp). |
| -preset fast | Preset fast curiously appears to generate faster results at a better quality than medium, for a 3-5% larger file. Use medium if file size matters more; see [Presets](#presets). |
| -b:v 250M | The bitrate can be set instead of `-qp`; see [Bitrate](#bitrate). |
| -oapv-params "profile=444-12" | Tells the encoder which APV profile to write. Only needed on FFmpeg 8.0 and 8.1; see below. |

On FFmpeg 8.0 and 8.1, the encoder only works out the APV profile for `yuv422p10le`. For any other pixel format you
have to give the matching profile with `-oapv-params`; without it the encode fails with `oapve_encode() failed` and
leaves an empty file. From FFmpeg 9.0 the profile is chosen from the pixel format (commit `8885116f4d`, "derive and
validate APV profile from pixel format"), so `-oapv-params` is not needed, and giving it does no harm: on 9.0.2 the
files were identical with and without it. Tested on 8.0.1, 8.1, 9.0.2 and a 9.1 development build.

| Pixel format | `-oapv-params` (8.0 and 8.1 only) | APV profile |
| :---- | :---- | :---- |
| yuv422p10le | none required | 422-10 |
| yuv422p12le | profile=422-12 | 422-12 |
| yuv444p10le | profile=444-10 | 444-10 |
| yuv444p12le | profile=444-12 | 444-12 |
| yuva444p10le | profile=4444-10 | 4444-10, with alpha |
| yuva444p12le | profile=4444-12 | 4444-12, with alpha |

For `yuv422p10le`, on any version, the encode can be as simple as:

```console
ffmpeg -start_number 2500 -i "INPUT.%05d.dpx" -frames:v 200 -c:v liboapv -qp 20 \
     -preset fast -pix_fmt yuv422p10le \
     -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
     -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 -y "OUTPUT.mov"
```

<!---
HIDING Familys for now, they dont work.

## APV Familys

Instead of the bitrate and QP parameter, you can optionally specify a family, which can be one of:
| *Family Name* | *Color Sampling* | *Notes* | * FFMPEG Parameter *|
| 422-LQ |  YCbCr422 | Editing-friendly low-data-rate workflows | -oapv-params: profile=422-10:family=422-HQ |
| 422-SQ |  YCbCr422 | Standard quality mezzanine || -oapv-params: profile=422-10:family=422-HQ |
| 422-HQ | YCbCr422 | High quality mezzanine || -oapv-params: profile=422-10:family=422-HQ |
| 444-HQ | YCbCr444 | high quality - Finishing || -oapv-params: profile=444-12:family=444-HQ |

This will then pick an appropriate bitrate based on your resolution and frame-rate, so saving the need to need to do any significant testing.
You will also need to match the pix_fmt setting with the oapv-params.

```
ffmpeg -start_number 2500 -i "INPUT.%05d.dpx" -frames:v 200 -c:v liboapv -qp 20 \
     -preset fast -pix_fmt yuv444p12le -oapv-params "profile=444-12" -sws_flags spline+accurate_rnd+full_chroma_int \
     -vf "scale=out_color_matrix=bt709:out_range=tv" \
     -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 -y "OUTPUT.mov"
```
-->

## Presets

There are presets of:

* Fastest  
* Fast  
* Medium  
* Slow  
* Placebo

Presets affect the file-size and quality results surprisingly little, other than varying how long the encode takes.

Fastest and Fast are fairly similar: compared with medium they are twice as fast and slightly higher quality, at the expense of a 3-5% increase in disk space.

Medium is the smallest file size, but also has the worst PSNR values by small amounts.

We recommend fast if encoding speed is an issue, or medium if file-size is an issue.  

Below is a breakdown comparison:

| ![](enctests/reference-results/apv_presets-vmaf_harmonic_mean.png) | ![](enctests/reference-results/apv_presets-encode_time.png) |
|![](enctests/reference-results/apv_presets-filesize.png) |

## QP

There are two main adjustments, bitrate or QP.

QP (Quantization Parameter) is 0-63 in FFmpeg's `-qp`, the default being 32, at any bit depth. In APV the maximum
grows by 6 for each bit above 10 (`MAX_QUANT` in the OpenAPV source), so 12-bit can go to 75, and the same QP gives
finer quantisation at 12-bit: 12-bit QP 30 is roughly 10-bit QP 18, which is why the recommended values below
differ. To use 64-75 at 12-bit you would have to pass `-oapv-params qp=...`, and it needs OpenAPV 1.1.1.0 or later:
earlier versions limit the encoder to 63 at every bit depth, and with the libraries in our FFmpeg 9.0.2 and 9.1
development builds 12-bit QP 70 failed with `oapve_encode() failed`. A `qp=` above 75 is ignored without an error,
and FFmpeg's default of 32 is used. The effect on file-size and quality are pretty consistent depending on whether the results are 10-bit or 12-bit.

For 10-bit encodes below are graphs for encoding at 422p10 for visually lossless values we recommend qp=20, there are small increases in PSNR if you go down to about 15, and below that the improvements are fairly minimal. These are similar for 444p10.

| ![](enctests/reference-results/apv_qp-encode_time.png) |  ![](enctests/reference-results/apv_qp-filesize.png) |
| ![](enctests/reference-results/apv_qp-vmaf_harmonic_mean.png) |  ![](enctests/reference-results/apv_qp-psnr_y_harmonic_mean.png) |

For 12-bit encodes below are graphs for encoding at 422p12 for visually lossless values we recommend qp=30, but there will be small improvements in the PSNR if you lower it to qp=25; below that the improvements are fairly minimal. It's similar for 444p12 encodes.

| ![](enctests/reference-results/apv_qp12-encode_time.png) |  ![](enctests/reference-results/apv_qp12-filesize.png) |
| ![](enctests/reference-results/apv_qp12-vmaf_harmonic_mean.png) |  ![](enctests/reference-results/apv_qp12-psnr_y_harmonic_mean.png) |

## Bitrate

You can explicitly set the bitrate, below are wedges for 422p10.

| ![](enctests/reference-results/apv_bitrate-encode_time.png) |  ![](enctests/reference-results/apv_bitrate-filesize.png) |
| ![](enctests/reference-results/apv_bitrate-vmaf_harmonic_mean.png) |  ![](enctests/reference-results/apv_bitrate-psnr_y_harmonic_mean.png) |

But in practice it does cap out at a quality above 300Mbps.

Note, if you look at the [YUV Diff](https://encode.taurich.org/wedge_results/ffmpeg_version_git-2025-07-22-1ce20f55cc/darwin-arm64/apv_bitrate_tests-encode/apv_bitrate-compare.html?media=chimera_wind_srgb.%2506d&left=chimera_wind_srgb-test_oapv_bitrate-medium_b050&right=chimera_wind_srgb-test_oapv_bitrate-medium_b250), particularly for 422p10 Comparing a bit rate of 250Mb/s vs, qp16 (which approximately have the same filesize) show using the qp value generates better results than using the bitrate flag.

| ![][image8] | ![][image9] |
| Bitrate: 250Mb/s |   qp: 16 |  
| File size: 241,363,608 |  File size: 214,007,491 |

This is a known issue that hopefully will be addressed in a future update. It's worth stressing that this particular view does exaggerate extremely small changes, so if using bitrate is desirable, test to see if the results are acceptable.

## Codec Comparison Benchmarking

These benchmarks were for HD versions of the netflix chimera media (200 frame clips). This is running on a M2 Macbook Pro, so we can compare directly with the Videotoolbox apple ProRes encode (NOTE, which has hardware assist). We have picked a couple of QP values, and mostly consider a QP value of 15 to be the most desirable rate, we were picking codec settings (where available) to approximately match the prores PSNR value, so we can compare the different file sizes and encode time.

| ![](enctests/reference-results/intra-test422-encode_time.png)  This is showing different intraframe codecs against encoding time. | ![](enctests/reference-results/intra-test422-filesize.png) This is showing different intraframe codecs against file size. |
| ![](enctests/reference-results/intra-test422-vmaf_harmonic_mean.png) This is showing different intraframe codecs against VMAF harmonic mean | ![](enctests/reference-results/intra-test422-psnr_y_harmonic_mean.png) This is showing different intraframe codecs against psnr y harmonic mean |

The APV encoder is comparable in this case to ffmpeg with video-toolbox on an M2 Max (with encoder hardware), it is unknown how optimal the ffmpeg wrapper is. But there are definitely improvements over DNxHD. HTJ2K is a little unfair in this context since it is a full RGB image, but clearly is slower at encoding. Also worth noting prores_ks is quite a bit slower.

For 444 testing:  
Note, dnxhr and prores_ks are both encoding only to 10-bit, since they do not support 12-bit in ffmpeg.

| ![](enctests/reference-results/intra-test444-encode_time.png)  This is showing different intraframe codecs against encoding time. | ![](enctests/reference-results/intra-test444-filesize.png) This is showing different intraframe codecs against file size. |
| ![](enctests/reference-results/intra-test444-vmaf_harmonic_mean.png) This is showing different intraframe codecs against VMAF harmonic mean | ![](enctests/reference-results/intra-test444-psnr_y_harmonic_mean.png) This is showing different intraframe codecs against psnr y harmonic mean |

## Playback

For playback you need to at least be on ffmpeg 8.0. OpenRV does have a [Pull-request](https://github.com/AcademySoftwareFoundation/OpenRV/pull/843) to add 8.0 as an option to OpenRV. The changes are not specific to OpenAPV, but are related to updates to ffmpeg 8.0.

## Playback performance

This measures decode speed with `ffmpeg -hide_banner -benchmark -stream_loop 4 -i <FILENAME> -f null -`, as a way to compare one codec with another without the display getting in the way. The values are frames per second; higher is faster. Some clips were not measured for every codec, so the averages of the `dnxhr` and `oapv_422p10le` columns are not directly comparable with the others.

| Clip | dnxhr | dnxhr_hqx | oapv_422p10le | oapv_422p10le_qp15 | oapv_422p10le_qp20 | oapv_422p10le_qp25 | prores_ks_hq | prores_videotoolbox_yuv422p10le_hq |
| :---- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| chimera_cars_srgb | 315.6 | 305 | 454.6 | 298.2 | 341.9 | 476.2 | 280.4 | 281.8 |
| chimera_coaster_srgb | 342.2 | 314.7 |  | 299.4 | 351.9 | 465.8 | 306 | 301.5 |
| chimera_fountains | 327.7 | 329.3 |  | 220.9 | 249.2 | 331.5 | 297.8 | 276.3 |
| chimera_wind_srgb |  | 360.1 |  | 257.2 | 302.6 | 409.3 | 328.4 | 313.2 |
| **Average** | **328.5** | **327.3** | **454.6** | **268.9** | **311.4** | **420.7** | **303.2** | **293.2** |

[image8]: enctests/reference-results/apv_bitrate-b250-yuvdiff.png

[image9]: enctests/reference-results/apv_qp16-yuvdiff.png
