---
layout: default
title: Chroma Siting Tests
nav_order: 5.85
parent: Test Output
---

# Chroma Siting Tests

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

The detail behind [Chroma Siting](ChromaSiting.html): where each converter puts the chroma, what each format
records, and how it was measured. To check a player, use the [Chroma Siting Check](sourceimages/chroma_siting_check/README.html)
files ([more test files](#players)).

## Results by converter

Converting RGB to 4:2:2 and 4:2:0. Positions are in luma samples: 0 is co-sited, 0.5 is centered. The results
were the same on 6.0, 7.0, 7.1, 8.0.1, 8.1, 9.0 and 9.1, except where noted.

| Converter | 4:2:2,<br>should be co-sited ([BT.709 item 4.3](https://www.itu.int/rec/R-REC-BT.709)) | 4:2:0 (horizontal / vertical),<br>should be co-sited / centered ([H.264](https://www.itu.int/rec/T-REC-H.264)/[H.265](https://www.itu.int/rec/T-REC-H.265) Annex E default) | Correct? |
| :--- | :--- | :--- | :--- |
| `zscale` (default) | co-sited | co-sited / centered | Yes |
| `zscale=...:chromal=center` | centered | centered / centered | Only for formats that want centered chroma |
| `scale`, or no filter | centered, pair-averaged | centered / centered | **No** |
| `scale=...:flags=unstable` (8.1+) | centered, pair-averaged | centered / centered | **No**, the same as `scale` |
| `scale=...:out_chroma_loc=left` (7.1+) or `out_h_chr_pos=0` | -0.05, pair-averaged | -0.05 / centered | Close, not exact |
| as above, plus `-sws_flags +full_chroma_inp` | co-sited | co-sited / centered | Yes |
| no filter, `-chroma_sample_location left` | centered; **co-sited (-0.05) from 9.1** | the same | From 9.1: close, not exact |

"Pair-averaged" means the converter averaged each pair of RGB pixels into one chroma value before filtering:
a line on an even column and a line on the following odd column give exactly the same chroma. libswscale does
this for RGB input unless `full_chroma_inp` is set, whatever position it is asked for, which is why asking for
co-sited without that flag only gets to within 0.05 of a pixel. Note that this contradicts older advice
(including earlier versions of [FFmpeg swscale Filter](EncodeSwsScale.html)) that `full_chroma_inp` does nothing
for RGB input.

The last row is new in FFmpeg 9.1: `-chroma_sample_location` is now
passed into the filter graph, the way 7.1 started doing for `-colorspace`, so the conversion FFmpeg inserts
follows it. In 9.0 and earlier it does not affect the conversion.

## What each format records {#recorded-details}

What FFmpeg 9.0 writes, for frames that carry a chroma location (VP9 measured on 6.1.6 and 9.0.2, the same on both):

| Codec | Field | 4:2:0 | 4:2:2 |
| :--- | :--- | :--- | :--- |
| H.264 | VUI `chroma_sample_loc_type` (4:2:0 only) | Written, except `left` (the default, which readers assume when nothing is written) | No field; assumed co-sited |
| HEVC (`libx265`) | VUI, as H.264 (4:2:0 only) | Written | No field |
| AV1 (`libsvtav1`) | `chroma_sample_position` (4:2:0 only) | `left` and `topleft` written; AV1 has no value for centered | No field |
| AV1 (`libaom-av1`) | as above | Always written as unknown: FFmpeg's `libaom` wrapper does not pass it on | No field |
| VP9 (`libvpx-vp9`) | None in the bitstream. In MP4 the `vpcC` box's `chromaSubsampling` (see the MOV / MP4 row below) | MP4: `left` written as 0 (vertical), anything else, including `center` and no location, as 1 (co-located, i.e. `topleft`): centered chroma is mislabelled | MP4: 2, no siting |
| ProRes, DNxHD/DNxHR | None | | Assumed co-sited |

| Container | Field | Behavior |
| :--- | :--- | :--- |
| Matroska / WebM | `ChromaSitingHorz`, `ChromaSitingVert` | Written for every codec and subsampling, and read back by FFmpeg. The only container here that records siting for every codec and FFmpeg reads back. |
| MXF | `ColorSiting` | Written, but not read back by FFmpeg. With no location on the frames, 4:2:2 is written as 0 (co-sited). FFmpeg maps `left` to 6 and `center` to 3 whatever the subsampling, which are ST 377-1's 4:2:0 values; for 4:2:2 the matching values would be 0 and 1. |
| MOV / MP4 | None, except VP9's `vpcC` | Only what the codec stream itself carries, apart from VP9 in MP4 (above). FFmpeg does not read `vpcC` back: `ffprobe` shows `unspecified`. |

### DNxHR in MXF

MXF does record siting, which makes a mismatch worse rather than better: the file states the wrong thing.
Encoding the test chart to DNxHR HQX 4:2:2 in MXF (OP1a and OP-Atom gave the same results; also the same on 6.0,
7.1 and 9.0):

| Command | MXF `ColorSiting` | Chroma actually is |
| :--- | :--- | :--- |
| `scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709` | 0, co-sited | **centered**: the label is wrong |
| `zscale=rangein=full:matrix=709:range=limited` | 0, co-sited | co-sited |
| `zscale=...:chromal=left` | 6, vertical midpoint | co-sited, but the label is odd for 4:2:2 |
| `scale` with `out_chroma_loc=left` and `full_chroma_inp` | 6, vertical midpoint | co-sited |

FFmpeg names 4:2:2 co-siting `topleft`, and maps `left` to MXF value 6, "vertical midpoint", which ST 377-1
defines as the MPEG-2 and H.264 4:2:0 position. For 4:2:2 that is the wrong value: a reader that takes it
literally sees 4:2:0 siting on 4:2:2 material. So for 4:2:2 MXF, leave `zscale`'s chroma location at its default
(or use `topleft`), which gives 0; do not set it to `left`.

## Reading back to RGB, measured {#reading-back-results}

Measured by decoding 4:2:2 and 4:2:0
versions of the test chart with known siting to 16-bit RGB PNG, with and without a chroma location tag (FFV1 in
Matroska, which carries the tag through to FFmpeg's decoder). Positions are in luma samples: 0 is co-sited, 0.5
centered.

| Converter | Tagged `left` or `topleft`,<br>should follow the tag | Tagged `center`,<br>should follow the tag | No tag (chroma co-sited),<br>should assume co-sited ([BT.709 item 4.3](https://www.itu.int/rec/R-REC-BT.709)) |
| :--- | :--- | :--- | :--- |
| `zscale` | Correct | Correct | Assumes co-sited: correct |
| `scale`, or no filter, 6.1 to 9.0 | **Assumes centered: chroma 0.5 to the right** | Correct | **Assumes centered: 0.5 to the right** |
| `scale`, or no filter, 9.1 | Follows the tag (within 0.07) | Correct | **Assumes centered: 0.5 to the right** |

The results were the same on 6.1.6, 7.0, 7.1.5, 8.0.1, 8.1 and 9.0.2; 9.1 is
the only one that differs, and only for coarse detail when converting to packed RGB such as PNG: the finest
chroma detail still comes out as if centered (see the [4:2:2 player chart](ChromaSitingPlayerChart.html#how-it-works)). `-sws_flags +full_chroma_int` (or `scale=flags=...+full_chroma_int`) makes libswscale
interpolate the chroma instead of repeating each sample across two pixels, which it otherwise does when converting
4:2:x to RGB, but it does not change the position it assumes.

## Checking players {#players}

Players and browsers make the same choice when they display 4:2:x, and most of them cannot be measured from a
script. There are three sets of test files for them, each with its own page:

* [Chroma Siting Check](sourceimages/chroma_siting_check/README.html): small files, one per label, codec and
  orientation, including HDR10 and rotated copies, with a [viewer page](sourceimages/chroma_siting_check/view.html).
  A player that follows the label shows a blank field, any other shows the word **WRONG**. Start here.
* [4:2:2 Player Chart](ChromaSitingPlayerChart.html): full HD, for what a 4:2:2 player does instead (centered linear,
  centered bicubic, or sample repeat), and whether it reads the MKV and MXF labels.
* [Pixel Charts](ChromaSitingPixelChart.html): 64x64 charts to zoom in on, to show single pixels.

## How this was tested

* [chroma_siting_chart.png](sourceimages/chroma_siting_chart.png), generated by [make_chroma_siting_chart.py](sourceimages/make_chroma_siting_chart.py) and described
  in `sourceimages/README.md`, has linear "tents" in blue that peak exactly between two columns (rows), and
  single-pixel lines on even and odd columns (rows).
* The chroma position is where the two sides of the tent meet in the converted chroma plane: a symmetric filter
  on a linear ramp returns the ramp's value at the filter's center, so this gives the sample position
  independently of the filter, gain or offset. The lines give the same position a second way, and show whether
  even and odd columns are treated alike.
* All conversions are to 16-bit 4:2:2 and 4:2:0 written as raw video, so no codec is involved, except the
  tagging and DNxHR tests, which encode with each codec.

```console
python tests/chroma_siting.py --label 9.0      # once per FFmpeg version
python tests/chroma_siting.py --summarize      # tests/chroma-siting/summary.md
python tests/chroma_siting_containers.py --label 9.0
python tests/chroma_siting_images.py
```

Each script measures whichever `ffmpeg` is on the `PATH` (or `FFMPEG_BIN` and `FFPROBE_BIN`). Run it once per
FFmpeg version with `--label`, then `--summarize` combines the runs into the script's `summary.md`. With a rez
setup that has an `ffmpeg-<version>` package per version, `--rez 6.0 7.0 ...` does both. The scripts need numpy
and the OpenImageIO Python bindings (`requirements.txt`).
The combined results for every version are on [Chroma Siting by Version](FFmpegChangesChromaSiting.html).

The same measurements, and the reverse direction, are also part of the encoding test framework, so they are re-run
for each FFmpeg version (`enctests/test_configs/chroma_siting_tests.yml` and `decode_siting_tests.yml`). For the
reverse direction, [make_chroma_siting_sources.py](sourceimages/make_chroma_siting_sources.py) subsamples the chart in numpy at a known siting
and stores it as FFV1 in Matroska. The decoded RGB is converted back to full-resolution chroma, and compared with
the ideal chroma of the chart shifted by a fraction of a pixel; the shift that matches best is how far the
decoder moved the chroma. Both are blurred first, so the converter's own filter does not affect the result.

## Where this is specified

| Specification | What it says |
| :--- | :--- |
| [ITU-R BT.601-7](https://www.itu.int/rec/R-REC-BT.601) (SD), Part A, sampling structure | "C<sub>R</sub> and C<sub>B</sub> samples co-sited with odd (1st, 3rd, 5th, etc.) Y samples in each line" |
| [ITU-R BT.709-6](https://www.itu.int/rec/R-REC-BT.709) (HD), item 4.3 | C<sub>B</sub>, C<sub>R</sub> "co-sited with each other and with alternate Y samples", "the first active color-difference samples being co-sited with the first active luminance sample" |
| [ITU-R BT.2020-2](https://www.itu.int/rec/R-REC-BT.2020) (UHD), Table 5 | For 4:2:2 and 4:2:0: "The first (top-left) sample is co-sited with the first Y' samples" |
| [ITU-T H.264](https://www.itu.int/rec/T-REC-H.264) and [ITU-T H.265](https://www.itu.int/rec/T-REC-H.265), Annex E (VUI) | `chroma_sample_loc_type_top_field` / `_bottom_field`, values 0 to 5, for 4:2:0 only, shown in Figure E-1. 0 (left: co-sited horizontally, centered vertically) is the default when nothing is signalled. |
| [ITU-T H.273](https://www.itu.int/rec/T-REC-H.273) (07/21 and later) | Adds a coding-independent code point for the 4:2:0 chroma sampling grid alignment, alongside the familiar primaries, transfer and matrix code points |
| [AV1 specification](https://aomediacodec.github.io/av1-spec/#color-config-semantics), color config semantics | `chroma_sample_position`, 4:2:0 only: 0 unknown, 1 `CSP_VERTICAL` "horizontally co-located with (0, 0) luma sample, vertical position in the middle between two luma samples", 2 `CSP_COLOCATED` "co-located with (0, 0) luma sample". There is no value for centered. |
| [Matroska, RFC 9559](https://www.rfc-editor.org/rfc/rfc9559#section-5.1.4.1.28.23) sections 5.1.4.1.28.23 and .24 | `ChromaSitingHorz`: 0 unspecified, 1 left collocated, 2 half. `ChromaSitingVert`: 0 unspecified, 1 top collocated, 2 half. |
| SMPTE ST 377-1:2019 (MXF), section G.2.29, CDCI picture descriptor | `ColorSiting`: 0 coSiting, "as in ITU-R Rec 601, SMPTE ST 314 4:1:1 or MPEG-2 4:2:2"; 1 horizontal mid-point; 3 quincunx, "as in MPEG-1 4:2:0"; 4 Rec601 (equivalent to 0, deprecated); 5 line alternating; 6 vertical midpoint, "as in MPEG-2 4:2:0 and H.264/AVC 4:2:0"; 255 unknown, the default when absent. (SMPTE standards are not freely available.) |
| FFmpeg [`AVChromaLocation`](https://github.com/FFmpeg/FFmpeg/blob/master/libavutil/pixfmt.h) (`libavutil/pixfmt.h`) | FFmpeg's own names, with a diagram: `left` is "MPEG-2/4 4:2:0, H.264 default for 4:2:0", `center` is "MPEG-1 4:2:0, JPEG 4:2:0", `topleft` is "ITU-R 601, SMPTE 274M ..., mpeg2 4:2:2" |

So in FFmpeg's terms, professional 4:2:2 is `topleft` (for 4:2:2, which has no vertical subsampling, `left` and
`topleft` put the chroma in the same place), H.264/HEVC 4:2:0 is `left`, and BT.2020 4:2:0 is `topleft`.
