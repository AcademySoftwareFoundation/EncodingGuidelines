---
layout: default
nav_order: 5.87
title: Chroma Siting Check
parent: Test Output
---

# Chroma Siting Check: Does the Player Follow the Label?

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

**[Open the viewer page](view.html)** to go through the files in a browser.

The [player charts](../../ChromaSitingTests.html#chart-420) tell you what a player assumes, but you have to work out
from the label which band should be flat. These files turn that into a yes or no: each one is made for its own
label, and a player that follows the label shows a flat field, while any other player shows the word **WRONG**. So
the rule is the same for every file: blank is right.

[view.html](view.html) shows each file at exactly one video pixel per screen pixel, records your answers, and gives
a summary to copy. In other players, open the files at 100%.

## The files

A 4:2:0 file has two panels, Across and Down, which can be wrong independently; a 4:2:2 file has only Across. The
HEVC files are 10-bit and the H.264 files 8-bit, so that browsers play them. The FFV1 (`.mkv`) and MXF files are
for desktop players.

| File | Label | Should be |
| :--- | :--- | :--- |
| [420-hevc-untagged.mp4](chroma_siting_check_420-hevc-untagged.mp4), [420-h264-untagged.mp4](chroma_siting_check_420-h264-untagged.mp4) | None | Across co-sited, Down centered (`left`, the default) |
| [420-hevc-left.mp4](chroma_siting_check_420-hevc-left.mp4), [420-lossless-left.mkv](chroma_siting_check_420-lossless-left.mkv) | `left` | Across co-sited, Down centered |
| [420-hevc-topleft.mp4](chroma_siting_check_420-hevc-topleft.mp4), [420-h264-topleft.mp4](chroma_siting_check_420-h264-topleft.mp4), [420-lossless-topleft.mkv](chroma_siting_check_420-lossless-topleft.mkv) | `topleft` | Co-sited both ways |
| [420-hevc-center.mp4](chroma_siting_check_420-hevc-center.mp4), [420-h264-center.mp4](chroma_siting_check_420-h264-center.mp4), [420-lossless-center.mkv](chroma_siting_check_420-lossless-center.mkv) | `center` | Centered both ways |
| [422-prores-untagged.mov](chroma_siting_check_422-prores-untagged.mov), [422-hevc-untagged.mp4](chroma_siting_check_422-hevc-untagged.mp4), [422-dnxhr-untagged.mxf](chroma_siting_check_422-dnxhr-untagged.mxf) | None (MXF `ColorSiting` 0) | Co-sited |
| [422-lossless-left.mkv](chroma_siting_check_422-lossless-left.mkv) | `left` | Co-sited |
| [422-lossless-center.mkv](chroma_siting_check_422-lossless-center.mkv), [422-dnxhr-center.mxf](chroma_siting_check_422-dnxhr-center.mxf) | `center` (MXF `ColorSiting` 1) | Centered |

Every name starts with `chroma_siting_check_`. The files are 640 pixels wide and 360 high (216 for 4:2:2), and the
whole set is about 1.6 MB. They are made by [make_chroma_siting_check.py](../make_chroma_siting_check.py), and
[tests/chroma_siting_check.py](../../tests/chroma_siting_check.py) measures them as FFmpeg decodes them, or from a
1:1 screenshot (`--capture`). Do not re-encode them: compression blurs the one-pixel stripes.

### Rotated copies

Phone video is often stored sideways with a display matrix that turns it upright. The label describes the stored
frame, so a player has to rebuild the chroma on the stored frame's grid and then rotate, or swap the siting if it
rotates the Y'CbCr planes first. These copies are stored turned 90 degrees and say to turn them back:

* [420-hevc-left-rot90.mp4](chroma_siting_check_420-hevc-left-rot90.mp4)
* [420-hevc-topleft-rot90.mp4](chroma_siting_check_420-hevc-topleft-rot90.mp4)
* [420-h264-untagged-rot90.mp4](chroma_siting_check_420-h264-untagged-rot90.mp4)
* [420-h264-topleft-rot90.mp4](chroma_siting_check_420-h264-topleft-rot90.mp4)
* [422-hevc-untagged-rot90.mp4](chroma_siting_check_422-hevc-untagged-rot90.mp4)
* [422-prores-untagged-rot90.mov](chroma_siting_check_422-prores-untagged-rot90.mov)

Their Across panel on screen tests the stored frame's vertical siting, so a rotated 4:2:2 file has a Down panel
instead. Each should be blank, as for the file it was made from.

## How it works

The files use the mirror trick and colors of [the 4:2:0 chart](../../ChromaSitingTests.html#chart-420). A panel's
background repeats a four-pixel cycle of stripes (vertical stripes for Across, horizontal ones for Down), and the
word has the same chroma and the luma of the mirror image. For a player that rebuilds the chroma where the label
says, every pixel of the word is also a pixel of the background, so from a distance the word disappears; for any
other player the word and background differ in linear light and the word shows. This holds whatever filter the
player uses, and whatever the display's gamma.

Where the word's edge crosses the stripes the pattern changes phase, which would show as an outline, so the edge
is staggered by 0 to 7 pixels from row to row. Close up the word is still faintly visible as a change of texture:
judge it from a distance.

As with the charts, it only works at exactly 100%. A viewer that scales the picture averages the code values first,
and the word disappears whatever the player does. The scale check at the top right shows it: its two halves look
equally bright from a distance only at 100%.

## Viewing them

* **The display mode must be 1:1 with the panel.** A macOS "looks like" mode that is not the panel's native
  resolution or exactly half of it rescales everything, which averages the stripes away, so every file looks
  right. The viewer page warns when the OS is sending a width no panel has (6400 for a 4K screen at "looks like
  3200x1800"); the scale check in the video shows it too.
* **Large pixels need more distance.** On a screen with about 110 pixels per inch, such as a 27" 2560x1440, the
  stripes and the word's outline are easy to see close up. Stand back further than for a Retina screen.
* **Browsers draw video in more than one way**: handed to the operating system, or composited into the page.
  Clicking, pausing, or showing controls can switch between them. The viewer page has switches for controls and
  nearest-neighbor rendering, and a link to open the file on its own, to compare. A result that changes with these
  is a real difference between the browser's drawing paths, not a fault in the file.

## Results

### FFmpeg

Measured with `python tests/chroma_siting_check.py` on 9.1. 9.0.2 is the same, except that planar RGB shows every
file centered both ways, as for the [charts](../../ChromaSitingTests.html#chart-420).

| Conversion | Files not rotated | Rotated files |
| :--- | :--- | :--- |
| `zscale` | Blank, except **WRONG** for the MXF with `ColorSiting` 1 (FFmpeg does not read it) | **WRONG** |
| No filter, to planar RGB | Blank, except **WRONG** for the untagged 4:2:2 files (no label FFmpeg reads, so it assumes centered) | **WRONG** |
| No filter, to packed RGB | **WRONG** across for everything but `center`, and down too for 8-bit `topleft` | **WRONG** |

FFmpeg gets every rotated file wrong. Its autorotate inserts `transpose` on the Y'CbCr planes, and `transpose` does
not change the chroma location, so the conversion to RGB that follows puts the chroma in the wrong place, with
`zscale` as well as libswscale (measured on 9.0.2 and 9.1; `libavfilter/vf_transpose.c` is unchanged on the master
branch). Decoding with `-noautorotate`, converting with `zscale` and rotating the RGB gives a blank field. Any tool
built on FFmpeg that rotates the same way has the same problem.

### Players

Not yet collected. The players' results with the [player charts](../../ChromaSitingTests.html#chart-420) show what
to expect; for example Safari and Chrome on macOS showed 8-bit H.264 tagged `topleft` centered both ways, so
they should show **WRONG** in both panels of `420-h264-topleft.mp4`. If you go through the files, the summary from the
viewer page is welcome as an issue on the repository.
