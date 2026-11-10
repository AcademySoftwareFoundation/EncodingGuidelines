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

Creates a [SMPTE HD colorbars](https://en.wikipedia.org/wiki/SMPTE_color_bars) image. NOTE, this is actually created in YUV space, and only for 8-bit Y'CbCr.

ffmpeg does have a built-in SMPTE color bars, however by default, it does not create it in the right colorspace, so you do need to specify the color primaries, colorspace and colortrc to make it behave correctly.
Also note, these are 8-bit only.

This is an h264 output yuv422p

```console
ffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -c:v h264 -crf 10  smptehdbars-h264.mov
```

This is a 8-bit 444 raw encode.

```console
ffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1,format=yuv444p -c:v v408 smptehdbars-v408.mov
```

This is a PNG output, warning this would only be to the legal range, so the [pluge](https://en.wikipedia.org/wiki/Picture_line-up_generation_equipment) would be zeroed out:

```console
ffmpeg -color_primaries bt709 -colorspace bt709 -color_trc bt709 -re -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -frames:v 1  smptehdbars.png
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
