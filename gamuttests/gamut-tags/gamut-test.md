---
layout: default
title: Gamut test
nav_order: 6.3
parent: Test Output
---

# Gamut test

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

The same SDR picture (sRGB curve) with its colour space declared different ways, to see which tags a viewer
reads, and whether it clips or compresses colour outside the screen's gamut.

The page and its images are not in this repository; they are hosted at
[encode.taurich.org](https://encode.taurich.org/gamuttests/gamut-tags/index.html). The viewer works best
[full screen](https://encode.taurich.org/gamuttests/gamut-tags/index.html).

<iframe src="https://encode.taurich.org/gamuttests/gamut-tags/index.html" title="Gamut tag test"
  style="width:100%; height:900px; border:0;" loading="lazy" allow="fullscreen"></iframe>

## Reading the charts

Each chart has text drawn in one colour on a background of a nearby colour:

* **"sRGB"** text, a darker version of the background, is the control: it should be readable everywhere.
* **"P3"** text, in the P3 primary on the BT.709 primary: readable only if the screen shows more than sRGB.
* **"BT.2020"** text, in the BT.2020 primary on the P3 primary (BT.2020 charts only): readable only if the screen
  shows more than P3. On a P3 screen it should vanish; if it is faintly visible, the viewer compresses colour
  outside the screen's gamut rather than clipping it.

Tagged versions of a chart should all look the same. One that looks like *png-untagged* had its tags ignored.

| File | Colour space declared by |
| :--- | :--- |
| png-untagged | Nothing (control: shown as sRGB, so the colours are wrong) |
| png-icc | ICC profile (`iCCP`) only |
| png-cicp | `cICP` only |
| png-icc-cicp | Both, agreeing |
| png-conflict | An sRGB ICC profile and the real `cICP`: the PNG specification says `cICP` wins |
| png-oiio-default | ICC + `cICP` + the `sRGB`/`gAMA`/`cHRM` chunks `oiiotool` adds by default |
| mp4-h264, mp4-hevc | Primaries, transfer and matrix in the video stream and the MP4 `colr` box |

There are two sets: a BT.2020 container and a P3-D65 container.

## What we saw

On a MacBook Pro (XDR screen), macOS 26.6:

* The PNGs clipped colour outside the screen's gamut (the BT.2020 text vanished), but the BT.2020 MP4s compressed
  it (the text stayed faintly visible). Images and video are handled differently.
* Chrome followed `cICP` over the ICC profile (*png-conflict* looked like *png-cicp*), as the PNG specification
  says it should.
* On two SDR monitors, macOS compressed rather than clipped when fitting P3 into their smaller gamuts.

The HDR version of these checks, and what they mean for review, are in [HDR Display Tests](../../tests/hdr-metadata-display/hdr-display-tests.html).

## Making the files

[`gamuttests/make_gamut_tag_test.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/gamuttests/make_gamut_tag_test.py)
writes the charts, the ICC profiles (ICC v4, sRGB curve, made by the script) and this page's viewer. The PNG tags
are written with `oiiotool` (`--iccread`, `--cicp`). `oiiotool` also writes `sRGB`/`gAMA`/`cHRM` chunks unless
`oiio:ColorSpace` is set to a display colour space (e.g. `srgb_p3d65_display`), which *png-oiio-default* shows.

This replaces an older test that tagged its videos with `-color_primaries`, which FFmpeg 7.1 and later ignore. Its
files are still in `gamuttests/iccgamut/`, used by [Color Metadata and Web Color Preservation](../../WebColorPreservation.html).
