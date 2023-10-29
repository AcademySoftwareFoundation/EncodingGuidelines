---
layout: default
title: Other ffmpeg arguments.
nav_order: 5.5
parent: Encoding Overview
---

# Other ffmpeg arguments.

This is covering other things that can be done directly in ffmpeg that might be useful.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>


## Audio

```
-filter_complex "[1:0]apad" -shortest
```
This is a useful filter to add when adding an audio file, if the audio file might not match the length of the resulting movie. This will either pad the audio to match the video, if the audio is short, or truncate the audio to match the video.

TODO - Provide full example of adding audio to the "quickstart" demo.

## Image resizing.

### Keeping the image height a factor of 2.

There may be reasons that you want to do any image resizing directly inside ffmpeg, (e.g. when converting from another movie format). A number of the codecs require that the width and height be a factor of 2 (and sometimes 4). The expression below will ensure that the height is set correctly, assuming the width is 1920
```
-vf scale=1920:trunc(ow/a/2)*2:flags=lanczos
```

If you are downrezing, you will get the best results with the lancozs filter, otherwise the default is bicubic.

TODO - this needs testing, to confirm filter quality.


See: [https://trac.ffmpeg.org/wiki/Scaling](https://trac.ffmpeg.org/wiki/Scaling) for more info.


## Concatination of video files.

See: [https://trac.ffmpeg.org/wiki/Concatenate](https://trac.ffmpeg.org/wiki/Concatenate)

This has been useful in splitting long prores encodes into chunks, and then merging them back together.
The merge process is not quick, so there are limits to how much you can split the process, but provided that the merge process not I/O bound, it can typically end up with faster encodes.

TODO - Provide some examples of speed improvement, as well as a sample command line.

## ffmpeg help

If you find the below to be too terse, [ffimprovisr](https://amiaopensource.github.io/ffmprovisr/) is a great resource to find more friendly descriptions/examples of common ffmpeg use-cases.

| | |
| ffmpeg -formats | list all file formats |
| ffmpeg -muxers | list all muxers (e.g. mp4, mov) |
| ffmpeg -h muxer=<MUXERNAME> | List of options for a particular muxer, e.g. ffmpeg -h muxer=mp4 |
| ffmpeg -filters | list all filters
| ffmpeg -codecs | list all codecs (encoders and decoders) |
| ffmpeg -encoders | list just encoders | 
| ffmpeg -h encoder=<ENCODERNAME> | List args for specified encoder, e.g. ffmpeg -h encoder=prores_ks. This also lists what supported pixel formats are supported. |
| ffmpeg -h decoder=<DECODERNAME> | List args for specified decoder, e.g. ffmpeg -h decoder=exr |

## Useful Filters

Ffmpeg has a crazy number of filters (see [Ffmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)) below are some potentially relevant ones to VFX pipelines.

### stereo framepack

https://www.ffmpeg.org/ffmpeg-filters.html#toc-framepack - Generate a frame packed stereoscopic video 
```
ffmpeg -i LEFT -i RIGHT -filter_complex framepack=frameseq OUTPUT
```

### stereo3d 
https://www.ffmpeg.org/ffmpeg-filters.html#toc-stereo3d 
Re-pack an existing stereo movie into a different format

### SMPTE HD bars

Creates a [SMPTE HD colorbars](https://en.wikipedia.org/wiki/SMPTE_color_bars) image. NOTE, this is actually created in YUV space, and only for 8-bit Y'CrCb. 

ffmpeg does have a built-in SMPTE color bars, however by default, it does not create it in the right colorspace, so you do need to specify the color primaries, colorspace and colortrc to make it behave correctly.
Also note, these are 8-bit only.

This is an h264 output yuv422p

```
ffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -c:v h264 -crf 10  smptehdbars-h264.mov
```

This is a 8-bit 444 raw encode.

```
ffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1,format=yuv444p -c:v v408 smptehdbars-v408.mov
```

This is a PNG output, warning this would only be to the legal range, so the [pluge](https://en.wikipedia.org/wiki/Picture_line-up_generation_equipment) would be zeroed out:

```
ffmpeg -color_primaries bt709 -colorspace bt709 -color_trc bt709 -re -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -vframes 1  smptehdbars.png
```

### Nullsrc
A dummy source video signal.

Creating a blank YUV h264 file of 1024 frames.
```
ffmpeg -r 24 -f lavfi -i nullsrc=s=1280x720,format=yuv444p -frames:v 1024 yuv444p.mov
```

Creating a blank YUV 10-bit h264 file
```

ffmpeg -r 24 -f lavfi -i nullsrc=s=1280x720,format=yuv444p10le -frames:v 1024 yuv444p10le.mov
```

THis is commonly used with geq.

### geq

[geq](https://www.ffmpeg.org/ffmpeg-filters.html#geq)  Apply a generic equation to each pixel 

```
ffmpeg -r 24 -f lavfi -i nullsrc=s=512x512 -pix_fmt yuv444p -frames:v 1024 -vf geq=X/2:128:128 yuv444p_ramp.mov
```

If you want other bit-depths, you do need to add an additional format flag for example:
```
ffmpeg -r 24 -f lavfi -i nullsrc=s=1024x512,format=yuv444p10le -frames:v 1024 -vf geq=X:512:512 yuv444p10_ramp.mov
```


### identity

Calculate the differences between two image streams.
[toc-identity](https://www.ffmpeg.org/ffmpeg-filters.html#toc-identity)

```
ffmpeg -i movie1.mov -i movie2.mov -lavfi identity -f null -
```

Will output a line like:
```
 identity Y:0.430940 U:0.516449 V:0.448389 average:0.465259 min:0.452062 max:0.480941``
```

Where each number is a 0-1 scale, where 1 is identical.

The two images need to be the same resolution and pixel format (at least both RGB or YCrCb).

### lut lutrgb and lutyuv

[lut_002c-lutrgb_002c-lutyuv](https://www.ffmpeg.org/ffmpeg-filters.html#toc-lut_002c-lutrgb_002c-lutyuv)

Allows you to create a calculated LUT that is then applied to the picture.

### PSNR
Obtain the average, maximum and minimum PSNR (Peak Signal to Noise Ratio) between two input videos
[psnr](https://www.ffmpeg.org/ffmpeg-filters.html#toc-psnr)

```
ffmpeg -i movie1.mov -i movie2.mov -lavfi psnr -f null -
```

Will output a line like:

```
PSNR y:46.121876 u:50.295497 v:48.852140 average:46.987439 min:45.790238 max:49.754820
```

### v360

Convert 360 videos between various formats.
[v360](https://www.ffmpeg.org/ffmpeg-filters.html#toc-v360)

### vectorscope

[vectorscope](https://www.ffmpeg.org/ffmpeg-filters.html#toc-vectorscope)

