---
layout: default
title: Resizing
nav_order: 4.5
parent: Encoding Overview
---

# Resizing

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

**We recommend resizing outside FFmpeg, or in linear light.** Shrinking an image averages neighbouring pixels. Image
code values are gamma-encoded, not proportional to light, so averaging them gives the wrong brightness: a fine
black-and-white pattern gives off half the light of white, which is code 188 in sRGB, but averaging the codes gives
128, which is much darker. Every resize filter in FFmpeg and in `oiiotool` works on the values it is given, so unless
the image is converted to linear light first, fine detail comes out too dark.

## How much it matters

We measured this by shrinking three sRGB images to a quarter of their size, and comparing each result with a
reference that averages each 4×4 block of pixels in linear light (the right brightness). The table gives the mean
difference from the reference in 8-bit code values; negative is darker. The results were the same on FFmpeg 6.1.6,
8.1 and 9.0.2, with `oiiotool` 3.1.

| Resize | Zone plate | Test chart | Animation |
| :--- | ---: | ---: | ---: |
| `scale`, any filter | −30.7 | −5.7 | −0.5 |
| `zscale`, any filter | −30.2 | −5.3 | −0.2 |
| `oiiotool --resize` | −30.2 | −5.3 | −0.2 |
| `zscale`, lanczos, in linear light | 0.0 | +0.7 | −0.1 |
| `oiiotool`, lanczos3, in linear light | 0.0 | +0.7 | −0.1 |

- The filter makes no difference to the brightness: only resizing in linear light fixes it.
- It matters most for fine, high-contrast detail: test charts, text, thin lines, hair and fabric, CG and graphics.
  The zone plate's finest rings, which should shrink to an even grey, come out 30 codes too dark. On the animation
  frame, which is mostly flat colour, it is under one code.
- `zscale` in linear light and `oiiotool` in linear light give practically the same result.

See the [resize comparison](https://encode.taurich.org/tests/resize-compare/compare.html#src=zoneplate&a=source&b=scale_bicubic&mode=wipe&zoom=0)
to wipe between them; the pixel probe shows the zone plate's outer rings at 127 after FFmpeg's default resize, and 161
in linear light, against 162 in the reference.

## Resizing in linear light

The best place to resize is before FFmpeg, in your compositing or finishing tool, or with `oiiotool`, which reads
sRGB-encoded images, converts them to linear, resizes and converts back:

```console
oiiotool --frames 1-200 input.%04d.png --colorconvert srgb_tx lin_rec709 --resize:filter=lanczos3 1920x1080 \
    --colorconvert lin_rec709 srgb_tx -d uint16 -o resized.%04d.png
```

`zscale` can do the same inside FFmpeg: convert to linear light, resize in floating point, convert back, then do
the usual conversion to Y'CbCr, all in one filter chain (tested on FFmpeg 6.1.6 and 9.0.2):

```console
ffmpeg -framerate 24 -i input.%04d.png -c:v libx264 -pix_fmt yuv420p \
    -vf "zscale=primariesin=709:primaries=709:transferin=iec61966-2-1:transfer=linear,format=gbrpf32le,zscale=w=1920:h=1080:filter=lanczos,zscale=primariesin=709:primaries=709:transferin=linear:transfer=iec61966-2-1,zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
    -color_range tv -colorspace bt709 output.mp4
```

This assumes the source is sRGB-encoded (`iec61966-2-1`); for a source with another curve, change `transferin` and
`transfer` to match. Kept in one chain, the overshoot of the lanczos filter at bright edges survives into the
headroom above limited-range white rather than being clipped.

## Resizing scene-linear (HDR) sources

A scene-linear source, such as an ACES OpenEXR, has a better place still to resize: before the view transform (the
display rendering, such as the ACES 2.0 SDR view), in scene-linear light. That averages the light in the scene, as a
lower-resolution camera would see it. After the view transform the highlights have already been tone mapped, so even
a resize in display-linear light gets them wrong.

We measured this on an HDR frame, Netflix's Sparks (ACES2065-1 OpenEXR, with highlights up to about 200 times scene
white), shrunk by 4 and viewed through OCIO's "ACES 2.0 - SDR 100 nits (Rec.709)" view for sRGB, against a
reference that averages each 4×4 block in scene-linear light and then applies the view. Measured over the part of the
frame with the most highlights, in 8-bit code values; the same on FFmpeg 8.1 and 9.0.2, with `oiiotool` 3.1 and
OCIO 2.5:

