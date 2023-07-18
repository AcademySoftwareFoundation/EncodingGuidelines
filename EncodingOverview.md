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

## Easy install of OCIO/OIIO/FFmpeg

Different approaches for getting started include: [anaconda](https://www.anaconda.com/) you will also need to download the ACES OCIO configuration files from: https://github.com/colour-science/OpenColorIO-Configs
```
conda create --name aswf-ffmpeg
conda activate aswf-ffmpeg
conda install -c conda-forge py-openimageio
pip install PyYAML pillow
```
This should give you py-openimageio, openimageio and ffmpeg-4.4

TODO - Provide other approaches for quickly getting going (e.g. vcpkg)

## Quick introduction to color conversion using oiiotool

```
export OCIO=~/git/OpenColorIO-Configs/aces_1.2/config.ocio # Or wherever your OCIO is.
oiiotool --framepadding 5 --frames 1-100 sourcefilename_acescg.#.exr --resize 1920x0 \
       --colorconvert acescg srgb --dither -o outputimage.#.png
```

| --- | --- |
| --frames 1-100 | The frame range of the source media. |
| --framepadding 5 | Set the framepadding to 5 (i.e. outputimage.00001.tif) |
| [--resize 1920x0](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-resize) | Resize the image so that the width is 1920 wide, and adjust the height so that the aspect ratio stays the same. (Note you may want to use [--fit](https://openimageio.readthedocs.io/en/master/oiiotool.html?highlight=resize%20filter#cmdoption-fit) too). This will use the lanczos3 filter for decreasing resolution, and the blackman-harris filter for increase resolution. |
| --colorconvert acescg srgb | Do a colorspace convert from ACEScg to sRGB. (See the autocc flag below)|
| --dither |  Adding a dither process when writing to an 8-bit file |


Other flags you might want to use include:

| --- | --- |
| --missingfile checker | If a frame is missing, put a checkboard frame in its place. |
| --threads 2 | If you want to limit the number of threads the oiiotool process consumes, the default is as many threads as there are cores present in the hardware |
| --autocc | Turns on automatic color space conversion,

The above will work well for many of the h264 files, but for generating movies with an extended bit depth (8-16), you may want to do:
```
export OCIO=~/git/OpenColorIO-Configs/aces_1.2/config.ocio # Or wherever your OCIO is.
oiiotool --framepadding 5 --frames 1-100 sourcefilename_acescg.#.exr --resize 1920x0
         --colorconvert acescg srgb -d uint16 -o outputimage.#.png
```

Adding the `-d uint16` flag forces the intermediate file format to be 16-bit, rather than the 8-bit default. Note, we have also removed the dither flag.

## Image resizing.

There are a couple of gotchas with image resizing to watch out for:
   * A number of the encoders require that the resulting movie file be a factor of 2, there isnt a direct way to do this in oiiotool, you would need to read the source image file to determine the right output scale.
   * Watch for filter options, if you choose to do the filtering in ffmpeg, it defaults to bicubic, which is not a great choice for downrezing image formats. For reasons why lancozs is prefered, see:
      * [https://legacy.imagemagick.org/Usage/filter/](https://legacy.imagemagick.org/Usage/filter/)
      * [https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm](https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm)


## See Also.
The following utility - [https://github.com/jedypod/generate-dailies](https://github.com/jedypod/generate-dailies) calls openimageio directly in python to do the image conversion, exporting the resulting file directly to ffmpeg. It has a nice configuration file for text overlays and ffmpeg configuration that is worth looking at too.
