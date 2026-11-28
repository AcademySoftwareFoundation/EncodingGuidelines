---
layout: default
nav_order: 1.5
title: Preparing Frames with oiiotool
parent: Encoding Overview
---

# Preparing Frames with oiiotool

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

{: .highlight }
> Do the color management (scene-linear EXR to display) with [OCIO](https://opencolorio.org/), in a tool such as
> [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) or Nuke, and write 16-bit PNG or TIFF
> frames for FFmpeg to encode. From FFmpeg 8.1 you can instead do it inside FFmpeg with the
> [OCIO filter](FfmpegOcio.html).

## Why do the color management first

FFmpeg's own color handling is designed for video standards, not for scene-linear VFX sources. We recommend doing
any color space conversion with OCIO, either in a tool such as Nuke or `oiiotool`, or with FFmpeg's
[OCIO filter](FfmpegOcio.html) (FFmpeg 8.1 or later). We recommend the ACES configuration whenever possible, since
it gives a good baseline for color space conversion. We mention Nuke a number of times, but many other tools also
do this conversion well using OCIO.

When the conversion is done outside FFmpeg, an intermediate file is written out, such as PNG, TIFF or DPX, for FFmpeg
to read as an [image sequence](FfmpegInputs.html). FFmpeg then only has to do the
[RGB to Y'CbCr conversion](ColorPreservation.html) and the encode.

Hint: by default the Nuke PNG writer uses slow compression, which adds time that is unnecessary for an intermediate
file. The Nuke SDK includes the source for the PNG writer, so it is possible to disable it, but switching to TIFF has
the same result.

## Converting with oiiotool

```console
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1 # A built-in config (OCIO 2.2 or newer), or the path to your own config.
oiiotool --parallel-frames --framepadding 5 --frames 1-100 sourcefilename_acescg.#.exr --resize:highlightcomp=1 1920x0 \
       --ociodisplay "sRGB - Display" "ACES 1.0 - SDR Video" -d uint16 --cicp "1,13,0,1" -o outputimage.#.png
```

| Flag | Description |
| --- | --- |
| `--parallel-frames` | Process several frames at once rather than one after another. In our tests (24 UHD EXRs to HD PNGs, Apple M2) it was 3.7 times faster, with identical pixels. |
| `--frames 1-100` | The frame range of the source media. |
| `--framepadding 5` | Set the frame padding to 5 (i.e. outputimage.00001.png) |
| [`--resize:highlightcomp=1 1920x0`](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-resize) | Resize the image so that the width is 1920 wide, and adjust the height so that the aspect ratio stays the same. (Note you may want to use [`--fit`](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-fit) too). This uses the lanczos3 filter for decreasing resolution, and the blackman-harris filter for increasing it. The resize is done before the view transform, in scene-linear light; `highlightcomp=1` compresses values above 0.18 before filtering and expands them afterwards, which stops lanczos leaving dark halos around bright highlights, at the cost of slightly dimmer highlights and fine detail. Resizing in a log space such as ACEScct is the other common choice; see [Downscaling](Resizing.html#scene-linear-openexrs). |
| `--ociodisplay "sRGB - Display" "ACES 1.0 - SDR Video"` | Apply the ACES display and view transform for an sRGB monitor, as a review tool would. |
| `-d uint16` | Write 16-bit files rather than the 8-bit default. 16-bit intermediates make the RGB to Y'CbCr conversion more accurate, even for 8-bit encodes. |
| `--cicp "1,13,0,1"` | Tag the PNG files as BT.709 primaries with the sRGB transfer function (see [below](#tagging-the-frames-with---cicp)). |

To convert between color spaces without a view transform, use `--colorconvert` instead, e.g.
`--colorconvert acescg srgb`. If you have to write 8-bit files, add `--dither`, and leave out `-d uint16`.

## Tagging the frames with `--cicp` {#tagging-the-frames-with---cicp}

`--ociodisplay` changes the pixels, but does not tag the file with the display it converted to: in our tests
(OpenImageIO 3.1.12) its PNG files had no color chunks at all, so FFmpeg reads them as untagged. `--cicp` writes a
PNG `cICP` chunk, the same four [ITU-T H.273](https://www.itu.int/rec/T-REC-H.273) code points that video files use
(primaries, transfer, matrix, full range), which FFmpeg reads as the frame's primaries and transfer.

A PNG with no color chunks has no defined color space, and tools fill the gap differently: browsers and most image
viewers display it as sRGB, and OpenImageIO reports it as sRGB when it reads it back, but FFmpeg reports the
primaries and transfer function as unknown. The sRGB guess is wrong for frames converted for a Rec.1886 or PQ
display, which is when tagging matters most. An encode that relies on the frames for its tags, rather than on
`setparams`, then gets no primaries or transfer function, and in MOV/MP4 no `colr` atom at all.

| Display | `--cicp` |
| :--- | :--- |
| sRGB | `"1,13,0,1"` |
| Rec.1886 / Rec.709 | `"1,1,0,1"` |
| HDR, Rec.2100 PQ | `"9,16,0,1"` |

The matrix is `0` (RGB) and the range `1` (full), since the frames are RGB.

The tag does not change the pixels or the conversion to Y'CbCr, which was identical with and without it. What it
changes is the tags on the movie: on FFmpeg 6.1.6 and 9.0.2, an H.264 encoded from the tagged frames was tagged
BT.709/sRGB, while one encoded from the untagged frames had no primaries or transfer function. The `setparams` in
the [Encoding Cheatsheet](Quickstart.html) commands sets them either way, so it is not essential there, but it means
the frames describe themselves to any tool that reads them.

Apart from `--ociodisplay`, OpenImageIO writes `sRGB`, `gAMA` and `cHRM` chunks to PNG files by default, including
after `--colorconvert acescg srgb`, which is correct. But it also writes them when nothing was converted: an EXR
written straight to PNG is still scene-linear, but tagged sRGB, and FFmpeg reads it as BT.709/sRGB. So a PNG
tagged sRGB is not evidence that the color conversion was done; check the command that made it.

Other flags you might want to use include:

| Flag | Description |
| --- | --- |
| `--missingfile checker` | If a frame is missing, put a checkerboard frame in its place. |
| `--threads 2` | If you want to limit the number of threads the oiiotool process consumes, the default is as many threads as there are cores present in the hardware. This also limits `--parallel-frames`. |
| `--autocc` | Turns on automatic color space conversion: input files are converted to the scene-linear working space when they are read, and output files to the color space implied by their name or format. |

{: .note }
A number of encoders require the width and height of the movie to be a multiple of 2. There isn't a direct way to do
this in oiiotool; you need to read the source image size to work out the right output size, or round it in FFmpeg
(see [Keeping the image height a multiple of 2](OtherFfmpegArgs.html#keeping-the-image-height-a-multiple-of-2)).

## Building OCIO, OIIO and FFmpeg

* The Docker build files in [docker/rocky-ffmpeg-8.1](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/tree/main/docker/rocky-ffmpeg-8.1).
* The Conan recipes in the [conan](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/tree/main/conan) directory, which build FFmpeg with OCIO and zimg (`zscale`) support on macOS, Linux and Windows.

## See also

* [generate-dailies](https://github.com/jedypod/generate-dailies) calls OpenImageIO directly in Python to do the
  image conversion, and sends the result straight to FFmpeg. It has a nice configuration file for text overlays and
  FFmpeg settings that is worth looking at too.
