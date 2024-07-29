---
layout: default
nav_order: 6.08
title: Bit Depth Analysis
parent: Test Output
---

# Bit Depth Analysis

Sometimes its useful to know what the actual dynamic range of a particular combination of codec, profile and pixel format is, since it may not necessarily be what you think. i.e. you think you are getting 10-bits (i.e. 1024 values) when in fact you could be getting quite a bit less.

This work is inspired by [https://github.com/ColorlabMD/Prores-BitDepth](https://github.com/ColorlabMD/Prores-BitDepth).

These tests generate a luminance YCrCb flat image, where each frame increments the luminance by one using the geq ffmpeg filter.

For example for the prores_ks codec we would run:

```
ffmpeg -y -r 24 -f lavfi -i nullsrc=s=720x480,format=yuv444p10le -frames:v 1024 -vf geq=N:512:512 -c:v prores_ks -profile:v 4444xq ./colors-prores_ks_10_4444xq.mov
```

We then read the resulting movie file, to see if the luminance that we expect.

The columns are defined as:
   * Test Name - which codec we are testing.
   * Bit Depth - What bit-depth the codec is being evaluated to (which determines how many unique values to test to).
   * Unique values - How many resulting values are unique, but may not be exactly the same value.
   * STDDEV > 0.0001 - Standard deviation of the frame is > 0.0001 which means what should be a flat color, isnt.
   * Off by 1 - The color is a flat color, but is "off by 1" (i.e. what should be 3 is 4), again not ideal.
   * Other invalid - is a flat color, but is some other value than expected.

## Running the tests

To run the tests you need three additional python libraries as well as ffmpeg:

```
pip install yuvio numpy pyseq 
```

Warning: The file sizes can get large, so expect it to generate 8GB of data.

Note, the one thing the ColorlabMD test does that this does not currently do is to also do a comparison of chroma variation.

## Results

### Prores_ks

Tests - prores_ks_10_4444xq, prores_ks_10_proxy, prores_ks_10_hq

It shows that the ffmpeg_ks encoder is only encoding to the legal 10-bit range (i.e. 877 values), which is pretty much what we expect.

The tests [https://github.com/ColorlabMD/Prores-BitDepth](https://github.com/ColorlabMD/Prores-BitDepth) tests seem a little unfair on prores_ks, which clearly defines itself as a 10-bit codec, and I suspect that the apple encoding is setting full range values which Prores (in this case) is not.

Note, Prores_ks will read 12 bit files, just not generate them.

### Apple Videotoolbox Prores

Tests - prores_videotoolbox_10_proxy, prores_videotoolbox_10_hq, prores_videotoolbox_10_4444, prores_videotoolbox_12_xq

Interestingly, we are getting better results for prores_ks for proxy and HQ, in that the values are at least consistent, which for videotoolbox they are often off by 1.

However, for 4444 and XQ they are good.

### DNxHD

All the values are as expected.

### h264

All the values are as expected.

### x265 HEVC

x265 HEVC is struggling with flat color with quite a few values not generating a uniform value, unless lossless is used.

### VP9 

All the values are as expected.

### libsvtav1

All the values are as expected.

### libaom-av1

Is slightly better, with 866 unique values, but many of them are off by one or more. At 12-bit the results are similar. Using lossless will maintain all values (as expected). 


Click [here](bitDepthResults.html) to see the full page table.

{% include_relative bitDepthResults.html %}
