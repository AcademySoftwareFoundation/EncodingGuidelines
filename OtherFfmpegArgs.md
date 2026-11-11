---
layout: default
title: Useful FFmpeg Filters
nav_order: 5.65
parent: Encoding Overview
---

# Useful FFmpeg Filters

This is covering other things that can be done directly in FFmpeg that might be useful.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Other FFmpeg Resources

* [GOP values explained](https://aws.amazon.com/blogs/media/part-1-back-to-basics-gops-explained/#:~:text=Simply%20put%2C%20a%20GOP%20is,30%20frames%2C%20or%201%20second)
* [ffmprovisr](https://amiaopensource.github.io/ffmprovisr/) is a great resource to find more friendly descriptions/examples of common ffmpeg use-cases.

## Audio

```console
-filter_complex "[1:0]apad" -shortest
```

This is a useful filter when adding an audio file that might not match the length of the resulting movie. The `apad` filter pads the audio with silence if it's shorter than the video, and `-shortest` ensures the output ends when the shortest stream (usually the video) finishes.

### Full Example: Adding Audio to a Video

```console
ffmpeg -i video.mp4 -i audio.wav \
    -c:v copy -c:a aac -b:a 192k \
    -filter_complex "[1:0]apad" -shortest output.mp4
```

## Image resizing

### Keeping the image height a multiple of 2

There may be reasons that you want to do any image resizing directly inside ffmpeg, (e.g. when converting from another movie format). A number of the codecs require that the width and height be a multiple of 2 (and sometimes 4). The expression below will ensure that the height is set correctly, assuming the width is 1920

```console
-vf "scale=1920:trunc(ow/a/2)*2:flags=lanczos"
```

If you are down-scaling, you will get the best results with the `lanczos` filter; otherwise, the default is `bicubic`. The `lanczos` filter provides higher sharpness and reduces aliasing compared to simpler filters, making it the preferred choice for high-quality VFX delivery.

See: [https://trac.ffmpeg.org/wiki/Scaling](https://trac.ffmpeg.org/wiki/Scaling) for more info.

## Concatenation of video files

See: [https://trac.ffmpeg.org/wiki/Concatenate](https://trac.ffmpeg.org/wiki/Concatenate)

This is particularly useful when splitting long ProRes encodes into chunks across multiple machines or processes, then merging them back together.

### Example: Using the Concat Demuxer

First, create a `filelist.txt`:

```text
file 'part1.mov'
file 'part2.mov'
file 'part3.mov'
```

Then run the concatenation command:

```console
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mov
```

The `-c copy` flag ensures that the streams are merged without re-encoding, making the process extremely fast and preserving original quality. This workflow can significantly reduce total turnaround time for long deliveries by allowing parallel encoding of segments.

## ffmpeg help

| Command | Description |
| --- | --- |
| `ffmpeg -formats` | list all file formats |
| `ffmpeg -muxers` | list all muxers (e.g. mp4, mov) |
| `ffmpeg -h muxer=<MUXERNAME>` | List of options for a particular muxer, e.g. ffmpeg -h muxer=mp4 |
| `ffmpeg -filters` | list all filters |
| `ffmpeg -codecs` | list all codecs (encoders and decoders) |
| `ffmpeg -encoders` | list just encoders |
| `ffmpeg -h encoder=<ENCODERNAME>` | List args for specified encoder, e.g. ffmpeg -h encoder=prores_ks. This also lists the supported pixel formats. |
| `ffmpeg -h decoder=<DECODERNAME>` | List args for specified decoder, e.g. ffmpeg -h decoder=exr |

## Useful Filters

FFmpeg has a crazy number of filters (see [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)) below are some potentially relevant ones to VFX pipelines.

### stereo framepack

<https://www.ffmpeg.org/ffmpeg-filters.html#toc-framepack> - Generate a frame packed stereoscopic video

```console
ffmpeg -i LEFT -i RIGHT -filter_complex framepack=frameseq OUTPUT
```

### stereo3d

<https://www.ffmpeg.org/ffmpeg-filters.html#toc-stereo3d>
Re-pack an existing stereo movie into a different format

### SMPTE HD bars

Creates a [SMPTE HD colorbars](https://en.wikipedia.org/wiki/SMPTE_color_bars) image. The `smptehdbars` source
draws the bars directly as 8-bit Y'CbCr, limited range, with BT.709 values (75% yellow is Y' 168). It does not tag
them correctly: 6.1.6 tags the matrix as BT.709 but sets no primaries or transfer, and from 7.0 it tags the matrix
as BT.601 (`bt470bg`), so anything that converts the frames to RGB uses the wrong matrix (75% yellow comes out as
188,203,6 instead of 191,191,0). This looks like a bug: the filter compares its instance name, not the filter name,
with `smptehdbars`. Colour flags before `-i` (`-colorspace bt709 -f lavfi -i smptehdbars...`) change neither the
pixels nor the matrix tag. Add `setparams` to the source instead, as in all the commands below (tested on 6.1.6,
7.1.5 and 9.0.2).

For accurate bars, use the [vapoursynth-colorbars](https://github.com/ifb/vapoursynth-colorbars) plugin for
[VapourSynth](https://www.vapoursynth.com/) instead. It uses the 10-bit and 12-bit Y'CbCr values tabulated in
SMPTE RP 219-2 directly, rather than calculating them, and can also make ITU-R BT.2111 HLG and PQ bars, NTSC and
PAL bars, and sizes from 720p to 8K. A script such as `bars.vpy`:

```python
import vapoursynth as vs
from vapoursynth import core

core.std.LoadPlugin("/path/to/libcolorbars.dylib")  # .so on Linux, .dll on Windows
c = core.colorbars.ColorBars(resolution=3, format=vs.YUV444P10)  # 1920x1080, 10-bit 4:4:4
c.set_output()
```

piped into FFmpeg, with `setparams` to tag it:

```console
vspipe -c y4m bars.vpy - | ffmpeg -i - \
    -vf "setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709" \
    -c:v ffv1 -level 3 smptehdbars-10bit.mkv
```

The test framework's references in
[sourceimages/rp219](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/tree/main/sourceimages/rp219)
were made this way, and the
[sourceimages README](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/sourceimages/README.md)
gives the options used and how they were validated. You can use those files directly if 1920x1080 10-bit or
12-bit BT.709 is what you need.

H.264, 8-bit 4:2:0:

```console
ffmpeg -f lavfi -i "smptehdbars=duration=1:size=1920x1080:rate=1,setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709" \
    -c:v libx264 -crf 10 smptehdbars-h264.mov
```

Uncompressed 8-bit 4:4:4 (FFmpeg 9.0 and later; the `v408` encoder was removed in 9.0, so on earlier versions use
`-c:v v408` instead of `-c:v rawvideo -pix_fmt uyva`; both write the same `v408` file):

```console
ffmpeg -f lavfi -i "smptehdbars=duration=1:size=1920x1080:rate=1,setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709" \
    -frames:v 1 -c:v rawvideo -pix_fmt uyva smptehdbars-v408.mov
```

PNG, converted to RGB with `zscale`. The bars are limited range, so the
[pluge](https://en.wikipedia.org/wiki/Picture_line-up_generation_equipment) below black is clipped to 0. Use
`format=gbrp`, not `rgb24`: zscale cannot output `rgb24`, and FFmpeg 8.0 and earlier then convert with libswscale,
which gives 189 instead of 191 for the 75% bars.

```console
ffmpeg -f lavfi -i "smptehdbars=duration=1:size=1920x1080:rate=1,setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709" \
    -frames:v 1 -vf "zscale,format=gbrp" smptehdbars.png
```

### Zoneplate

Creates a [Zoneplate test chart](https://ffmpeg.org/ffmpeg-filters.html#zoneplate). This was introduced in ffmpeg 6.1 and is great for testing filtering.

Creating it with ffmpeg directly to RGB:

```console
ffmpeg -f lavfi -i zoneplate=ku=512:kv=100:kt2=0:ky2=256:kx2=556:s=wvga:yo=0:kt=11:duration=1 -pix_fmt rgb48be zoneplate_rgb16.png
```

Creating it with ffmpeg directly to YCbCr:

```console
ffmpeg -f lavfi -i zoneplate=ku=512:kv=100:kt2=0:ky2=256:kx2=556:s=wvga:yo=0:kt=11:duration=1 -pix_fmt yuv420p10 -strict -1 zoneplate_yuv420p10.y4m
```

### Nullsrc

A dummy source video signal.

Creating a blank YUV h264 file of 1024 frames.

```console
ffmpeg -r 24 -f lavfi -i nullsrc=s=1280x720,format=yuv444p -frames:v 1024 yuv444p.mov
```

Creating a blank YUV 10-bit h264 file

```console
ffmpeg -r 24 -f lavfi -i nullsrc=s=1280x720,format=yuv444p10le -frames:v 1024 yuv444p10le.mov
```

This is commonly used with geq.

### geq

[geq](https://www.ffmpeg.org/ffmpeg-filters.html#geq)  Apply a generic equation to each pixel

```console
ffmpeg -r 24 -f lavfi -i nullsrc=s=512x512 -pix_fmt yuv444p -frames:v 1024 -vf geq=X/2:128:128 yuv444p_ramp.mov
```

If you want other bit-depths, you do need to add an additional format flag for example:

```console
ffmpeg -r 24 -f lavfi -i nullsrc=s=1024x512,format=yuv444p10le -frames:v 1024 -vf geq=X:512:512 yuv444p10_ramp.mov
```

### identity

Calculate the differences between two image streams.
[toc-identity](https://www.ffmpeg.org/ffmpeg-filters.html#toc-identity)

```console
ffmpeg -i movie1.mov -i movie2.mov -lavfi identity -f null -
```

Will output a line like:

```console
 identity Y:0.430940 U:0.516449 V:0.448389 average:0.465259 min:0.452062 max:0.480941
```

Where each number is a 0-1 scale, where 1 is identical.

The two images need to be the same resolution and pixel format (at least both RGB or YCbCr).

### lut lutrgb and lutyuv

[lut_002c-lutrgb_002c-lutyuv](https://www.ffmpeg.org/ffmpeg-filters.html#toc-lut_002c-lutrgb_002c-lutyuv)

Allows you to create a calculated LUT that is then applied to the picture.

### PSNR

Obtain the average, maximum and minimum PSNR (Peak Signal to Noise Ratio) between two input videos
[psnr](https://www.ffmpeg.org/ffmpeg-filters.html#toc-psnr)

```console
ffmpeg -i movie1.mov -i movie2.mov -lavfi psnr -f null -
```

Will output a line like:

```console
PSNR y:46.121876 u:50.295497 v:48.852140 average:46.987439 min:45.790238 max:49.754820
```

### v360

Convert 360 videos between various formats.
[v360](https://www.ffmpeg.org/ffmpeg-filters.html#toc-v360)

### vectorscope

[vectorscope](https://www.ffmpeg.org/ffmpeg-filters.html#toc-vectorscope)
