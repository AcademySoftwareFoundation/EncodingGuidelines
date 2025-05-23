---
layout: default
nav_order: 2
title: Encoding Cheatsheet
---

# Encoding Cheatsheet

This is a cheatsheet for encoding best practices for VFX/Animation production. For each section there are more detailed sections on why these settings are picked, and notes on what parameters you may want to change.

This document is based on results from ffmpeg 6.0.

# H264 Encoding from an image sequence for Web Review

If you are encoding from an [image sequence](FfmpegInputs.html) (e.g. imagefile.0000.png imagefile.0001.png ...) to h264 using ffmpeg, we recommend:

<!---
name: test_quickstart
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/chip-chart-1080-16bit-noicc-yuv420p.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -pix_fmt yuv420p \
        -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
        -frames:v 100 -c:v libx264 -preset slower -crf 18 \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
       -movflags faststart outputfile.mp4
```

| --- | --- |
| **-r 24**     | means 24 frames per second for the png files. |
| **-start_number** 1 | The frame sequence starts from frame 1 (defaults to 0) |
**-i inputfile.%04d.png** | the %04d means the file sequence will be padded to 4 digits, i.e. 0000, 0001, 0002, etc. It is the same syntax supported by the C printf function.
**[-frames:v](https://ffmpeg.org/ffmpeg.html#toc-Video-Options) 100** | is optional, but allows you to specify how many frames to encode, otherwise it will encode the entire frame range. There is an obsolete alias flag `-vframes` which will be retired.
**-c:v libx264** | use the h264 encoding library (libx264)
**-preset slower** | a reasonably high quality preset, which will run slow, but not terribly slow.
**-pix_fmt yuv420p** | use yuv420 video format, which is typical for web playback. If you want a better quality for RV or other desktop tools use -pix_fmt yuv444p10le
**-color_range tv** | mp4 metadata - specifying color range as 16-235 (which is default for web playback).
**-colorspace bt709** | mp4 metadata - specifying bt709 yuv color pixel format
**-color_primaries bt709** | mp4 metadata - bt709 color gamut primaries
**-color_trc iec61966-2-1** | mp4 metadata color transfer = iec61966-2-1 = sRGB - See tests [here](WebColorPreservation.html). In some cases, you may also want -color_trc bt709 |
**-movflags faststart** | This re-organises the mp4 file, so that it doesnt have to read the whole file to start playback, useful for streaming. It can add a second or so to do this, since it does require re-writing the file. |

**-vf "scale=in_color_matrix=bt709:out_color_matrix=bt709"** means use the sw-scale filter, setting:

| --- | --- |
| **in_color_matrix=bt709** | color space bt709 video coming in (normal for TV/Desktop video).|
| **out_color_matrix=bt709** | means color space bt709 video going out.  |

The combination of this and in_color_matrix will mean the color encoding will match the source media. If you are only adding one set of flags, this is the one, otherwise it will default to an output colorspace of bt601, which is a standard definition spec from the last century, and not suitable for sRGB or HD displays.

Separately, if you are converting from exr's in other colorspaces, **please use [OCIO](https://opencolorio.org/) to do the color space conversions.** [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) is an excellent open-source tool for this.

For more details see:
   * [H264 Encoding](Encodeh264.html)
   * [YUV Conversion](ColorPreservation.html#yuv)
   * [Browser color issues](WebColorPreservation.html)


# ProRes 422 encoding with ffmpeg.

Unlike h264 and DnXHD, Prores is a reverse-engineered codec. However, in many cases ffmpeg can produce adequate results. There are a number of codecs, we recommend the prores_ks one.

<!---
name: test_proresquickstart
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/smptehdbars_10_yuv422p10le.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png \
    -pix_fmt yuv422p10le -vframes 100 \
    -c:v prores_ks -profile:v 3 -qscale:v 9 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 outputfile.mov
```

| --- | --- |
| **-profile:v 3** | Prores profile |
| **-qscale:v 9** | Controls the output quality, lower numbers higher quality and larger file-size. [See comparison graph](EncodeProres.html#prores_ks--qscalev-comparison) |
| **-pix_fmt yuv422p10le** | Convert to 10-bit YUV 422 |
| **-vendor apl0** | Treat the file as if it was created by the apple-Prores encoder (even though it isn't), helps some tools correctly read the Quicktime |

For more details see:
   * [Prores](EncodeProres.html)
   * [YUV Conversion](ColorPreservation.html#yuv)

# ProRes 4444 encoding with ffmpeg.

As above, but using 4444 (i.e. a color value for each pixel + an alpha)

<!---
name: test_prores444
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png  \
    -pix_fmt yuv444p10le -vframes 100 \
   -c:v prores_ks -profile:v 4444 -qscale:v 9 \
   -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 outputfile.mov
```

| ---------           | ----------- |
| **-profile:v 4444** | Prores profile for 4444 |
| **-qscale:v 9**     | Controls the output quality, lower numbers higher quality and larger file-size. [See comparison graph](EncodeProres.html#prores_ks--qscalev-comparison) |
| **-pix_fmt yuv444p10le** | Convert to 10-bit YUV 4444 |

For more details see:
   * [Prores](Encoding.html#prores)
   * [YUV Conversion](ColorPreservation.html#yuv)

# TV vs. Full range. <a name="tvfull"></a>
All the video formats typically do not use the full numeric range but instead the R', B', G' and Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantisation artifacts for 8-bit encoding (the standard for web playback).

TODO Get Quantization examples.

You can force the encoding to be full range using the libswscale library by using
```
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709"
```
Specifying *out_range=full* forces the output range, but you also need to set the NCLX tag:
```
-color_range 2
```
A full example encode would look like:

<!---
name: test_fullrange
sources: 
- sourceimages/radialgrad.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -y -loop 1 -i ../sourceimages/radialgrad.png \
    -pix_fmt yuv420p -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" \
    -c:v libx264 -t 5  -qscale:v 1 \
    -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 ./greyramp-fulltv/radialgrad-full.mp4
```
We have seen the full range encoding work across all browsers, and a number of players including RV.

TODO: Do additional testing across all players.

For more details see:
   * [Comparing full-range vs. tv range](https://academysoftwarefoundation.github.io/EncodingGuidelines/tests/greyramp-fulltv/compare.html)
   * [Encoding Guide](Encoding.html#range)

