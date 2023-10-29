---
layout: default
title: Ffmpeg Frame Sequences Specification
nav_order: 2
parent: Encoding Overview

---

# Ffmpeg Frame Sequences Specification

Care needs to be taken when specifying frame sequences, since there is additional metadata that would normally be present in a movie container (e.g. mp4 or mov files) that are not present in an image sequence.

Ffmpeg will convert an image sequence using the [image2](https://ffmpeg.org/ffmpeg-formats.html#image2-1) demuxer. This provides the code for determining how to wildcard as well as how to specify the frame-rate.

## Image sequences

There are two approaches for defining image sequences, globbing and printf style.

### Printf image sequence definition.

The conventional approach is to define the image sequence with a "%d" or a "%0Nd", which specifies where the frame number should go, for example:
img.%d.png

would match: img.0.png img.1.png img.2.png ... img.10.png etc.

img.%04d.png means the numbers need to be zero padded to 4 digits, so it would match img.0000.png img.0001.png img.0002.png ... etc.

By default, the frame number is expect to start from 0, but you can define it with the flag: `-start_number`, e.g.:
```console
ffmpeg -start_number 1 -i img.%04d.png foo.mov
```
Would start from frame number img.0001.png

If not defined the end frame will be the last continuous frame in the frame sequence, so if you have a missing frame it will stop there. 
You can define the number of frames to capture using the `-frames:v` flag.

N.B. In a windows command shell, % has a special meaning, so you may need to escape the "%", by replacing it with %%, or quote it, e.g.:
```console
ffmpeg -start_number 1 -i img.%%04d.png foo.mov
```
TODO TEST.

### Globbing image sequence definition.

There is a globbing option that makes it a little easier to specify a block of frames, since you dont need to specify the first frame.

```console
ffmpeg -pattern_type glob -i "img.*.png" foo.mov
```
Will grab all frames that start with img. and end with ".png"



## Frame Rate

The following aliases are defined for framerate values, either `-r` or `-framerate` parameters.

| ntsc | 30000/1001 | 29.97 fps equivalent. |
| pal | 25| |
| qntsc | 30000/1001 | VCD compliant NTSC - 29.97 fps |
| qpal |  25 | VCD compliant PAL |
| sntsc | 30000/1001 | square pixel NTSC - 29.97 fps  |
| spal |   25 | square pixel PAL |
| film |  24 | |
| ntsc-film |  24000/1001 |  23.98 fps |

Is is prefereable to use a fractional rate, or one of the above settings where possible, for example `-r 30000/1001` is the more precise version of 29.97. 

Other common fractional rates not defined with presets include:

| 60000/1001 | 59.94 fps equiavalent. |
| 120000/1001 | 119.88 fps equivalent |

If not specified, the default framerate chosen is 25 fps (i.e. pal).

TODO Confirm no difference between -r and -framerate. -framerate seems a little more proper.

## Looping

You can loop the input file with the `-loop 1` parameter, e.g.:
```console
ffmpeg -y -pattern_type glob -loop 1 -framerate ntsc -i "../sourceimages/chip-chart-1080-noicc.*.png" -pix_fmt yuv444p10le  -frames:v 100  ./chip-chart-yuvconvert/looptest.mov
```

Note, you want to control the number of frames to output, for a long sequence you would put the `-frames:v 100` before the "-i" flag, but here we are putting it before the output, since we want it to apply to the overall looping input, not the input sequence.

