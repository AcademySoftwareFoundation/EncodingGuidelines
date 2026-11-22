---
layout: default
title: HDR Display Tests
nav_order: 6.32
parent: Test Output
---

# HDR Display Tests

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

Test pages for checking what a player or display does with HDR10 metadata (mastering display, MaxCLL/MaxFALL)
and with colour outside its gamut. The results, and the setup we recommend from them, are in
[HDR Encoding](../../enctests/HDR_Encoding.html#player-behaviour).

## The pages

The pages, videos and images are not in this repository; they are hosted at encode.taurich.org.

| Page | What it is for |
| :--- | :--- |
| [HDR display tests](https://encode.taurich.org/tests/hdr-metadata-display/simple/index.html) | Start here. Eight tests, one question each, with what to look at and what each result means. |
| [HDR10 metadata display test (full set)](https://encode.taurich.org/tests/hdr-metadata-display/index.html) | Twelve charts for detailed checks, including which copy of the metadata a player reads (HEVC SEI or MP4 `mdcv`/`clli` boxes). |
| [Gamut test](../../gamuttests/gamut-tags/gamut-test.html) | The same SDR picture with its colour space declared different ways (PNG ICC, cICP, both, video tags), to see which tags a viewer reads and whether it clips or compresses colour outside the screen's gamut. |

The tests in the first page:

1. **Mastering peak:** does the player use the mastering display peak luminance?
2. **Default with no metadata:** what peak does it assume when there is none?
3. **Mastering peak or MaxCLL:** which one wins when they disagree?
4. **Mastering primaries:** does it change colours according to the mastering display primaries?
5. **SDR white in PQ:** at what PQ level does the system put the page's white?
6. **Honest metadata:** does metadata that matches the content (within 1000 cd/m<sup>2</sup> and P3) change it?
7. **Image vs video gamut:** do images and video handle colour outside the screen's gamut the same way?
8. **Colours inside P3:** are colours near the P3 edge changed when they come in a BT.2020 file?

Each test flips between two or three files (<kbd>Space</kbd>); <kbd>R</kbd> shows a reference rendered by
libplacebo, a player that uses all of the metadata, so you can see what a difference looks like. Each file has a
download link, so the same files can be opened in QuickTime, a review tool, or on a TV.

## Using them

* Look at the screen itself, not a screenshot: tone mapping is often done after the screenshot is taken.
* Keep the display settings fixed while comparing, and note them with the results. On a Mac the result depends on
  the display preset, the brightness setting and which window is active; the pages show a setup guide when opened
  on a Mac.
* The browser is a player too. Repeat the tests in the players you review with.
* An external HDR monitor or TV that tone maps from the HDMI/DisplayPort metadata gets one set of metadata for the
  whole screen, so use full screen (<kbd>Enter</kbd>) there, or play the files on the TV itself.

## Making them

The pages and videos are made by
[`tests/hdr_metadata_simple.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/hdr_metadata_simple.py),
[`tests/hdr_metadata_display_chart.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/hdr_metadata_display_chart.py)
and
[`gamuttests/make_gamut_tag_test.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/gamuttests/make_gamut_tag_test.py).
The HDR charts need FFmpeg 9.0 or later with `libx265` (for `-mastering_display` and `-content_light`), and
libplacebo for the references; the gamut test needs `oiiotool`. Each script's header says how to run it.
