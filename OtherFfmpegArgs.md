---
layout: default
title: Other ffmpeg arguments.
nav_order: 5.5
parent: Encoding Overview
---

# Other ffmpeg arguments.

This is covering other things that can be done directly in ffmpeg that might be useful.

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
| ffmpeg -codecs | list all codecs (encoders and decoders) |
| ffmpeg -encoders | list just encoders | 
| ffmpeg -formats | list all file formats |
| ffmpeg -muxers | list all muxers (e.g. mp4, mov) |
| ffmpeg -encoder=<ENCODERNAME> | List args for specified encoder, e.g. ffmpeg -encoder=prores_ks |
| ffmpeg -decoder=<ENCODERNAME> | List args for specified encoder, e.g. ffmpeg -encoder=prores_ks |

## HD Color Bars

ffmpeg does have a built-in SMPTE color bars, however by default, it does not create it in the right colorspace, so you do need to specify the color primaries, colorspace and colortrc to make it behave correctly.
Also note, these are 8-bit only.

This is an h264 output - NOTE, this is a yuv444p output, for more common h264 you may want a yuv420p 
TODO: Figure out why this ends up as a 422 compression.

```
ffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -pix_fmt yuv444p -c:v h264 -crf 10  smptehdbars-h264.mov
```

This is a 8-bit 444 raw encode.

cffmpeg -re -color_primaries bt709 -colorspace bt709 -color_range tv -color_trc bt709 -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -pix_fmt yuv444p -c:v v408 smptehdbars-v408.mov
```

This is a PNG output, warning this would only be to the legal range, so the [pluge](https://en.wikipedia.org/wiki/Picture_line-up_generation_equipment) would be zeroed out:
```
ffmpeg -color_primaries bt709 -colorspace bt709 -color_trc bt709 -re -f lavfi -i smptehdbars=duration=1:size=1920x1080:rate=1 -vframes 1  smptehdbars.png
```
