---
layout: default
nav_order: 6.16
title: Resizing Scene-Linear EXRs
parent: Test Output
---

# Resizing Scene-Linear EXRs

{: .warning }
This is currently actively in development. If you have any recommendations for this, do please let us know.

Three ACES2065-1 OpenEXR images (Sparks, BrightRings and Desk), viewed through OCIO's ACES 2.0 SDR view, shrunk to a
quarter of their size by FFmpeg (`zscale` and the `ocio` filter), `oiiotool` and Nuke. Each is resized either after
the view transform, as an SDR pipeline would, or before it, in scene-linear light (or log), where highlights far
brighter than white make filters with negative lobes ring. The reference averages each 4×4 block in scene-linear
light, then applies the view. Wipe or flip between any two, or show their difference. For 8-bit sRGB sources, see
[Resizing in FFmpeg vs. oiiotool vs. Linear Light](../resize-compare/resize.html), and for what we recommend,
[Downscaling: scene-linear OpenEXRs](../../Resizing.html#scene-linear-openexrs).

The EXRs are also shrunk by 2.13 (Sparks from 4096 to 1920 wide), with the scene-linear variants only. At that factor
output pixels no longer line up with source pixels, so the reference averages the source pixels each output pixel
covers, weighting the ones at its edges by how much of them it covers. Methods built on 4×4 blocks (the anti-ringing
clamp, highlightcomp with its light restored) use the same footprints there, and work less well: the FFmpeg clamp's
window has to be a fixed 5×5 square, a little looser than the footprint, and restoring highlightcomp's light makes the
highlights somewhat too bright. The cubic comes much closer to the reference at ×2.13 than at 4×.

The page and its images are about 35 MB, so they are not in this repository; they are hosted at
[encode.taurich.org](https://encode.taurich.org/tests/resize-hdr-compare/compare.html). The viewer works best
[full screen](https://encode.taurich.org/tests/resize-hdr-compare/compare.html).

<iframe src="https://encode.taurich.org/tests/resize-hdr-compare/compare.html" title="EXR resize comparison"
  style="width:100%; height:1650px; border:0;" loading="lazy"></iframe>

## Sharp filters without halos

Lanczos is sharper than the cubic, and there are ways to keep most of that sharpness without the halos. None of them is
a single option in FFmpeg or `oiiotool` yet, and we are still testing them (the page above shows them). Figures are
Sparks and BrightRings at 4×: brightness, then 99th percentile error, in 8-bit code values.

- **Anti-ringing:** clamp each output pixel to the range of the source pixels it covers. Next to a highlight, plain
  background stays plain, so there is no halo; inside the highlight lanczos is left alone and keeps its light. This
  is what libplacebo (and so mpv, and FFmpeg's `libplacebo` filter, as `antiringing`) and madVR do. With stock FFmpeg
  filters it takes a long command (`hdr_ff_antiring_ocio` in `tests/resize-test.py`); on our images it gives
  Sparks +0.1, 52 and BrightRings +0.5, 21, but can look slightly blocky around the sparks.
- **Highlight compensation with its light restored:** multiply the highlight-compensated result by the ratio of each
  output pixel's average in scene-linear to the same average done on compressed values, which puts back the light it
  loses (Sparks −0.4, 26; BrightRings −0.2, 35; with the anti-ringing clamp on top, −0.1, 19 and +0.3, 17). This
  needs a small script (see below). For a factor that is not a whole number it makes the highlights somewhat too
  bright.

## Making the page

[`tests/resize-test.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-test.py)
makes this page (`tests/resize-hdr-compare/compare.html`) and the
[8-bit sRGB page](../resize-compare/resize.html). For the EXRs it needs:

- `ffmpeg` with `zscale` and the `ocio` filter (FFmpeg 8.1 or later), and `oiiotool` with OpenColorIO 2.5 or later
  (it uses the built-in `ocio://default` config), on the `PATH`;
- the Python packages in the repository's `requirements.txt` (including the OpenImageIO bindings);
- the Sparks EXR: run `enctests/sources/hdr_sources/download_media.sh`;
- the [OpenEXR test images](https://github.com/AcademySoftwareFoundation/openexr-images) checked out next to this
  repository (`../openexr-images`), or set `OPENEXR_IMAGES` to their folder.

Then, from the `tests` folder:

```console
python resize-test.py
```

It takes about a quarter of an hour, mostly for the EXRs. Any EXR it cannot find is left out, with a message. To view
the page locally, serve the folder over HTTP, for example `python -m http.server` in `tests`, then open
`http://localhost:8000/resize-hdr-compare/compare.html`.

The timing table comes from
[`tests/resize-timing.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-timing.py),
which runs each variant on the 200 Sparks frames, from the EXRs to a ProRes 422 HQ QuickTime, and writes
`tests/resize-timing-results.json`. Run it once as it is and once with `--parallel-frames` (for oiiotool), before
`resize-test.py`; it takes about half an hour. Without the results, the timing table is left out.

The anti-ringing variant clamps lanczos to the range of the source pixels each output pixel covers (its 4×4 block at
4×), in a single FFmpeg command, which needs `tests/log16.clf` for the limits.
[`tests/resize-antiring.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-antiring.py)
does the same with the OpenImageIO Python bindings and exact limits; it is the reference the FFmpeg command was
checked against, and is not on the page.

The "light restored" highlightcomp variants come from
[`tests/resize-highlightcomp.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-highlightcomp.py),
run by `resize-test.py` with the OpenImageIO Python bindings (the timing test leaves them out): highlightcomp, multiplied by the ratio of the
average of the source pixels each output pixel covers, in scene-linear, to the same average done on the compressed
values. The footprints for both scripts and for the reference come from
[`tests/python/resizefootprint.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/python/resizefootprint.py).

The Nuke variants (Sparks only) come from [`tests/resize-nuke.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-nuke.py): paste it into Nuke's Script
Editor (it was run in Nuke 17.1v1) to write the EXRs to `resize-compare/nuke/`, then run `resize-test.py`. Without them,
the Nuke variants are left out.

The folder is self-contained, so it can be copied to any web server as it is.