| Resize | Brightness | 99th percentile error |
| :--- | ---: | ---: |
| After the view transform, on the display values (`scale`, `zscale` or `oiiotool`, any filter) | −3.3 | 63 |
| After the view transform, in display-linear light (lanczos) | −2.5 | 51 |
| Before the view transform, in scene-linear light: lanczos | −1.5 | 105 |
| Before the view transform, in scene-linear light: mitchell | +0.8 | 69 |
| Before the view transform, in scene-linear light: gaussian | +5.5 | 109 |

- Resizing after the view transform makes the highlights and their surroundings too dark, whatever the filter.
- With highlights this bright, the filter matters much more than for SDR images. Lanczos's negative lobes ring around
  each spark, leaving dark halos, which give the worst errors in the table; a wide filter such as gaussian spreads
  each highlight's energy over its neighbours, which after the tone map shows as bloom. A moderate filter such as
  mitchell is a good compromise.
- FFmpeg can do this too, and gives the same result as `oiiotool`: `zscale` resizes the EXR, then the `ocio` filter
  applies the view.

See the [HDR examples](https://encode.taurich.org/tests/resize-compare/compare.html#src=sparks&a=zscale_lanczos&b=hdr_oiio_scene_mitchell&mode=wipe&zoom=0)
in the resize comparison.

With `oiiotool`:

```console
oiiotool --frames 1-200 input.%04d.exr --resize:filter=mitchell 1920x1080 \
    --ociodisplay:from=ACES2065-1 "sRGB - Display" "ACES 2.0 - SDR 100 nits (Rec.709)" -d uint16 -o resized.%04d.png
```

With FFmpeg 8.1 or later built with the `ocio` filter (see [FFmpeg OCIO Filter](FfmpegOcio.html)), resizing,
the view transform and the conversion to Y'CbCr in one command; `filter=bicubic:param_a=0.3333333:param_b=0.3333333`
is the mitchell filter. `OCIO=ocio://default` selects OCIO's built-in config; use your own config as usual:

```console
OCIO=ocio://default ffmpeg -framerate 24 -i input.%04d.exr -c:v libx264 -pix_fmt yuv420p \
    -vf "zscale=w=1920:h=1080:filter=bicubic:param_a=0.3333333:param_b=0.3333333,format=gbrpf32le,ocio=input=ACES2065-1:display=sRGB - Display:view=ACES 2.0 - SDR 100 nits (Rec.709):format=rgb48,format=rgb48le,zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
    -color_range tv -colorspace bt709 output.mp4
```

{: .warning }
> Put `zscale` straight after the input. FFmpeg 8.0 and later decode half-float EXRs as half-float; `zscale` resizes
> those directly, but a `format=gbrpf32le` in front of it makes FFmpeg convert them with libswscale, which clamps
> every value to 0–1 and loses the highlights before the resize (on the Sparks frame, the brightest value falls from
> about 227 to 1.16). See [FFmpeg Version Changes](FFmpegChanges.html#exr-half-float-80).

## Choosing a filter

The filter controls sharpness and artefacts, in linear light or not. If you are processing live action, the
consensus is typically lanczos. Animation and motion graphics may suffer from lanczos's ringing (halos at hard edges;
see the [animation example](https://encode.taurich.org/tests/resize-compare/compare.html#src=animation&a=scale_area&b=scale_lanczos&mode=toggle&zoom=4)),
but you really should compare the results.

| Filter | `scale` | `zscale` | `oiiotool` | Character |
| :--- | :--- | :--- | :--- | :--- |
| Lanczos | `flags=lanczos` | `filter=lanczos` | `lanczos3` (its default for shrinking) | Sharp; can ring at hard edges |
| Spline | `flags=spline` | `filter=spline36` | | Sharp and smooth |
| Bicubic | `flags=bicubic` (the default) | `filter=bicubic` | `catmull-rom`, `mitchell` | In between |
| Bilinear | `flags=bilinear` | `filter=bilinear` (the default) | `triangle` | Soft |
| Area / box | `flags=area` | | `box` | Softest, no ringing |
| Nearest | `flags=neighbor` | `filter=point` | | No filtering: fine detail aliases badly. Not for resizing |

- [Comparison gallery of image scaling algorithms - Wikipedia](https://en.wikipedia.org/wiki/Comparison_gallery_of_image_scaling_algorithms)
- [Cambridge in Color - resizing for web and email](https://www.cambridgeincolour.com/tutorials/image-resize-for-web.htm)
- [ImageMagick Examples -- Resampling Filters](https://www.imagemagick.org/Usage/filter)
