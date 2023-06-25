---
layout: default
nav_order: 4.1
title: H264 Encoding
parent: Encoding Overview
---

# H264 <a name="h264"></a>

This is the workhorse encoder for web review, its well supported by ffmpeg, and there is a lot of support for both encoding and decoding in hardware.

Key flags (see [https://trac.ffmpeg.org/wiki/Encode/H.264](https://trac.ffmpeg.org/wiki/Encode/H.264) )

| --- | --- |
| **-crf 23** | This is the constant rate factor, controlling the default quality (see: [https://slhck.info/video/2017/02/24/crf-guide.html](https://slhck.info/video/2017/02/24/crf-guide.html) ) where -crf 0 is uncompressed. By default this is set to 23, which is a little on the low side, using values closer to 15 is recommended, but this does come at the expense of file-size. For more on this see the [CRF comparison](CRF Comparison) below. |
| **-qp 23** | Quantization Parameter - it is recommended that you do not use this, in preference to -crf above (see: [https://slhck.info/video/2017/03/01/rate-control.html](https://slhck.info/video/2017/03/01/rate-control.html) ) |
| **-preset slower** | [https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ](https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ) |
| **-qscale:v 9** | Generic quality scale flag: [https://www.ffmpeg.org/ffmpeg.html#toc-Main-options](https://www.ffmpeg.org/ffmpeg.html#toc-Main-options) - TODO experiment with this. |
| **-tune film** | Optionally use the tune option to change settings based on specific inputs - [https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ](https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ) - see also: [https://superuser.com/questions/564402/explanation-of-x264-tune](https://superuser.com/questions/564402/explanation-of-x264-tune) I suspect that we would want to use one of:
    * **-tune film**    good for live action content.
    * **-tune animation** good for animated content with areas of flat colors.
    * **-tune grain**   good for live action content where you want to preserve the grain as much as possible. |

An example would be:
```
-preset slower -crf 11  -profile:v high -tune film
```
#### CRF Comparison

To help pick appropriate values with the CRF flag, we have run the [Test Framework](enctests/README.html) through some of the [reference media](enctests/sources/enc_sources/README.html).

| ![](enctests/reference-results/h264-crf-test-encode_time.png)  This is showing CRF values against encoding time. |
| ![](enctests/reference-results/h264-crf-test-filesize.png) This is showing CRF values against file size. |
| ![](enctests/reference-results/h264-crf-test-vmaf_harmonic_mean.png) This is showing CRF values against VMAF harmonic mean |


#### H264 Bitdepth

By default, h264 is created as a yuv420p file format. This is the recommended format for web playback and also playback with the quicktime player on OSX and other apple devices, but the h264 codec can support other formats that are modified with the `-pix_fmt` flag.

TODO Needs more investigation, e.g. do you set pix_fmt and profile, or will one set the other?

|---|---|
|-pix_fmt yuv444p10le| Defines a YUV 444 image at 10bits per component.|
|-profile:v high10 | Support for bit depth 8-10. |
|-profile:v high422 | Support for bit depth 8-10. Support for 4:2:0/4:2:2 chroma subsampling.|
|-profile:v high444 | Support for bit depth 8-10. for 4:2:0/4:2:2/4:4:4 chroma subsampling.|

### TODO
* Document usage on OSX hardware
* Document Nvidia encoders
