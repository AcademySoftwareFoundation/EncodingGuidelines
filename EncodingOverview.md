---
layout: default
nav_order: 3
title: Encoding Overview
has_children: true

---

# Encoding Overview

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

This page walks through the steps from rendered frames to a review movie, with a short summary of each step and a
link to the page that explains it. If you just want a command that works, start with the
[Encoding Cheatsheet](Quickstart.html).

## The pipeline in five steps

### 1. Color-manage to display RGB {#1-colour-manage-to-display-rgb}

Convert the scene-linear renders (typically ACEScg EXRs) to the display you are reviewing on, with OCIO. Either do it
before FFmpeg and write 16-bit PNG or TIFF frames, see [Preparing Frames with oiiotool](OiiotoolConversion.html), or
do it inside FFmpeg 8.1 or later with the [OCIO filter](FfmpegOcio.html). For HDR deliveries, see
[HDR Encoding](enctests/HDR_Encoding.html).

### 2. Resize

Resizing shrinks fine detail, and the result depends on the filter and on the color space you resize in. Where in
the chain to resize, and in which space, is covered on the [Resizing](Resizing.html) page, which is still being
updated.

### 3. Read the frames into FFmpeg

Image sequences have no frame rate or start frame of their own, so you have to give both. See
[FFmpeg Frame Sequences Specification](FfmpegInputs.html).

### 4. Convert RGB to Y'CbCr

Most codecs store Y'CbCr, not RGB, and this is the step where FFmpeg most often gets the color wrong.

* [RGB to Y'CbCr Conversion](ColorPreservation.html) explains the problem and compares the converters. Start here.
* [zscale Conversion](EncodeZscale.html) covers the converter we recommend, its options, and what to check.
* [Chroma Siting](ChromaSiting.html) covers where the color samples go when you subsample to 4:2:2 or 4:2:0.
* [FFmpeg swscale Filter](EncodeSwsScale.html) is for when `zscale` is not available.
* [RGB Encoding](RGBEncoding.html) covers codecs that can skip the conversion entirely.

FFmpeg's color flags changed meaning in FFmpeg 7.1. If a command gives different results on a different version,
see [FFmpeg Version Changes](FFmpegChanges.html).

### 5. Encode, tag and add metadata

* [Codec Comparisons](Encoding.html): which codec to use for which job, with a page per codec.
* [Color Metadata and Web Color Preservation](WebColorPreservation.html): the color tags that tell a player, and in
  particular a web browser, how to display the file.
* [Adding Timecode and Editorial Workflow](EditorialWorkflow.html): timecode, reel names and Avid workflows.
* [Adding Metadata](EncodingMetadata.html): shot, version and other metadata in MOV, MP4, MXF and MKV.

## Other pages

* [Useful FFmpeg Filters](OtherFfmpegArgs.html): audio, concatenation, test patterns, stereo and other filters.
