---
layout: default
nav_order: 6.15
title: Resizing in FFmpeg vs. oiiotool vs. Linear Light
parent: Test Output
---

# Resizing in FFmpeg vs. oiiotool vs. Linear Light

{: .warning }
This is currently actively in development. If you have any recommendations for this, do please let us know.

Three 8-bit sRGB images (a zone plate, a test chart and an animation frame) shrunk to a quarter of their size by
FFmpeg's `scale` and `zscale` filters and by `oiiotool`, both on the gamma-encoded values and in linear light,
compared with a reference that averages each 4×4 block in linear light. Wipe or flip between any two, or show their
difference. Scene-linear OpenEXR sources have their own page:
[Resizing Scene-Linear EXRs](../resize-hdr-compare/resize-hdr.html).

The page and its images are not in this repository; they are hosted at
[encode.taurich.org](https://encode.taurich.org/tests/resize-compare/compare.html). The viewer works best
[full screen](https://encode.taurich.org/tests/resize-compare/compare.html).

<iframe src="https://encode.taurich.org/tests/resize-compare/compare.html" title="Resize comparison"
  style="width:100%; height:1650px; border:0;" loading="lazy"></iframe>

## Making the page

[`tests/resize-test.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/resize-test.py)
makes both this page (`tests/resize-compare/compare.html`) and the
[EXR page](../resize-hdr-compare/resize-hdr.html) (`tests/resize-hdr-compare/compare.html`), with their images. See
the EXR page for what it needs for the EXRs. For this page it needs `ffmpeg` with `zscale` and `oiiotool` on the
`PATH`, and the Python packages in the repository's `requirements.txt`. From the `tests` folder:

```console
python resize-test.py
```

It prints the results of both pages as Markdown tables. To view the pages locally, serve the folder over HTTP
(browsers do not let the page load its images from a `file://` URL), for example `python -m http.server` in `tests`,
then open `http://localhost:8000/resize-compare/compare.html`.

The folder is self-contained, so it can be copied to any web server as it is (leave out `nuke/`, the Nuke results
the EXR page reads).
