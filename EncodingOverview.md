---
layout: default
nav_order: 3
title: Encoding Overview
has_children: true

---

{: .no_toc }

# Media Encoding with ffmpeg  <a name="encodestart"></a>

We will break the encoding process into three parts:
1. [The RGB to YCrCb conversion](#Color-space-conversion)
2. [The encoding process itself](Encoding.html)
3. [Metadata tagging for web browsers](WebColorPreservation.html)

# Color space conversion.  <a name="Color-space-conversion"></a>

FFmpeg is not a great tool for colorspace conversion. We recommend that any color space conversion be done using tools such as [Nuke](https://www.foundry.com/products/nuke-family/nuke) or [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) using [OCIO](https://opencolorio.org/). We strongly recommend using the ACES configuration whenever possible, since it provides a good baseline for colorspace conversion. Note, we may mention the use of Nuke a number of times, there are now a large number of 3rd party tools that will also do great at this color space conversion using OCIO.

Typically, we would assume that an intermediate file would get written out, such as PNG, TIF or DPX for processing in ffmpeg.

Hint: by default the nuke PNG writer will have the slow compression enabled, this does add a little time that is unnecessary for the sort of intermediate file we are using. In the nuke SDK they do provide the source for the PNG writer, so it is possible to get this disabled. However, you may find that switching to Tif will have the same result.
