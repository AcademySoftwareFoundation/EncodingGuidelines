---
layout: default
title: zscale Conversion
nav_order: 5.7
parent: Encoding Overview
---

# FFmpeg zscale Options

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

`zscale` is FFmpeg's interface to the [zimg](https://github.com/sekrit-twc/zimg) library. For converting image
sequences to Y'CbCr movies it is the converter we recommend, in preference to `scale` (libswscale), because in
our tests it was the only one that was correct by default:

| | `zscale` | `scale` (libswscale) |
| :--- | :--- | :--- |
| White level, 10-bit or higher RGB to limited range | 940 at 10-bit, as specified | 943 at 10-bit, 3774 at 12-bit, on every version up to 9.x |
| Chroma siting, 4:2:2 and 4:2:0 | Co-sited, as professional 4:2:2 and H.264/HEVC/AV1 expect | Centred by default; co-sited only with two extra options |
| Scene-linear (float) EXR | Handled, including values above 1.0 | Clamped to 0.0 - 1.0 |
| Accuracy against the ideal conversion | Exact in all our tests (8, 10 and 12-bit; 4:4:4, 4:2:2, 4:2:0) | Up to 4 code values off at 10-bit, 14 at 12-bit |

See [FFmpeg Version Changes](FFmpegChanges.html#libswscale-white-level-for-high-bit-depth-input),
[Chroma Siting](ChromaSiting.html) and [FFmpeg OCIO Filter](FfmpegOcio.html) for the measurements. libswscale is
still useful for resizing, and when `zscale` is not available; see [Ffmpeg Scaling Options](EncodeSwsScale.html).

## Availability

`zscale` needs FFmpeg built with zimg (`--enable-libzimg`). Check with:

```console
ffmpeg -filters | grep zscale
```

The Docker builds in this repository enable it, and the Conan build enables it by default. Many distribution
and static builds include it, but not all.

## Recommended commands

RGB image sequence to BT.709 Y'CbCr, on every FFmpeg version we tested (6.0 to 9.0):

```console
ffmpeg -i input.%06d.dpx \
  -vf "zscale=rangein=full:matrix=709:range=limited,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
  -c:v prores_ks -profile:v 4444xq -pix_fmt yuv444p10le \
  output.mov
```

* `rangein=full` says the RGB source is full range, `matrix=709` and `range=limited` are the output.
* `zscale` tags its output frames with the matrix and range, which the encoder copies into the file.
* `setparams` adds the primaries and transfer, which `zscale` only sets if you ask it to convert them (see
  [below](#what-zscale-tags)).
* `-pix_fmt` sets the output format; `zscale` converts straight to it. Use the codec's own format (for example
  `yuv422p10le` for ProRes 422 or DNxHR HQX, `yuv420p10le` for H.264/HEVC).
* For H.264 or HEVC in an MP4, add `-movflags +write_colr`.

The four `-color_*` flags (`-color_range tv -colorspace bt709 -color_primaries bt709 -color_trc ...`) are not
needed with this filter chain, but are harmless if you prefer to keep them; see
[FFmpeg Version Changes](FFmpegChanges.html#recommended-commands).

For HDR (BT.2020, PQ), the same pattern with `matrix=2020_ncl` and
`setparams=color_primaries=bt2020:color_trc=smpte2084`; see
[HDR and -x265-params](FFmpegChanges.html#hdr-and--x265-params).

## What zscale tags

The encoder takes its colour tags from the frames it receives, so what `zscale` sets on its output frames is what
ends up in the file:

| Property | Set by `zscale` | Otherwise |
| :--- | :--- | :--- |
| Matrix, range | Always (`matrix=`, `range=`) | |
| Primaries, transfer | Only when converted: give both the input and the output, e.g. `primariesin=709:primaries=709:transferin=iec61966-2-1:transfer=iec61966-2-1` | `setparams` |
| Chroma location | Only when `chromal=` is set | Left unset, which is what you want for 4:2:2 MXF; see [Chroma Siting](ChromaSiting.html#dnxhr-in-mxf) |

So this is equivalent to the recommended command, without `setparams` (tested on 6.0 and 9.0, ProRes):

```console
-vf "zscale=rangein=full:matrix=709:range=limited:primariesin=709:primaries=709:transferin=iec61966-2-1:transfer=iec61966-2-1"
```

## Options

The options that matter for colour conversion (`ffmpeg -h filter=zscale` lists them all). Each has an input
version (`...in`) describing the source, and an output version; the defaults (`input`) mean "the same as the
input frame".

| Option | Short | Input option | What it sets | Default |
| :--- | :--- | :--- | :--- | :--- |
| `matrix` | `m` | `matrixin` / `min` | Y'CbCr matrix: `709`, `2020_ncl`, `170m` (BT.601), `470bg` | input |
| `range` | `r` | `rangein` / `rin` | `limited` or `full` | input |
| `primaries` | `p` | `primariesin` / `pin` | Colour primaries: `709`, `2020`, ... | input |
| `transfer` | `t` | `transferin` / `tin` | Transfer: `709`, `iec61966-2-1` (sRGB), `smpte2084` (PQ), `linear`, ... | input |
| `chromal` | `c` | `chromalin` / `cin` | Chroma location: `left`, `center`, `topleft`, ... | input |
| `filter` | `f` | | Resampling filter, for resizing and for chroma: `point`, `bilinear`, `bicubic`, `spline16`, `spline36`, `spline64`, `lanczos` | `bilinear` |
| `dither` | `d` | | `none`, `ordered`, `random`, `error_diffusion` | `none` |
| `npl` | | | Nominal peak luminance, for linear light conversions | |

An RGB source has no matrix, and full range is the usual case for image sequences, so for encoding the options
you normally need are `rangein=full`, `matrix` and `range`. The chroma location defaults to co-sited for
4:2:2 and 4:2:0, which is correct for professional formats; leave `chromal` unset unless your delivery
specification asks for something else.

## Things to watch

### Make sure zscale is doing the conversion

If the format that follows `zscale` is one it cannot output, FFmpeg quietly lets `zscale` keep its input format
and inserts libswscale afterwards to do the conversion, with all of libswscale's problems. We hit this decoding
Y'CbCr to `rgb48be`: `zscale` only changed the range, and libswscale did the Y'CbCr to RGB conversion.

Converting to the formats encoders use (`yuv422p10le`, `yuv444p10le`, `yuv420p10le`, `gbrp10le` and so on) is
fine. For RGB output, put a planar RGB format straight after `zscale` (for example `format=gbrp16le`). To check,
run with `-v verbose` and look for `auto_scale` lines: anything other than a plain repack (for example
`gbrp16le` to `rgb48be`) means libswscale is converting.

### Decoding untagged Y'CbCr

`zscale=matrixin=709` on Y'CbCr that carries no colour tags (for example raw `.yuv`) can fail with
`no path between colorspaces`. Tag the frames with `setparams` first, then let `zscale` convert:

```console
-vf "setparams=colorspace=bt709:range=tv:color_primaries=bt709:color_trc=bt709,zscale=range=full:chromalin=left,format=gbrp16le"
```

### Geometry

`zscale` resizes (`w`, `h`, `filter`), but does not pad or fit to an aspect ratio, so command lines that combine
scaling with `pad`, `force_original_aspect_ratio` or `setsar` need the colour conversion separated from the
geometry rather than swapping `scale` for `zscale`. Its default filter is `bilinear`; for resizing, choose
`filter=lanczos` or `filter=spline36`. Resizing scene-linear EXR data must be done with `zscale`, not `scale`;
see [FFmpeg OCIO Filter](FfmpegOcio.html).

### Dithering

`zscale` does not dither by default (`dither=none`): conversions are rounded to the nearest code value, which is
what our accuracy tests measured as exact. If you convert a high bit depth source down to 8-bit, consider
`dither=error_diffusion` to avoid banding; we have not tested its effect.
