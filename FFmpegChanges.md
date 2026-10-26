---
layout: default
title: FFmpeg Version Changes
nav_order: 5
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
| [`-color_primaries` and `-color_trc` are ignored](#primaries-trc-flags-71) | 7.1 and later | The flags are silently dropped. Use `setparams` to set primaries and transfer. |
| [ProRes writes its colour tags from the frame, not the flags](#prores-colour-tags-come-from-the-frame) | All | With flags only, the MOV `colr` atom and the ProRes frame header can disagree (7.0 and earlier) or both be missing (7.1 and later). |
| [`-x265-params` colour settings only tag the HEVC stream](#hdr-and--x265-params) | All | They do not change the conversion. Without `-colorspace` or a conversion filter, the pixels are BT.601 in a file tagged BT.2020. |
| [libswscale puts limited-range white too high for high-bit-depth input](#libswscale-white-level-for-high-bit-depth-input) | All, including 9.0 | 10-bit RGB to 10-bit Y'CbCr puts 100% white at 943 instead of 940. Use `zscale`. `scale=...:flags=unstable` (8.1 and later) fixes 4:4:4 only. |

## Recommended commands

### Every version

This gives correct pixels and correct colour tags, in every place they are stored, on every version we tested
(FFmpeg 6.0 to 9.0), for both ProRes and H.264, and for any source bit depth:

```console
ffmpeg -i input.%06d.dpx \
  -vf "zscale=rangein=full:matrix=709:range=limited,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
  -c:v prores_ks -profile:v 4444xq -pix_fmt yuv444p10le \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
  output.mov
```

* **`zscale=rangein=full:matrix=709:range=limited`** does the RGB to Y'CbCr conversion. Without an explicit
  conversion, 7.0 and earlier convert with BT.601. `zscale` was exact in all our tests; see
  [below](#libswscale-white-level-for-high-bit-depth-input) for why we do not use `scale`. `zscale` also sets the
  matrix and range on its output frames, which is what tags them.
* **`setparams=color_primaries=bt709:color_trc=iec61966-2-1`** sets primaries and transfer on the frames. This is
  the only way to set them on 7.1 and later.
* **The four `-color_*` flags** turned out to be redundant with this filter chain on every version we tested,
  because the encoder takes its tags from the frames, which `zscale` and `setparams` have already set. They do no
  harm, and make the intent of the command explicit.

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
  -vf "zscale=rangein=full:matrix=709:range=limited,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
  -c:v prores_ks -profile:v 4444xq -pix_fmt yuv444p10le \
  output.mov
```

Do not be tempted to drop `zscale` on 7.1 and later. From 7.1, `-colorspace bt709 -color_range tv` alone does
get the matrix right, but the conversion is then done by libswscale, which puts 100% white at 943 instead of 940
from a 10-bit or 16-bit source (see [below](#libswscale-white-level-for-high-bit-depth-input)). The explicit
`zscale` is what makes it accurate, on every version.

For H.264 or HEVC in an MP4, also add `-movflags +write_colr`; otherwise the MP4 muxer writes no `colr` atom and
the tags only exist in the video stream.

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
python tests/colour_flags_matrix.py --rez 6.0 7.0 7.1 8.0.1 8.1 9.0
python tests/rgb2ycbcr_accuracy.py --rez 6.0 7.0 7.1 8.0.1 8.1 9.0
```

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
  re-matrixed to BT.2020, and the file still decodes to the
  same RGB. Neither is a retag. To change the label without touching the pixels, use `setparams`; see
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

See [Ffmpeg Scaling Options](EncodeSwsScale.html#colour-range-accuracy-prefer-zscale-for-range-conversions) for
more on the cause.

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
  -vf "zscale=rangein=full:matrix=2020_ncl:range=limited,setparams=color_primaries=bt2020:color_trc=smpte2084" \
  -c:v libx265 -crf 18 -pix_fmt yuv420p10le \
  -x265-params "master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1):max-cll=2000,50" \
  -color_range tv -colorspace bt2020nc -color_primaries bt2020 -color_trc smpte2084 \
  -movflags +faststart+write_colr -tag:v hvc1 output_hdr10.mp4
```

As with the SDR command, the `-color_*` flags are redundant here; this shorter form gave the same results on
7.0, 8.0.1, 8.1 and 9.0:

```console
ffmpeg -i hdr_pq.tif \
  -vf "zscale=rangein=full:matrix=2020_ncl:range=limited,setparams=color_primaries=bt2020:color_trc=smpte2084" \
  -c:v libx265 -crf 18 -pix_fmt yuv420p10le \
  -x265-params "master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1):max-cll=2000,50" \
  -movflags +faststart+write_colr -tag:v hvc1 output_hdr10.mp4
```

* `colorprim`, `transfer` and `colormatrix` are no longer needed in `-x265-params`: `libx265` fills them in from
  the frames. Leaving them in does no harm as long as they agree with the filters.
* The mastering display and content light level (`master-display`, `max-cll`) still have to be passed through
  `-x265-params`, as FFmpeg has no command line options for them. They end up in the HEVC stream only; we have not
  checked whether players also need them in the MP4 `mdcv`/`clli` boxes.
* Tested on 7.0, 8.0.1, 8.1 and 9.0. The 7.1 build we had crashes on any `libx265` encode, so HDR was not
  tested on 7.1.

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
BT.601 pixels in them.
