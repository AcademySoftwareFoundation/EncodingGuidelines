---
layout: default
nav_order: 4.1
title: H264 Encoding
parent: Codec Comparisons
---

# H264 <a name="h264"></a>

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

This is the workhorse encoder for web review, it's well supported by ffmpeg, and there is a lot of support for both encoding and decoding in hardware.

There are several h264 encoders available:

* [x264](#x264) - the videolan h264 open source library.
* [h264_nvenc](#nvidia-nvenc) - the nvidia hardware encoder.
* [h264_videotoolbox](#macos-videotoolbox) - MacOS only apple h264 encoder.

## x264

x264 is a library developed by the [videolan association](https://www.videolan.org/developers/x264.html). It has a GPL license.

Supported pixel formats: yuv420p yuvj420p yuv422p yuvj422p yuv444p yuvj444p nv12 nv16 nv21 yuv420p10le yuv422p10le yuv444p10le nv20le gray gray10le

Note, for web browsers use 4:2:0. 4:2:2 is not reliably supported (Firefox did not play 4:2:2 H.264 in our tests); see [H264 Bitdepth](#h264-bitdepth) for 8-bit against 10-bit.

Key flags (see [https://trac.ffmpeg.org/wiki/Encode/H.264](https://trac.ffmpeg.org/wiki/Encode/H.264) )

Example encoding:

<!---
name: test_h264
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
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
       less: 0.5
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
ffmpeg -r 24 -start_number 100 -i inputfile.%04d.png -frames:v 200 -c:v libx264 \
        -pix_fmt yuv420p10le -crf 18 -preset slow \
        -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
        -movflags +faststart -y outputfile.mp4
```

| Flag | Description |
| --- | --- |
| **-crf 18** | This is the constant rate factor, controlling the default quality (see: [https://slhck.info/video/2017/02/24/crf-guide.html](https://slhck.info/video/2017/02/24/crf-guide.html) ) where lower values are higher quality (`-crf 0` is not lossless at 10-bit; see [Lossless Encoding](#lossless-encoding)). By default this is set to 23, which is a little on the low quality side; using values closer to 18 is recommended, but this does come at the expense of file-size. For more on this see the [CRF comparison](#crf-comparison) below. |
| **-qp 23** | Quantization Parameter - it is recommended that you do not use this, in preference to -crf above (see: [https://slhck.info/video/2017/03/01/rate-control.html](https://slhck.info/video/2017/03/01/rate-control.html) ) |
| **-preset slow** | [https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ](https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ) |
| **-qscale:v 9** | Generic quality scale flag: [https://www.ffmpeg.org/ffmpeg.html#toc-Main-options](https://www.ffmpeg.org/ffmpeg.html#toc-Main-options). This is typically used for fixed-quality encoding in some codecs, but CRF is preferred for H.264. |
| **-tune film** | See below. |
| **-movflags +faststart** | `faststart` re-organizes the mp4 file, so that it doesn't have to read the whole file to start playback, useful for streaming. It can add a second or so to do this, since it does require re-writing the file. |
| **-vf "zscale=...,setparams=..."** | Convert the RGB images to BT.709 Y'CbCr with zscale and tag the result; see [zscale Conversion](EncodeZscale.html). The `-color_*` flags are then not needed, but are harmless. |

### Tune Parameter

Optionally use the tune option to change settings based on specific inputs - [https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ](https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ)

| Tuning | Description |
| :--- | :--- |
| **-tune film** | Good for live action content. |
| **-tune animation** | Good for animated content with areas of flat colors. |
| **-tune grain** | Good for live action content where you want to preserve the grain as much as possible. |

see also: [https://superuser.com/questions/564402/explanation-of-x264-tune](https://superuser.com/questions/564402/explanation-of-x264-tune)

### CRF Comparison

To help pick appropriate values with the CRF flag, we have run the [Test Framework](enctests/README.html) through some of the [reference media](enctests/sources/enc_sources/README.html).

| ![](enctests/reference-results/h264-crf-test-encode_time.png)  This is showing CRF values against encoding time. |
| ![](enctests/reference-results/h264-crf-test-filesize.png) This is showing CRF values against file size. |
| ![](enctests/reference-results/h264-crf-test-vmaf_harmonic_mean.png) This is showing CRF values against VMAF harmonic mean |

### libx264 preset comparisons

Below is showing a comparison of different preset values with a crf value of 18.
It shows that you really can just encode with -preset medium or -preset slow anything higher is really not gaining you anything.

| ![](enctests/reference-results/h264-test-encode_time.png)  This is showing preset values against encoding time. |
| ![](enctests/reference-results/h264-test-filesize.png) This is showing preset values against file size. Seeing very little variation in file size for the different presets. |
| ![](enctests/reference-results/h264-test-vmaf_harmonic_mean.png) This is showing preset values against VMAF harmonic mean (quality). |

### H264 Bitdepth

By default, h264 is created as yuv420p (8-bit 4:2:0), which is the most widely supported format. We recommend 10-bit 4:2:0 (`-pix_fmt yuv420p10le`) where your players allow it, since it avoids most of the banding of 8-bit at a similar file size.

In our tests on macOS 26, Safari, Chrome and Firefox all played 10-bit H.264, although Chrome placed its chroma half a pixel off (see [Chroma Siting Tests](ChromaSitingTests.html#chart-420)). Browsers on other platforms, and hardware players, have not been retested. Where a file has to play everywhere, use `-pix_fmt yuv420p`.

The h264 codec also supports other formats, selected with the `-pix_fmt` flag.

Setting `-pix_fmt` to 10-bit or high-chroma formats usually auto-selects the appropriate H.264 profile. However, explicitly setting `-profile:v` is recommended for ensuring compatibility with specific hardware decoders.

| Pixel Format | Recommended Profile | Supported Features |
| :--- | :--- | :--- |
| **yuv420p10le** | `high10` | 10-bit color, 4:2:0 subsampling. |
| **yuv422p10le** | `high422` | 10-bit color, 4:2:2 subsampling. |
| **yuv444p10le** | `high444` | 10-bit color, 4:4:4 subsampling. |

### Hardware Acceleration

#### macOS VideoToolbox

Uses the Apple hardware encoder. Ideal for fast proxies and web review on Apple Silicon.

```console
ffmpeg -i input.mov -c:v h264_videotoolbox -profile:v high -pix_fmt yuv420p -b:v 10M output.mp4
```

#### NVIDIA NVENC

Uses NVIDIA's dedicated hardware encoder (available on Windows/Linux).

```console
ffmpeg -i input.mov -c:v h264_nvenc -preset slow -rc vbr -cq 19 -pix_fmt yuv420p output.mp4
```

### Lossless Encoding

To achieve mathematically lossless encoding with `libx264`, use `-qp 0`. `-crf 0` is not lossless at 10-bit: it gave errors of up to 94 code values where `-qp 0` was exact (FFmpeg 6.1.6, 7.1.5 and 9.0.2). Only the encode is lossless; the RGB to Y'CbCr conversion before it still rounds. Lossless files can be extremely large and may not play back in standard web browsers.

```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
    -c:v libx264 -qp 0 -pix_fmt yuv444p10le -color_range tv -colorspace bt709 output_lossless.mp4
```
