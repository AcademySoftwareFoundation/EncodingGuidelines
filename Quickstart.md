---
layout: default
nav_order: 2
title: Encoding Cheatsheet
---

# Encoding Cheatsheet

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

This is a cheatsheet for encoding best practices for VFX/Animation production. For each section there are more detailed sections on why these settings are picked, and notes on what parameters you may want to change.

The commands on this page were tested with FFmpeg 6.0 and 9.0. Color handling changed in FFmpeg 7.1, and these
commands give the same result either side of it; see [FFmpeg Version Changes](FFmpegChanges.html).

## H.264 Encoding from an image sequence for Web Review

If you are encoding from an [image sequence](FfmpegInputs.html) (e.g. imagefile.0000.png imagefile.0001.png ...) to H.264 using ffmpeg, we recommend:

<!---
name: test_quickstart
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 6
     - assert: less
       value: mean_error_10bit
       less: 0.5
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: iec61966-2-1
     - assert: stringmatch
       value: colr
       string: nclx 1/13/1 tv
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -pix_fmt yuv420p10le \
        -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
        -frames:v 100 -c:v libx264 -preset slower -crf 18 \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
        -movflags +faststart outputfile.mp4
```

{: .note }
> `zscale` needs an FFmpeg built with zimg (`--enable-libzimg`). Check with `ffmpeg -filters | grep zscale`. If your build does not have it, use the libswscale equivalent instead:
>
> ```console
> -vf "scale=out_color_matrix=bt709:out_range=tv,setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709:range=tv"
> ```
>
> `setparams` labels the matrix and range here as well as the primaries and transfer: before FFmpeg 7.0, `scale` does not label its output frames, and ProRes then writes an unspecified matrix in its frame header even with `-colorspace bt709` (measured on 6.0 to 9.0.2 with `tests/colour_flags_matrix.py`). That gives the right tags on every version, with or without the four `-color_*` flags, but it is less accurate: from 10-bit and 16-bit sources libswscale puts white at 943 instead of 940 (at 10-bit), and it centres the 4:2:2/4:2:0 chroma rather than co-siting it. See [FFmpeg zscale Filter](EncodeZscale.html) and [Chroma Siting](ChromaSiting.html) for the measurements.

| Flag | Description |
| --- | --- |
| **-r 24** | means 24 frames per second for the png files. |
| **-start_number** 1 | The frame sequence starts from frame 1 (defaults to 0) |
| **-i inputfile.%04d.png** | the %04d means the file sequence will be padded to 4 digits, i.e. 0000, 0001, 0002, etc. It is the same syntax supported by the C printf function. |
| **[-frames:v](https://ffmpeg.org/ffmpeg.html#toc-Video-Options) 100** | is optional, but allows you to specify how many frames to encode, otherwise it will encode the entire frame range. There is an obsolete alias flag `-vframes` which will be retired. |
| **-c:v libx264** | use the H.264 encoding library (libx264) |
| **-preset slower** | a reasonably high quality preset, which will run slow, but not terribly slow. |
| **-pix_fmt yuv420p10le** | 4:2:0 10-bit. 10-bit avoids most of the banding of 8-bit at a similar file size. Safari, Chrome and Firefox played 10-bit H.264 in our tests on macOS; other platforms have not been retested, so if a file has to play everywhere use `-pix_fmt yuv420p` (8-bit). See [H.264 Bitdepth](Encodeh264.html#h264-bitdepth). For better quality in RV or other desktop tools use `-pix_fmt yuv444p10le`. |
| **-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1** | The color tags for the file: limited range (64-940 at 10-bit), BT.709 matrix, BT.709 primaries and the sRGB transfer function. The filter chain already sets all four (see below), so these are not needed, but they are harmless. Do not rely on them alone: before FFmpeg 7.1 they do not change the conversion, and from 7.1 `-color_primaries` and `-color_trc` are ignored. See [FFmpeg Version Changes](FFmpegChanges.html). |
| **-movflags +faststart** | `faststart` reorganizes the MP4 file so that it doesn't have to read the whole file to start playback, useful for streaming. It can add a second or so to do this, since it does require re-writing the file. |

**-vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1"** converts the RGB images to Y'CbCr with the zscale filter, then labels the result:

| Setting | Description |
| --- | --- |
| *(no input settings)* | zscale reads the input from the frames: RGB images (PNG, TIFF, DPX, EXR) are always full range, and JPEG and video sources carry their own tags. Only describe the input for a source with no tags; see [Sources without tags](EncodeZscale.html#sources-without-tags). |
| **matrix=709** | convert to Y'CbCr with the BT.709 matrix, and tag the frames as BT.709. |
| **range=limited** | the outgoing video uses the limited (studio) range, which is the standard for web playback. |
| **filter=lanczos** | the filter used to subsample the chroma to 4:2:0 (zscale's default, `bilinear`, is softer). |
| **setparams=color_primaries=bt709:color_trc=iec61966-2-1** | tag the frames with the BT.709 primaries and sRGB transfer function. This does not change the pixels; the encoder copies the tags into the file. |

Setting the matrix is the important part. Without a filter that sets it, FFmpeg before 7.1 converts with the BT.601 matrix, a standard definition spec from the last century, and not suitable for sRGB or HD displays. From 7.1, `-colorspace bt709` on its own does switch the conversion to BT.709, but through libswscale, and the primaries and transfer function are lost. The filter chain above gives the same, correct, result on every version we tested.

The input side is deliberately left to zscale. Earlier versions of this page forced it (`in_color_matrix=bt709`), which made no difference to RGB images but gave JPEG sequences a visible hue and saturation shift, because JPEGs are BT.601; forcing the input range to full does the same kind of damage to video sources. See [Sources without tags](EncodeZscale.html#sources-without-tags).

Separately, if you are converting from exr's in other colorspaces, **please use [OCIO](https://opencolorio.org/) to do the color space conversions.** [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) is an excellent open-source tool for this. But there is now also an OCIO filter for FFmpeg (see [FFmpeg OCIO Filter](FfmpegOcio.html)).

For more details see:

* [H.264 Encoding](Encodeh264.html)
* [Y'CbCr Conversion](ColorPreservation.html#yuv)
* [Browser color issues](WebColorPreservation.html)

## H.264 Encoding directly from EXRs with the OCIO filter

From FFmpeg 8.1, the [OCIO filter](FfmpegOcio.html) can apply the color management inside FFmpeg, so you can encode
straight from scene-linear EXRs without writing intermediate PNG or TIFF files:

```console
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1 # Or the path to your own config.
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.exr -pix_fmt yuv420p10le \
        -vf "ocio=input=ACEScg:display=sRGB - Display:view=ACES 1.0 - SDR Video:format=rgb48,format=rgb48le,zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
        -frames:v 100 -c:v libx264 -preset slower -crf 18 \
        -movflags +faststart outputfile.mp4
