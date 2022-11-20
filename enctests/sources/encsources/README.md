---
layout: default
nav_order: 7.1
title: Reference Source Test Media
parent: ASWF Encoding Test Framework
---

# Reference Source Test Media for HDR Media.

We have collected a number of source clips that you can use to test on, these are mostly from the excellent netflix [Open Source Content](https://opencontent.netflix.com/) site. Some of the clips are quite large, so we have tried to extract shorter 100-200 frame clips for the encoding tests, and also extracting individual clips from edited sequences.

You can download the clips using the `download_media.sh` shell script. The script will also convert the frames for the appropriate test image type and color space using oiiotool.

The clips that are created include:

| ![chimera_cars](thumbnails/chimera_cars_srgb.02516.jpg) | [Chimera cars](https://opencontent.netflix.com/#h.nv6npqncwttv) | creating sRGB versions from HDR_P3PQ exr files converted to sRGB|
| ![chimera fountain](thumbnails/chimera_fountains_srgb.05439.jpg) | [Chimera fountains](https://opencontent.netflix.com/#h.nv6npqncwttv) | creating sRGB versions from HDR_P3PQ exr files converted to sRGB |
| ![chimera wind](thumbnails/chimera_wind_srgb.01126.jpg) | [chimera wind chimes](https://opencontent.netflix.com/#h.nv6npqncwttv) | creating sRGB versions from HDR_P3PQ exr files converted to sRGB|


Other media that could be useful include:
| ![sintel trailer](thumbnails/sintel_trailer_2k_0591.jpg) | [sintel 1080p-png trailer download](https://s3.amazonaws.com/senkorasic.com/test-media/video/sintel/source/Sintel-trailer-1080p-png.zip) | Blender CG created media. |


There are other reference media at: [media.xiph.org](http://media.xiph.org/) and [media.xiph.org/video/derf](http://media.xiph.org/video/derf) in particular. Sadly, most of this media is in a [y4m](https://wiki.multimedia.cx/index.php/YUV4MPEG2) file format, but it can be a good place to look for other test media. This dataset is used for the [https://arewecompressedyet.com/?](https://arewecompressedyet.com/?) site, that is used for comparing different codecs (see [https://github.com/xiph/awcy](https://github.com/xiph/awcy) for the source for the web site).