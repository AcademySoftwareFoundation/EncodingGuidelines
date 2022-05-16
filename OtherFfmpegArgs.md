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


See: https://trac.ffmpeg.org/wiki/Scaling for more info.


## Concatination of video files.

See: https://trac.ffmpeg.org/wiki/Concatenate

This has been useful in splitting long prores encodes into chunks, and then merging them back together.
The merge process is not quick, so there are limits to how much you can split the process, but provided that the merge process not I/O bound, it can typically end up with faster encodes.

TODO - Provide some examples of speed improvement, as well as a sample command line.
