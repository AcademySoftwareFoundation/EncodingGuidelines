---
layout: default
nav_order: 7.2
title: HDR Reference Source Test Media
parent: ASWF Encoding Test Framework
---

# Reference Source Test Media for HDR Media.

We have collected a number of source clips that you can use to test on, these are mostly from the excellent netflix [Open Source Content](https://opencontent.netflix.com/) site. Some of the clips are quite large, so we have tried to extract shorter 100-200 frame clips for the encoding tests, and also extracting individual clips from edited sequences.

You can download the clips using the `download_media.sh` shell script. The script will also convert the frames for the appropriate test image type and color space using oiiotool.

The clips that are created include:

| ![sparks_srgb](thumbnails/sparks_srgb.6015.jpg) | [Sparks part 1](https://opencontent.netflix.com/#h.d0oh6u8prqhe) |  Creating both srgb and hlg color space versions for testing HDR and regular sRGB encodes |
| ![sparks2_srgb](thumbnails/sparks2_srgb.06726.jpg) | [Sparks part 2](https://opencontent.netflix.com/#h.d0oh6u8prqhe) |  Creating both srgb and hlg color space versions for testing HDR and regular sRGB encodes |
