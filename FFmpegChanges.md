---
layout: default
title: FFmpeg Version Changes
nav_order: 8
---

# FFmpeg Version Changes

FFmpeg changes behaviour between releases, sometimes without any warning, and the same command line can produce
different pixels or different colour tags depending on the version you run it with. This page lists the changes
we have found that affect the recommendations in these guidelines, which versions they apply to, and a set of
commands that give the right result on all of them.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Summary

| Change | Versions | What it means |
| :--- | :--- | :--- |
| [`-colorspace` and `-color_range` drive the RGB to Y'CbCr conversion](#colorspace-flags-71) | 7.1 and later | A plain encode tagged `-colorspace bt709` is now converted with BT.709 instead of BT.601. On a tagged source, `-colorspace` now converts the pixels rather than retagging them. |
| [`-colorspace` and `-color_range` convert, they no longer relabel](#relabelling-a-file) | 7.1 and later | Transcoding a tagged Y'CbCr file with them changes the pixels. To fix a wrong tag, use `setparams`. |
| [`-color_primaries` and `-color_trc` are ignored](#primaries-trc-flags-71) | 7.1 and later | The flags are silently dropped. Use `setparams` to set primaries and transfer. |
| [ProRes writes its colour tags from the frame, not the flags](#prores-colour-tags-come-from-the-frame) | All | With flags only, the MOV `colr` atom and the ProRes frame header can disagree (7.0 and earlier) or both be missing (7.1 and later). |
| [`-x265-params` colour settings only tag the HEVC stream](#hdr-and--x265-params) | All | They do not change the conversion. Without `-colorspace` or a conversion filter, the pixels are BT.601 in a file tagged BT.2020. |
| [Some encoders only accept limited range](#limited-range-encoders-71) | 7.1 and later | FFV1, ProRes, DNxHR, HuffYUV and others: full-range frames are converted back to limited range unless you add `-color_range pc`. |
| [libswscale puts limited-range white too high for high-bit-depth input](#libswscale-white-level-for-high-bit-depth-input) | All, including 9.0 | 10-bit RGB to 10-bit Y'CbCr puts 100% white at 943 instead of 940. Use `zscale`. `scale=...:flags=unstable` (8.1 and later) fixes 4:4:4 only. |
| [libswscale RGB to full-range Y'CbCr is too bright](#libswscale-full-range-80) | 8.0 and later | 10-bit and 12-bit output: luma gain too high, white about 3 code values (10-bit) high. Exact up to 7.1. Use `zscale`. |
| [libswscale Y'CbCr range conversion was 3 code values out](#libswscale-full-range-80) | 7.1 and earlier | Limited to full and full to limited at 10/12-bit. Fixed in 8.0 by the same change. |
| [Half-float EXRs decode as half-float, and converting them clamps](#exr-half-float-80) | 8.0 and later | Asking for 32-bit float through libswscale limits the image to 0.0 - 1.0. Use `zscale`. |
| [PNGs with bad EXIF data no longer decode](#png-exif-81) | 8.1 and later | The whole frame fails, not just the metadata. Seen with PNGs from OpenImageIO 2.4. Remove the EXIF with `exiftool -EXIF=`. |
| [libswscale ignores the chroma location when converting to RGB](#ycbcr-to-rgb) | 9.0 and earlier | Stills from co-sited 4:2:2/4:2:0 (ProRes, DNxHR, H.264) come out with the colour half a pixel to the right. Use `zscale`. |
| [Untagged Y'CbCr is converted to RGB as BT.601](#ycbcr-to-rgb) | All | libswscale assumes BT.601; `zscale` refuses. Give the matrix explicitly. |
| [Chroma location reaches the filter graph](#chroma-location-91) | 9.1 development builds | `-chroma_sample_location`, and the file's chroma location when decoding, now steer libswscale. Untagged files are still taken as centred. |

## Recommended commands

### Every version

This gives correct pixels and correct colour tags, in every place they are stored, on every version we tested
(FFmpeg 6.0 to 9.0), for both ProRes and H.264, and for any source bit depth:

```console
ffmpeg -i input.%06d.dpx \
  -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
  -c:v prores_ks -profile:v 4444xq -pix_fmt yuv444p10le \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
  output.mov
```

* **`zscale=matrix=709:range=limited`** does the RGB to Y'CbCr conversion. Without an explicit
  conversion, 7.0 and earlier convert with BT.601. `zscale` was exact in all our tests; see
  [below](#libswscale-white-level-for-high-bit-depth-input) for why we do not use `scale`. `zscale` also sets the
  matrix and range on its output frames, which is what tags them. `filter=lanczos` sets the resampling filter used for the 4:2:2/4:2:0 chroma (and for any resize). zscale's
  default, `bilinear`, gives softer chroma: on 4:2:0 test charts it left 99th percentile edge errors of 61 code
  values against 46 with `lanczos`. On 4:2:2 the two were within a code value or so on average, with `bilinear`
  very slightly cleaner on hard-edged graphics. The filter makes no difference to the colour accuracy inside flat
  areas, or to the chroma siting.
* **`setparams=color_primaries=bt709:color_trc=iec61966-2-1`** sets primaries and transfer on the frames. This is
  the only way to set them on 7.1 and later.
* **The four `-color_*` flags** turned out to be redundant with this filter chain on every version we tested,
  because the encoder takes its tags from the frames, which `zscale` and `setparams` have already set. They do no
  harm, and make the intent of the command explicit. The exception is full-range output: there `-color_range pc`
  is needed for many encoders; see [Some encoders only accept limited range](#limited-range-encoders-71).

`zscale` needs FFmpeg built with zimg (`--enable-libzimg`). Check with `ffmpeg -filters | grep zscale`. If your
build does not have it, `scale=out_color_matrix=bt709:out_range=tv` followed by
`setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709:range=tv`, plus the four `-color_*`
flags, gives the same tags on every version, but with the libswscale white level error for 10-bit and higher
sources.

### Shorter form

Since the flags are redundant, this is all that is needed. It gave the same results as the command above on every
version we tested (6.0 to 9.0), for ProRes and H.264:

```console
ffmpeg -i input.%06d.dpx \
  -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
  -c:v prores_ks -profile:v 4444xq -pix_fmt yuv444p10le \
  output.mov
```

Do not be tempted to drop `zscale` on 7.1 and later. From 7.1, `-colorspace bt709 -color_range tv` alone does
get the matrix right, but the conversion is then done by libswscale, which puts 100% white at 943 instead of 940
from a 10-bit or 16-bit source (see [below](#libswscale-white-level-for-high-bit-depth-input)). The explicit
`zscale` is what makes it accurate, on every version.

The MOV and MP4 muxers write the `colr` atom by default when the primaries, transfer and matrix are all set, so
`-movflags +write_colr` is not needed (measured on 6.1.6, 7.1.5 and 9.0.2). It was needed up to FFmpeg 4.3: the
default changed in 4.4 (commit `c5b20cfe19`). The flag now only forces a `colr` atom when some of the values are
unspecified.

## How these were tested

* **FFmpeg versions:** 6.0, 7.0, 7.1, 8.0.1, 8.1 (a git build from the 8.1 branch, `N-124257-g73262c9136`; the
  7.1 changes were also confirmed on the 8.1 release) and 9.0.1.
* **Colour tags:** read with `ffprobe`, plus the MOV/MP4 `colr` atom and the ProRes frame header read directly
  from the file.
* **Pixels:** the encoded planes are read without any FFmpeg colour conversion and compared, in code values,
  with the ideal BT.709 and BT.601 conversions computed independently in numpy. The libswscale measurements use
  SMPTE RP 219 reference bars generated from the specification's own Y'CbCr tables, and validated against them;
  see `sourceimages/README.md`.

The scripts are in the repository, and run once per FFmpeg version:

```console
python tests/colour_flags_matrix.py --label 9.0     # once per FFmpeg version
python tests/colour_flags_matrix.py --summarize     # tests/colour-flags-matrix/summary.md
python tests/rgb2ycbcr_accuracy.py --label 9.0
python tests/rgb2ycbcr_accuracy.py --summarize
```

Each script measures whichever `ffmpeg` is on the `PATH` (or `FFMPEG_BIN` and `FFPROBE_BIN`). Run it once per
FFmpeg version with `--label`, then `--summarize` combines the runs into the script's `summary.md`. With a rez
setup that has an `ffmpeg-<version>` package per version, `--rez 6.0 7.0 ...` does both. The scripts need numpy
and the OpenImageIO Python bindings (`requirements.txt`).

The same checks are also in the encoding test framework, which is run on each FFmpeg version (6.1.6, 7.0, 7.1.5,
8.0.1, 8.1, 9.0.2 and a 9.1 development build so far) and reports what changed between versions:
`enctests/test_configs/cicp_flags_tests.yml` (the tag recipes), `chroma_siting_tests.yml`, `decode_tests.yml` and
`decode_siting_tests.yml`. See `enctests/README.md`.

## `-colorspace` and `-color_range` now drive the conversion (7.1) {#colorspace-flags-71}

When an RGB source is encoded to Y'CbCr without a conversion filter, `ffmpeg` inserts its own `scale` filter to
do the conversion. Before 7.1, that conversion always used BT.601, and `-colorspace bt709` only wrote the tag, so
the file said BT.709 but contained BT.601 values. This is the classic "the colours shifted when I encoded" bug.

From 7.1, the encoder's `-colorspace` and `-color_range` are passed into the filter graph as requirements, and
the inserted `scale` converts to them
([commit a850f80e2c](https://github.com/FFmpeg/FFmpeg/commit/a850f80e2c), "fftools/ffmpeg_filter: propagate codec
yuv metadata to filters").

Encoding an untagged RGB PNG to ProRes 4444 with no conversion filter:

| Command line | 7.0 and earlier | 7.1 and later |
| :--- | :--- | :--- |
| No colour flags | BT.601, untagged | BT.601, untagged |
| `-colorspace bt709 -color_range tv` | **BT.601 pixels, tagged BT.709** | BT.709 pixels, tagged BT.709 |
| Explicit `scale` or `zscale` to BT.709 | BT.709 | BT.709 |

Two consequences:

* **The bare encode now gets the matrix right on 7.1 and later, as long as you tag it.** Any example that shows a
  "default" encode giving the wrong colours is only true before 7.1, or with no `-colorspace` at all. It is still
  not fully correct: the conversion is done by libswscale, which puts white at 943 instead of 940 from a 10-bit or
  16-bit source, so use `zscale` as in the recommended commands.
* **On a source that is already Y'CbCr, `-colorspace` now converts.** Before 7.1, transcoding a BT.709 file with
  `-colorspace bt2020nc` just relabelled it, leaving BT.709 pixels tagged as BT.2020. From 7.1 the pixels are
  re-matrixed to BT.2020, and the file still decodes to the same RGB (measured on 6.1.6, 7.0, 7.1.5, 9.0.2 and
  9.1.dev; `-color_range` behaves the same way). Neither is a retag. To change the label without touching the pixels, use `setparams`; see
  [Relabelling a file](#relabelling-a-file).

The inserted `scale` uses libswscale's defaults (bicubic, no `accurate_rnd`). `-sws_flags` still applies to it.

## `-color_primaries` and `-color_trc` are ignored (7.1) {#primaries-trc-flags-71}

From 7.1, `-color_primaries` and `-color_trc` on the output have no effect. The encoder copies all its colour
settings from the frames it receives, and since only matrix and range are passed into the filter graph, the
frames' primaries and transfer (usually "unspecified" for an image sequence) overwrite the values you set. This
follows from [commit 9a7686e545](https://github.com/FFmpeg/FFmpeg/commit/9a7686e545) ("fftools/ffmpeg_mux_init:
apply encoder options manually"), which changed when the options are applied. Before it, the options were applied
after the frame values were copied, so they won. It is still the case in 9.0.

| Command line | 7.0 and earlier | 7.1 and later |
| :--- | :--- | :--- |
| `-color_primaries bt709 -color_trc iec61966-2-1` | Tagged | **Not tagged** (unspecified) |
| `-vf setparams=color_primaries=bt709:color_trc=iec61966-2-1` | Tagged | Tagged |

The same applies when transcoding: a tagged source keeps its own primaries and transfer, and
`-color_primaries`/`-color_trc` cannot change them.

`setparams` sets the values on the frames, so it works on every version and every codec. For H.264 only, the
`h264_metadata` bitstream filter (`-bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=13`) also
sets them, but only in the H.264 stream: the MP4 `colr` atom keeps the unspecified values, so the two disagree,
and on 8.1 and 9.0 `ffprobe` reported the unspecified ones.

## Some encoders only accept limited range (7.1) {#limited-range-encoders-71}

Each encoder in FFmpeg declares the colour ranges it supports. From 7.1 `ffmpeg` passes that list into the filter
graph, together with `-colorspace` and `-color_range` (the same change as
[above](#colorspace-flags-71), [commit a850f80e2c](https://github.com/FFmpeg/FFmpeg/commit/a850f80e2c)). Many
encoders declare limited range only, so if the frames reaching them are full range, `ffmpeg` inserts a libswscale
`scale` and converts them back to limited range, without a warning. The full-range `zscale` in your filter chain is
quietly undone.

Encoders that declare limited range only include FFV1, ProRes (`prores_ks`, `prores_aw`), DNxHD/DNxHR, HuffYUV and
FFVHuff, MagicYUV, JPEG 2000 (`jpeg2000`, `libopenjpeg`), TIFF and MPEG-2. `libx264`, `libx265`, `libsvtav1`,
`libaom-av1`, `libvpx` and the VideoToolbox encoders accept both ranges.

`-color_range pc` tells `ffmpeg` that full range is what you want, and the frames are passed through unchanged.
Encoding 10-bit RGB bars with `zscale=matrix=709:range=full`:

| Encoder | 6.1 | 7.1 and later, no `-color_range` | 7.1 and later, `-color_range pc` |
| :--- | :--- | :--- | :--- |
| FFV1, DNxHR, FFVHuff, MagicYUV | Full range | **Converted to limited range** | Full range |
| ProRes (`prores_ks`) | Full range | **Converted to limited range** | Full range pixels, but see below |
| `libx264` | Full range | Full range | Full range |

* With `-color_range pc` the encoder accepts the frames, but it still can only record what its format allows.
  ProRes has no range field, so a full-range ProRes file is not marked as such, and from 8.1 `ffprobe` (and the
  FFmpeg decoder) reports it as limited range. Avoid full range with ProRes and DNxHR unless you control the
  player.
* The inserted conversion is libswscale, so for 10-bit and higher sources it also has the
  [range conversion errors](#libswscale-full-range-80) of the version you run.
* For limited-range output nothing changes: `-color_range tv` is redundant with `zscale=range=limited`, as in the
  recommended commands.

Tested on 6.1.6, 7.1.5 and 9.0.2, reading the pixels back at the stream's own pixel format.

## ProRes colour tags come from the frame

The ProRes encoder (`prores_ks`) writes primaries, transfer and matrix into each frame header from the frame's
own properties, never from the `-color_*` flags. The flags only reach the MOV `colr` atom. A player may read
either. With the flags alone:

| | `colr` atom | ProRes frame header |
| :--- | :--- | :--- |
| 7.0 and earlier | BT.709 | unspecified, so the two disagree |
| 7.1 and later | none written | matrix only |

With `setparams` (or `zscale`, which sets matrix and range on its output frames), both are correct on every
version. On 6.0, `scale` does not set the matrix on its output frames, so with `scale` the `setparams` filter
also needs `colorspace=bt709:range=tv`.

ProRes has no range field. `ffprobe` reports a ProRes stream's range as unknown before 8.1 and as limited (`tv`)
from 8.1; that is a change in what the decoder reports, not in the file.

## libswscale white level for high-bit-depth input

Converting full-range RGB to limited-range Y'CbCr, libswscale (the `scale` filter, and the `scale` that
`ffmpeg` inserts automatically) puts white above the specification value when the source is more than 8 bits.
This has not changed in any version from 6.0 to 9.0:

| Source | Output | `scale` | `scale=...:flags=unstable` (8.1+) | `zscale` | Specification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 8-bit RGB | 10-bit | 940 | 940 | 940 | 940 |
| 10-bit RGB | 10-bit | **943** | 940 (4:4:4 only) | 940 | 940 |
| 10-bit RGB | 12-bit | **3770** | 3760 (4:4:4 only) | 3760 | 3760 |
| 16-bit RGB | 12-bit | **3774** | 3760 (4:4:4 only) | 3760 | 3760 |

* The error is in luma and grows with brightness and bit depth: up to 3 code values at 10-bit and 14 at 12-bit.
* **8-bit sources are not affected**, which is why tests with 8-bit images do not show it.
* `-sws_flags spline+accurate_rnd+full_chroma_int` makes no difference to it.
* `flags=unstable` (8.1 and later) fixes it for 4:4:4 output only. For 4:2:2 and 4:2:0, the output is identical
  to plain `scale`.
* `zscale` was exact for every combination we tested: 8-, 10- and 16-bit RGB to 8-, 10- and 12-bit Y'CbCr, in
  4:4:4, 4:2:2 and 4:2:0.

See [FFmpeg Scaling Options](EncodeSwsScale.html#colour-range-accuracy-prefer-zscale-for-range-conversions) for
more on the cause.

## libswscale full-range conversions changed in 8.0 {#libswscale-full-range-80}

[Commit 384fe39623](https://github.com/FFmpeg/FFmpeg/commit/384fe39623) ("swscale/range_convert: fix mpeg ranges in
yuv range conversion for non-8-bit pixel formats", first in 8.0) changed libswscale's range conversion for 10-bit
and higher formats. It fixed conversions between limited and full-range Y'CbCr, and broke RGB to full-range Y'CbCr,
which had been exact.

Errors against the ideal BT.709 conversion of the SMPTE bars, in 10-bit code values (white level / largest error):

| Conversion | `scale`, 7.1 and earlier | `scale`, 8.0 to 9.0 | `scale=...:flags=unstable` (8.1+) | `zscale` |
| :--- | :--- | :--- | :--- | :--- |
| 10-bit RGB to 10-bit full-range Y'CbCr | 0 / 0 | **+2.8 / 3** | 0 / 1 | 0 / 0 |
| 10-bit RGB to 12-bit full-range Y'CbCr | -0.75 / 0.75 | **+2.9 / 3** | -0.25 / 0.25 | 0 / 0 |
| 10-bit limited to full-range Y'CbCr | **-3.0 / 3** | 0 / 2 | -0.2 / 2 | 0 / 1 |
| 12-bit limited to full-range Y'CbCr | **-4.0 / 4.25** | -0.25 / 0.75 | -0.25 / 0.75 | -0.25 / 0.75 |
| 10-bit full to limited-range Y'CbCr | **+3.0 / 3** | 0 / 1 | 0.1 / 1 | 0 / 1 |
| 12-bit full to limited-range Y'CbCr | **+2.5 / 2.75** | -0.75 / 0.75 | -0.25 / 0.5 | 0 / 0.5 |

* **RGB to full range, 8.0 and later:** the luma gain is too high. A 10-bit grey of 1019 comes out as 1022 instead
  of 1019, 851 as 854, and the brightest values clip at 1023. The 8.1 fix for the same commit's green tint on greys
  ([ticket 11646](https://trac.ffmpeg.org/ticket/11646)) did not change our results.
  8-bit output is affected less: the largest error went from 1 to 2 (8-bit) code values.
* **Y'CbCr range conversion, 7.1 and earlier:** white was 3 to 4 code values out in both directions. From 8.0 it
  is close to `zscale`, though limited to full at 10-bit still has a mean error about twice `zscale`'s.
* **RGB to limited-range Y'CbCr** (the usual case) is unchanged; see
  [above](#libswscale-white-level-for-high-bit-depth-input).
* `flags=unstable` (libswscale's new conversion code, 8.1 and later) gets close to `zscale` in all of these. We
  tested 4:4:4 only. On the development branch after 9.0, some format pairs (e.g. 10-bit RGB to 12-bit Y'CbCr) log
  "No backend found for operations" and silently fall back to the old code.

`zscale` gave the same results on every version, so it remains the recommendation for any range conversion.

Tested on 6.1.6, 7.1.5, 8.0.1, 8.1 (git build), 9.0.2 and the development branch (N-127508). The tests that
measure this are `color_tests.yml` and `ycbcr_range_tests.yml` in `enctests/test_configs`; they mark the
libswscale results as known issues, so a run on a new version reports whether they have been fixed.

## Half-float EXRs decode as half-float (8.0) {#exr-half-float-80}

FFmpeg 8.0 stopped converting half-float EXRs to 32-bit float in the decoder (commit `0e917389fe`), so they now
decode as `gbrpf16le`. 32-bit float EXRs are still `gbrpf32le`. Measured with an EXR holding -2.0 to 300.0, on 6.1.6, 7.0,
7.1.5, 8.0.1, 8.1, 9.0.2 and a 9.1 development build:

* **From 8.0, asking for 32-bit float clamps.** `-pix_fmt gbrpf32le` now needs a conversion, libswscale does it, and
  the values are limited to 0.0 - 1.0 (-2.0 becomes 0, 300.0 becomes 1). The same command on 7.1.5 and earlier keeps them.
  `format=gbrpf32le` in a filter graph does the same.
* **`scale` clamps floating point on every version**, for both half-float and 32-bit float EXRs.
* **`zscale` keeps the full range on every version.** `zscale,format=gbrpf32le` is the safe way to get 32-bit float.
  To read the true values from 8.0 on, use `-pix_fmt gbrpf16le`.
* **The `ocio` filter** keeps the full range with a float `format` (8.1, 9.0.2 and the 9.1 development build, the builds
  here that have it), unless `format=gbrpf32le` comes before it. See [FFmpeg OCIO](FfmpegOcio.html#working-with-exr-files-and-ffmpeg).

## HDR and `-x265-params` {#hdr-and--x265-params}

HDR encodes often set the colour description through the encoder's own options, for example:

```console
ffmpeg -i hdr_pq.tif -c:v libx265 -pix_fmt yuv420p10le \
  -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=...:max-cll=2000,50" \
  -tag:v hvc1 output.mp4
```

`libx265` applies `-x265-params` after FFmpeg's own settings, so these values always end up in the HEVC stream.
But FFmpeg never sees them: they do not affect the RGB to Y'CbCr conversion, and they do not reach the MP4 `colr`
atom. Encoding a 16-bit PQ TIFF:

| Command line | 7.0 | 8.1, 9.0 |
| :--- | :--- | :--- |
| `-x265-params` colour settings only | **BT.601 pixels**, stream tagged BT.2020 | **BT.601 pixels**, stream tagged BT.2020 |
| `-x265-params` + `-color_primaries`/`-color_trc`/`-colorspace` | **BT.601 pixels**, tagged BT.2020 | BT.2020 pixels, but with `+write_colr` the `colr` atom says primaries and transfer are unspecified |
| `zscale` + `setparams` (below) | BT.2020 pixels, tagged BT.2020 everywhere | BT.2020 pixels, tagged BT.2020 everywhere |

The first is wrong on every version: nothing tells FFmpeg which matrix to convert with, so it uses BT.601, a
mean luma error of about 15 code values on the test chart.

The same pattern as the SDR commands works for HDR. On every version:

```console
ffmpeg -i hdr_pq.tif \
  -vf "zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
  -c:v libx265 -crf 18 -pix_fmt yuv420p10le \
  -x265-params "master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1):max-cll=2000,50" \
  -color_range tv -colorspace bt2020nc -color_primaries bt2020 -color_trc smpte2084 \
  -movflags +faststart -tag:v hvc1 output_hdr10.mp4
```

As with the SDR command, the `-color_*` flags are redundant here; this shorter form gave the same results on
7.0, 8.0.1, 8.1 and 9.0:

```console
ffmpeg -i hdr_pq.tif \
  -vf "zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
  -c:v libx265 -crf 18 -pix_fmt yuv420p10le \
  -x265-params "master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1):max-cll=2000,50" \
  -movflags +faststart -tag:v hvc1 output_hdr10.mp4
```

* `colorprim`, `transfer` and `colormatrix` are no longer needed in `-x265-params`: `libx265` fills them in from
  the frames. Leaving them in does no harm as long as they agree with the filters.
* The mastering display and content light level (`master-display`, `max-cll`) still have to be passed through
  `-x265-params`, as FFmpeg has no command line options for them. They end up in the HEVC stream only; we have not
  checked whether players also need them in the MP4 `mdcv`/`clli` boxes.
* Tested on 7.0, 8.0.1, 8.1 and 9.0. The 7.1 build we had crashes on any `libx265` encode, so HDR was not
  tested on 7.1.

## PNGs with bad EXIF data no longer decode (8.1) {#png-exif-81}

From 8.1 the PNG decoder reads the `eXIf` chunk, and if the EXIF data cannot be parsed it fails the whole frame
instead of ignoring the metadata:

```console
[png @ 0x...] invalid TIFF header in EXIF data: Invalid data found when processing input
[dec:png @ 0x...] Decoding error: Invalid data found when processing input
```

`ffprobe` still reports the stream normally, so the file looks fine until you decode it, and none of
`-err_detect ignore_err`, `-ec 0` or `-max_error_rate 1` gets the frame back. The encode ends with an empty
output. With `-loop 1` on a single image, `ffmpeg` keeps retrying and never finishes.

We hit this with PNGs written by OpenImageIO 2.4 (`oiiotool` 2.4.15), which wrote a big-endian TIFF header with
the magic number byte-swapped (`MM*\0` instead of `MM\0*`). Images written by OpenImageIO 3.1 decode correctly.
Earlier FFmpeg versions ignored `eXIf` in PNG, so the same files decode on 8.0 and before.

To repair a file, remove the EXIF block. The pixels are not changed:

```console
exiftool -overwrite_original -EXIF= image.png
```

Re-saving with a current `oiiotool` also works, but it adds `sRGB`, `gAMA` and `cHRM` chunks, which FFmpeg reads
as colour tags.

* Tested on 6.0, 7.1.5, 8.0.1 (decode), and 8.1, 9.0.2 and 9.1-dev (fail).
* Introduced by FFmpeg commit `44af382979` ("avcodec/pngdec: support reading EXIF profiles"), first in 8.1.

## Converting Y'CbCr to RGB {#ycbcr-to-rgb}

Extracting stills (`ffmpeg -i movie.mov frame.png`) converts Y'CbCr to RGB, and the same libswscale/`zscale`
differences apply in that direction. Decoding lossless 10-bit BT.709 sources to 16-bit RGB PNG and comparing with
the RGB they were made from (errors in 10-bit code values, away from edges):

| Source | No filter, or `scale` | `zscale` |
| :--- | :--- | :--- |
| BT.709 limited range, chip chart | 5.3 max, 1.3 mean | 1.6 max, 0.3 mean |
| BT.709 limited range, RP 219 bars | 4.7 max, 1.5 mean | 1.0 max, 0.2 mean |
| BT.709 full range, chip chart | 2.3 max, 0.4 mean | 1.4 max, 0.3 mean |
| BT.709 full range, RP 219 bars | 1.4 max, 0.4 mean | 1.0 max, 0.1 mean |
| Untagged (BT.709 limited range pixels) | **146 max**: converted as BT.601 | No output: `zscale` will not guess the matrix |

* The results were identical on 6.1.6, 7.0, 7.1.5, 8.0.1, 8.1, 9.0.2 and a 9.1 development build;
  `scale=flags=accurate_rnd+full_chroma_int` gave the same as plain `scale`.
* For an untagged file, say what it is: `zscale=matrixin=709:rangein=limited` gives the same result as for the
  tagged file.
* **Chroma siting:** for 4:2:2 and 4:2:0 sources, libswscale also assumes the chroma is centred, whatever the
  file says, on every release up to 9.0, so co-sited material (ProRes, DNxHR, most H.264/HEVC) comes out with the
  colour half a pixel to the right. `zscale` follows the file's chroma location and assumes co-sited when there is
  none. Details in [Chroma Siting](ChromaSiting.html#reading-back-to-rgb).

```console
ffmpeg -i input.mov -frames:v 1 -vf "zscale,format=gbrp16le" -pix_fmt rgb48be frame.png
```

`format=gbrp16le` keeps the conversion in `zscale`, which outputs planar RGB; without it FFmpeg may convert with
libswscale instead. The repack to `rgb48be` for the PNG is lossless.

Tested with `enctests/test_configs/decode_tests.yml` and `decode_siting_tests.yml`.

## Chroma location reaches the filter graph (9.1) {#chroma-location-91}

FFmpeg development builds after 9.0 pass the chroma location through the filter graph, as 7.1 started doing for
the matrix and range (commits `02abeae2c7`, "fftools/ffmpeg: add chroma location support", and `950fe27d23`,
"avfilter/vf_scale: convert to the negotiated chroma location"). Measured on N-127508-ga2cfa47aec:

* **Encoding:** with no conversion filter, `-chroma_sample_location left` now makes the inserted conversion
  co-site the chroma (measured -0.03 of a pixel; 0.5, centred, on 9.0 and earlier). Explicit `scale` without
  `out_chroma_loc` still centres it.
* **Decoding to RGB:** libswscale now follows a file's chroma location instead of assuming centred. A file with
  no chroma location is still taken as centred, so co-sited material that does not say so, which includes all
  ProRes and DNxHR, is still converted half a pixel off.

This is not in a release yet; recheck when 9.1 is released. `zscale` is unaffected.

## Relabelling a file

From 7.1 there are three distinct operations, and it helps to keep them separate:

* **Convert:** `-pix_fmt`, `-colorspace` and `-color_range` say what you want the output to be, and `ffmpeg`
  converts to it if the input differs.
* **Transform:** filters such as `zscale`, `colorspace` and `ocio` change the colour and set the tags on their
  output.
* **Relabel:** `setparams` changes the tags without touching the pixels. This is what you want to fix a file that
  is correctly encoded but wrongly tagged:

```console
ffmpeg -i mislabelled.mov \
  -vf "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv" \
  -c:v prores_ks -profile:v 3 fixed.mov
```

Before 7.1, `-colorspace` and `-color_range` also relabelled, which is how files ended up tagged BT.709 with
BT.601 pixels in them. From 7.1 they convert, even when the source is already Y'CbCr and tagged. Transcoding a
10-bit BT.709 limited-range FFV1 file to FFV1, and comparing the decoded pixels with the source's:

| Command line | 6.1.6, 7.0 | 7.1.5, 9.0.2, 9.1.dev |
| :--- | :--- | :--- |
| `-colorspace bt2020nc` | Tagged BT.2020, pixels unchanged | **Re-matrixed to BT.2020** (up to 44 codes different) |
| `-color_range pc` | Tagged full range, pixels unchanged | **Expanded to full range** (Y' 103–877 became 45–947) |
| `-vf setparams=colorspace=bt2020nc` | Tagged BT.2020, pixels unchanged | Tagged BT.2020, pixels unchanged |

The 7.1+ conversions are done by an inserted libswscale `scale`, so on 7.1.5 they differ from 9.0.2 by a code or
two (see [libswscale full-range conversions](#libswscale-full-range-80)). A converted file still decodes to the same
picture, so the mistake is easy to miss; what changes is the data, and a later relabel of it is then wrong.

Do not relabel H.264 in MP4 with the `h264_metadata` bitstream filter alone (for example
`-c copy -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1`). It
rewrites the stream's VUI but not the container's `colr` atom, which keeps the old values (unspecified, in our
test) even with `-movflags +write_colr`. `ffprobe` reports the new VUI values, so the file looks fixed, but a
player that reads `colr` still sees the old tags. The same on 6.1.6, 7.1.5, 8.0.1, 8.1, 9.0.2 and 9.1.dev.
Re-encoding with `setparams`, as above, sets both.
