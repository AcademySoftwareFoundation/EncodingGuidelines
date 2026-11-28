---
layout: default
nav_order: 6.5
title: Codec Test Page
parent: Test Output
---

There is also a [full-screen version of this page](web_compatibility.html).

This page shows H.264, HEVC/H.265, VP9 and AV1 at 8, 10 and 12-bit, in Y'CbCr 4:2:0, 4:2:2 and 4:4:4, and in RGB.
It tests your browser as it loads: for each movie it records whether it plays, whether the colors match the source,
and what the browser claims it supports. The results are at the bottom of the page, where you can copy or download
them.

How it is made:

* The movies are encoded by [`make_web_tests.py`](make_web_tests.py) from
  [`codec_web_tests.yml`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/enctests/test_wedge_configs/codec_web_tests.yml)
  (FFmpeg 9.0.2). The Y'CbCr files are converted with `zscale`.
* The page is written by [`build_page.py`](build_page.py) from
  [`web_compatibility_template.html`](web_compatibility_template.html), which reads each movie's codec string and
  the colors it should show.
* Submitted results go to a Google Sheet through [`google_sheet_collector.gs`](google_sheet_collector.gs); its
  header has the setup steps.
* To check a result by eye, [`tests/codec-color-compare.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/codec-color-compare.py)
  encodes two images with the same settings and writes a local A/B viewer (`tests/codec-color-compare/compare.html`)
  that plays the movies in the browser next to the source, or shows FFmpeg's decode of them. It is not published
  here, since the movies come to about 23MB.

{% include_relative web_compatibility.html %}