```

| Setting | Description |
| --- | --- |
| **ocio=input=ACEScg** | The color space of the EXRs, as named in your OCIO config. |
| **display=sRGB - Display:view=ACES 1.0 - SDR Video** | The display and view transform, as you would pick them in a review tool. |
| **format=rgb48** | OCIO writes 16-bit RGB, which `zscale` then converts to Y'CbCr. |
| **format=rgb48le** | Changes nothing, but works around a crash in the FFmpeg 9.0 release when `zscale` directly follows the OCIO filter. |
| **zscale=...,setparams=...** | The same conversion and tags as the [command above](#h264-encoding-from-an-image-sequence-for-web-review). `setparams` matters even more here: FFmpeg tags EXR frames as linear, and the OCIO filter does not change the tags. |

This needs an FFmpeg built with OCIO (`ffmpeg -filters | grep ocio`); the [Conan recipes](conan/README.html)
in this repository build one. On FFmpeg 8.1, 9.0.2 and 9.1, the result matched converting the same frames with
`oiiotool --ociodisplay` and then using the command above, to within 1 code value at 10-bit.

For more details, including HDR, resizing, and slates and burn-ins, see [FFmpeg OCIO Filter](FfmpegOcio.html).

## ProRes 422 encoding with FFmpeg

Unlike H.264 and DNxHD, ProRes is a reverse-engineered codec. However, in many cases ffmpeg can produce adequate results. There are a number of codecs, we recommend the prores_ks one. If you are running on MacOS we would recommend using [prores_videotoolbox](EncodeProres.html#prores_videotoolbox) which is using the official Apple ProRes library and is hardware accelerated.

<!---
name: test_proresquickstart
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 4
     - assert: less
       value: mean_error_10bit
       less: 0.8
     - assert: less
       value: max_error_10bit
       less: 13
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
    -pix_fmt yuv422p10le -frames:v 100 \
    -c:v prores_ks -profile:v 3 -vendor apl0 outputfile.mov
```

| Flag | Description |
| --- | --- |
| **-vf "zscale=...,setparams=..."** | Convert to BT.709 Y'CbCr and tag it, as for [H.264 above](#h264-encoding-from-an-image-sequence-for-web-review). ProRes takes its color tags from the frames, so no `-color_*` flags are needed. |
| **-profile:v 3** | ProRes 422 HQ; see the [profile list](EncodeProres.html#prores_ks-profile) |
| **-pix_fmt yuv422p10le** | Convert to 10-bit Y'CbCr 4:2:2 |
| **-vendor apl0** | Treat the file as if it was created by the Apple ProRes encoder (even though it isn't), helps some tools correctly read the Quicktime |

For ProRes 4444 (4:4:4, optionally with alpha), use `-profile:v 4444` with `-pix_fmt yuv444p10le`
(`yuva444p10le` for alpha); see the [ProRes](EncodeProres.html) page.

For more details see:

* [ProRes](EncodeProres.html)
* [Y'CbCr Conversion](ColorPreservation.html#yuv)

## Other codecs and workflows

* For other codecs (DNxHR for Avid, AV1 and VP9 for the web, OpenAPV, HTJ2K) see [Codec Comparisons](Encoding.html),
  which starts with which codec to use for which job.
* [Encoding Overview](EncodingOverview.html) walks through the whole pipeline, from EXRs to a tagged movie.
* If a command gives different results on another FFmpeg version, see [FFmpeg Version Changes](FFmpegChanges.html).
