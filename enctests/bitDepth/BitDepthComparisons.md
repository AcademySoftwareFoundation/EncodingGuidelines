---
layout: default
nav_order: 6.08
title: Bit Depth Analysis
parent: Test Output
---

# Bit Depth Analysis

Sometimes its useful to know what the actual dynamic range of a particular combination of codec, profile and pixel format is, since it may not necessarily be what you think. i.e. you think you are getting 10-bits (i.e. 1024 values) when in fact you could be getting quite a bit less.

This work is inspired by [https://github.com/ColorlabMD/Prores-BitDepth](https://github.com/ColorlabMD/Prores-BitDepth).

These tests do some interesting comparisons between the apple prores encoder and ffmpeg.
It shows that the ffmpeg_ks encoder is only encoding to the legal 10-bit range (i.e. 877 values). 

These tests seem a little unfair on prores_ks, which clearly defines itself as a 10-bit codec, and I suspect that the apple encoding is setting full range values which prores (in this case) is not.

Having said that, its still an interesting test to do, so we have implimented an alternative version of this test, which generate a movie directly in YUV space where each frame is a different luminance. We then output the quicktime file to a raw YUV file, and then see how many unique values exist, as well as seeing whether the output values are the same as the values we put in.

Click [here](bitDepthResults.html) to see the full page table.

{% include_relative bitDepthResults.html %}
