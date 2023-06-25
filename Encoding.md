---
layout: default
nav_order: 4
title: Encoding
parent: Encoding Overview
---

## Encoding Overview <a name="Encoding-Overview"></a>

Creating movies for review should be a simple process where the movie file accurately represents the source media content, so that you can feel confident that issues with the content are not as a result of creating the movie. Sadly, this is not the case, there are many steps that can create an incorrect result, either through a color shift, or encoding artifacts. This frequently means there isn't a single right answer for all cases, so we will attempt to document the different scenarios where you could get tripped up.

We will mostly be focusing on encoding with ffmpeg, however there will be some cases where we will recommend other tools. Splitting the process into two steps:
1. Convert the source media to the target color space.
2. Encode the target intermediate frames into the resulting movie.

## Encoding <a name="encode"></a>
NOTE, We do not have any test suites for encoding a this time. This is an area for future development.

A good starting point for encoding options is here: [https://trac.ffmpeg.org/wiki/Encode/VFX](https://trac.ffmpeg.org/wiki/Encode/VFX)

We have encoding guides for the following:
1. [h264](Encodeh264.html)
2. [Prores](EncodeProres.html)
3. [DNxHD](EncodeDNXHD.html)


TODO:
* Figure out the missing metadata so that ffmpeg can correctly decode a quicktime to still.
* Add other codecs, e.g. DNxHD, AV1
* Do some colorspace tests with different qscale values to see where color breaks down.
* VMAF

