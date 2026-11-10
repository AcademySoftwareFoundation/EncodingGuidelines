---
layout: default
nav_order: 3
title: Encoding Overview
has_children: true

---

# Media Encoding with ffmpeg  <a name="encodestart"></a>

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

We will break the encoding process into three parts:

1. [The RGB to YCbCr conversion](ColorPreservation.html)
2. [The encoding process itself](Encoding.html)
3. [Metadata tagging for web browsers](WebColorPreservation.html)

## Color space conversion  <a name="Color-space-conversion"></a>

FFmpeg is not a great tool for colorspace conversion. We recommend that any color space conversion be done using tools such as [Nuke](https://www.foundry.com/products/nuke-family/nuke) or [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) using [OCIO](https://opencolorio.org/). We strongly recommend using the ACES configuration whenever possible, since it provides a good baseline for colorspace conversion. Note, we may mention the use of Nuke a number of times, there are now a large number of 3rd party tools that will also do great at this color space conversion using OCIO.

Typically, we would assume that an intermediate file would get written out, such as PNG, TIFF or DPX for processing in ffmpeg.

Hint: by default the nuke PNG writer will have the slow compression enabled, this does add a little time that is unnecessary for the sort of intermediate file we are using. In the nuke SDK they do provide the source for the PNG writer, so it is possible to get this disabled. However, you may find that switching to TIFF will have the same result.

## Building OCIO/OIIO/FFmpeg

Two options for building ffmpeg include:

* The Docker build files in [docker/rocky-ffmpeg-8.1](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/tree/main/docker/rocky-ffmpeg-8.1).
* The Conan recipes in the [conan](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/tree/main/conan) directory, which build ffmpeg with OCIO support on macOS, Linux and Windows.

## Quick introduction to color conversion using oiiotool

```console
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1 # Or wherever your OCIO is, this is using a builtin OCIO config, with OCIO 2.2 or newer.
oiiotool --framepadding 5 --frames 1-100 sourcefilename_acescg.#.exr --resize 1920x0 \
       --colorconvert acescg srgb --dither -o outputimage.#.png
```

| Flag | Description |
| --- | --- |
| `--frames 1-100` | The frame range of the source media. |
| `--framepadding 5` | Set the framepadding to 5 (i.e. outputimage.00001.png) |
| [`--resize 1920x0`](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-resize) | Resize the image so that the width is 1920 wide, and adjust the height so that the aspect ratio stays the same. (Note you may want to use [`--fit`](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-fit) too). This will use the lanczos3 filter for decreasing resolution, and the blackman-harris filter for increase resolution. |
| `--colorconvert acescg srgb` | Do a colorspace convert from ACEScg to sRGB. (See the `--autocc` flag below) |
| `--dither` | Adding a dither process when writing to an 8-bit file |

Other flags you might want to use include:

| Flag | Description |
| --- | --- |
| `--missingfile checker` | If a frame is missing, put a checkerboard frame in its place. |
| `--threads 2` | If you want to limit the number of threads the oiiotool process consumes, the default is as many threads as there are cores present in the hardware |
| `--autocc` | Turns on automatic color space conversion: input files are converted to the scene-linear working space when they are read, and output files to the color space implied by their name or format. |

The above will work well for many of the h264 files, but for generating movies with a higher bit depth (10-bit or more), you may want to do:

```console
export OCIO=~/git/OpenColorIO-Configs/aces_1.2/config.ocio # Or wherever your OCIO is.
oiiotool --framepadding 5 --frames 1-100 sourcefilename_acescg.#.exr --resize 1920x0 \
         --colorconvert acescg srgb -d uint16 -o outputimage.#.png
```

Adding the `-d uint16` flag forces the intermediate file format to be 16-bit, rather than the 8-bit default. Note, we have also removed the dither flag.

## Image resizing

There are a couple of gotchas with image resizing to watch out for:

* A number of the encoders require that the width and height of the resulting movie be a multiple of 2, there isn't a direct way to do this in oiiotool, you would need to read the source image file to determine the right output scale.
* Watch for filter options, if you choose to do the filtering in ffmpeg, it defaults to bicubic, which is not a great choice for downrezing image formats. For reasons why lanczos is preferred, see:
  * [https://legacy.imagemagick.org/Usage/filter/](https://legacy.imagemagick.org/Usage/filter/)
  * [https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm](https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm)

## See Also

The following utility - [https://github.com/jedypod/generate-dailies](https://github.com/jedypod/generate-dailies) calls openimageio directly in python to do the image conversion, exporting the resulting file directly to ffmpeg. It has a nice configuration file for text overlays and ffmpeg configuration that is worth looking at too.
