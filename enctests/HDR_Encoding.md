---
layout: default
nav_order: 5.5
title: HDR Encoding
parent: Encoding Overview
---

# HDR Encoding

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

There are a lot of competing standards for [HDR](https://www.lightillusion.com/what_is_hdr.html), we are going to focus only on two due to their relative simplicity (not requiring dynamic metadata), and lack of licensing fees.

1. [HLG](https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma) encoding, developed by NHK and the BBC.  
2. [HDR10](https://en.wikipedia.org/wiki/HDR10)/PQ10 which uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer).

{:.note }  
For VFX/Animation review we are recommending using the PQ10 standard (essentially HDR10 without the master-display/max-cll parameters). We would recommend mastering to a known max luminance such as 1000 nit, and configuring OCIO to match that value, rather than relying on the monitor to apply a tonemap, at least for internal review. This also gives you a fair degree of flexibility in terms of which codecs you can use (essentially most 10+bit codecs should work), since you can use the [PQ10 Encoding](#pq10-ffmpeg-h265-encoding) approach.

## HDR10

HDR10 is defined as having:

* Transfer Function PQ  
* Bit depth: 10-bit  
* Color Primaries: rec2020  
* Static Metadata SMPTE ST-2086 \- (See below).

Unlike HLG it is not backwards compatible with older SDR displays. The static metadata gives hints to the display how to adjust the media for that display, however since its the same for the entire duration of the content, there may be issues where a dark scene followed by a light scene may not be interpreted correctly. Subsequent formats such as Dolby Vision and HDR10+ address these issues.

However, since we are typically talking about VFX review for individual shots, this format should be ok.

### PQ EOTF

So instead of specifying a gamma curve as the transfer function, the Perceptual Quantizer (PQ), standardized as [SMPTE ST2084](https://en.wikipedia.org/wiki/Perceptual_quantizer) represents luminance from 0 to 10000 nits. It still uses a power function to give more detail in the lower range. Office monitors are often in the 250-350 nit range.

In practice most HDR monitors are more likely to be in the 1000-2000 nit range, and even there they often try to limit the percentage of the overall screen that is full brightness This is done to manage power consumption and prevent overheating from thermal throttling.

### Choosing the OCIO display transform {#ocio-display-transform}

We take advantage of ACES, through OCIO, to convert the scene-referred EXRs to the PQ display space. With FFmpeg 8.1 or later, built with OCIO support (see [FFmpeg OCIO Filter](../FfmpegOcio.html)), the `ocio` filter does this inside `ffmpeg`, so the EXRs can be read directly with no intermediate files. The examples below all start this way; if your FFmpeg has no `ocio` filter, each section ends with the same encode made from PNG files written by `oiiotool`.

The filter takes three choices, and the second and third also determine what you should put in the HDR metadata (see [Master Display](#master-display) and [Max-CLL/Max-FALL](#max-cllmaxfall)):

| OCIO parameter | What it does | Link to the metadata |
| :--- | :--- | :--- |
| `input=ACES2065-1` | The colorspace of the source EXRs, or whatever your source imagery is using, such as ACEScg. | None. |
| `display=Rec.2100-PQ - Display` | The encoding of the output: Rec.2100 primaries with the PQ transfer function. Use `Rec.2100-HLG - Display` for [HLG](#hlg). | Sets the `-color_primaries bt2020` and `-color_trc smpte2084` tags (and `arib-std-b67` for HLG). |
| `view=ACES 2.0 - HDR 1000 nits (P3 D65)` | The view transform, which tone maps the scene to the peak luminance and gamut of the display you are mastering for: here 1000 nits, limited to P3. The examples use the ACES 2.0 config `studio-config-v4.0.0_aces-v2.0_ocio-v2.5` (OCIO 2.5 or later), which also has 500, 2000 and 4000 nit views. | The peak is your mastering display's peak luminance, so it is the maximum in `master-display` (`L(10000000,1)` is 1000 nits) and the upper bound for `max-cll`. The gamut is P3, which is what the [Master Display](#master-display) example lists. |

#### Setups for a P3 monitor {#ocio-setups}

There is no P3 video container: HDR10, PQ10 and HLG all carry BT.2020 primaries, so the file is always encoded and tagged as BT.2020. But almost every HDR mastering monitor covers P3 at most, not the full BT.2020 gamut, so we limit the colors *inside* that BT.2020 container to P3. A P3 limited view does exactly that. A Rec.2020 limited view leaves colors outside P3, which a P3 monitor then clips or gamut maps in its own way, so the review no longer matches what was approved. Use the Rec.2020 views only if your monitor really covers more than P3, which is rare.

View names differ between configs, so pin the config and, if you use your own, list its views first. The configs built into OCIO fall into two families, and older configs still load in newer versions of OCIO (the ACES 1.3 configs are all still built into OCIO 2.5):

| Config | P3 limited PQ setup |
| :--- | :--- |
| ACES 2.0 (`studio-config-v4.0.0_aces-v2.0_ocio-v2.5`, OCIO 2.5 or later), as in the examples | `display=Rec.2100-PQ - Display:view=ACES 2.0 - HDR 1000 nits (P3 D65)` in one filter. For HLG, the same view on `Rec.2100-HLG - Display`. |
| ACES 1.3 (e.g. `studio-config-v1.0.0_aces-v1.3_ocio-v2.1`, OCIO 2.1 or later) | The `P3 lim` views exist only on `ST2084-P3-D65 - Display`, which writes P3 primaries, so convert its output into the BT.2020 container with a second `ocio` filter (below). This config has no P3 limited HLG view. |

With an ACES 1.3 config, the P3 version of the filter is:

```console
-vf "ocio=input=ACES2065-1:display=ST2084-P3-D65 - Display:view=ACES 1.1 - HDR Video (1000 nits & P3 lim):format=rgb48,format=rgb48le,ocio=input=ST2084-P3-D65 - Display:output=Rec.2100-PQ - Display:format=rgb48,format=rgb48le,zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084"
```

Keep the format between the two `ocio` filters at `rgb48`: with a floating point format (`gbrpf32le`) the second filter fails with "Bit-depth mismatch" on FFmpeg 9.0.2. An earlier version of this page paired the `P3 lim` view with the `Rec.2100-PQ - Display`, which does not exist in these configs, and both `oiiotool` and the `ocio` filter reject it.

Measured with saturated ACES patches, by how far the output falls outside P3 (OCIO 2.5.1, FFmpeg 8.1 and 9.0.2; the encodes worked on both):

| Config and view | Colors outside P3 |
| :--- | :--- |
| ACES 2.0, `Rec.2100-PQ`, `HDR 1000 nits (P3 D65)` | No |
| ACES 1.3, `ST2084-P3-D65`, `1000 nits & P3 lim`, then converted to `Rec.2100-PQ` | No |
| ACES 2.0, `Rec.2100-PQ`, `HDR 1000 nits (Rec.2020)` | Yes |
| ACES 1.3, `Rec.2100-PQ`, `1000 nits & Rec.2020 lim` | Yes |

For PQ10, which carries no metadata, the view is simply what you tell the reviewers the content was mastered for: pick the one that matches the monitor, as the display will not tone map it for you. The rest of the filter chain is the same for every example here:

| Filter | What it does |
| :--- | :--- |
| `format=rgb48,format=rgb48le` | Keep the OCIO output as 16-bit RGB, so there is precision to spare for a 10-bit encode. The second `format` works around a crash in the FFmpeg 9.0 release; see [FFmpeg OCIO Filter](../FfmpegOcio.html). |
| `zscale=matrix=2020_ncl:range=limited:filter=lanczos` | Convert to limited range BT.2020 Y'CbCr; see [FFmpeg zscale Filter](../EncodeZscale.html). |
| `setparams=color_primaries=bt2020:color_trc=smpte2084` | Tag the frames, as the OCIO filter does not. |

If you also need to resize, do it before the `ocio` filter (it is the slow part), using `zscale` since `scale` clamps scene-linear values; see [Resizing before or after the OCIO filter](../FfmpegOcio.html#filter-order-resizing-before-or-after-the-ocio-filter).

### PQ10 FFmpeg H265 encoding

PQ10 is a simplified HDR format essentially HDR10 without the metadata. It uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer) aka SMPTE ST 2084 otherwise is somewhat similar to create as HLG, but there may be different reasons for choosing each.

```console
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
ffmpeg -framerate 24 -start_number 6700 -i sparks2/SPARKS_ACES_%05d.exr \
    -c:v libx265 -tag:v hvc1 \
    -vf "ocio=input=ACES2065-1:display=Rec.2100-PQ - Display:view=ACES 2.0 - HDR 1000 nits (P3 D65):format=rgb48,format=rgb48le,zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
    -color_range tv -color_trc smpte2084 -color_primaries bt2020 -colorspace bt2020nc \
    -pix_fmt yuv444p10le \
    sparks2_pq1000_444.mov
```

| :---- | :---- |
| \-c:v libx265 | Use the h265 encoder |
| \-tag:v hvc1 | Tag the file to enable playback with QuickTime Player |
| \-vf "ocio=...,zscale=...,setparams=..." | Apply the display transform, convert the full range RGB to limited range Y'CbCr with the BT.2020 non-constant luminance matrix, and tag the frames with the BT.2020 primaries and PQ transfer function (see [Choosing the OCIO display transform](#ocio-display-transform)). From FFmpeg 7.1 the `-color_primaries` and `-color_trc` flags are ignored, so `setparams` is what tags the file. |
| \-color\_range tv | Set the output range to be tv (limited) range. |
| \-color\_trc smpte2084 | smpte2084 is the PQ reference EOTF |
| \-color\_primaries bt2020 | Use the bt2020 color primaries |
| \-colorspace bt2020nc | Tagging the Y'CbCr as being encoded using the BT-2020 non-constant luminance. |
| \-pix\_fmt yuv444p10le | Y'CbCr 444, although 422 in many cases is also fine. |

In many cases this may be sufficient, particularly if you are using the ACES transforms that closely map to the maximum luminance of the review monitor (e.g. the 1000 nit view-transforms). It depends on how much the monitor can take advantage of the master-display parameters (see below).

This will also work for other codecs such as H.264, vp9, ProRes, AV1, OpenAPV although you would need to change or remove the -tag:v flag.

### PQ10 4:2:0 and chroma siting

4:2:0 is where chroma siting matters most. BT.2020 defines its 4:2:0 chroma as co-sited with the top-left luma sample (`topleft`), whereas H.264/HEVC readers assume `left` when nothing is signalled, and `scale` always centres the chroma. For HDR 4:2:0 you should therefore ask `zscale` for `chromal=topleft`, which both places the chroma and labels the frames so that `libx265` writes the matching chroma location (type 2) into the stream. 4:2:2 does not need this: horizontally it is co-sited either way, so leave `chromal` at its default. The measurements, what the specifications say, and how to check a player are on the [Chroma Siting](../ChromaSiting.html) page.

```console
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
ffmpeg -framerate 24 -start_number 6700 -i sparks2/SPARKS_ACES_%05d.exr \
    -c:v libx265 -tag:v hvc1 \
    -vf "ocio=input=ACES2065-1:display=Rec.2100-PQ - Display:view=ACES 2.0 - HDR 1000 nits (P3 D65):format=rgb48,format=rgb48le,zscale=matrix=2020_ncl:range=limited:chromal=topleft:filter=lanczos,format=yuv420p10le,setparams=color_primaries=bt2020:color_trc=smpte2084" \
    sparks2_pq1000_420.mov
```

| --- | --- |
| \-vf "ocio=...:format=rgb48,format=rgb48le" | Apply the display transform to the EXRs (see [Choosing the OCIO display transform](#ocio-display-transform)). |
| zscale=...:chromal=topleft | Convert to limited range BT.2020 Y'CbCr, siting the chroma co-sited with the top-left luma sample and labelling the frames `topleft`. |
| format=yuv420p10le | Subsample to 10-bit 4:2:0 here, after `zscale`, so the siting is applied by `zscale` rather than by a second conversion. |
| setparams=... | Tag the BT.2020 primaries and PQ transfer function. |

Check the result with `ffprobe -show_entries stream=chroma_location`, which should say `topleft` (measured on FFmpeg 9.0.2 with `libx265`). Be aware that some players ignore the tag and treat the file as `left`; see [Checking a player by eye](../ChromaSiting.html#checking-a-player). If you are delivering to a specification that asks for `left` (for example most streaming), leave `chromal` out.

### PQ10 without the OCIO filter

If your FFmpeg has no `ocio` filter, convert the EXRs to 16-bit PNG files first with `oiiotool`, which applies the same display transform, and encode those. Converting to PQ-1000 nits:

Converting to PQ-1000 Nits.

```console
# Assuming we are using OCIO 2.5 or higher
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr\
     --iscolorspace "ACES2065-1" --resize 1920x1014 \
       --ociodisplay "Rec.2100-PQ - Display" "ACES 2.0 - HDR 1000 nits (P3 D65)" \
       -d uint16 -o sparks2_pq1000/sparks2_pq1000.#.png
```

| --- | --- |
| \--iscolorspace "ACES2065-1" | Set the input colorspace to ACES2065-1 (or whatever your source imagery is using such as ACEScg) |
| \--ociodisplay "Rec.2100-PQ \- Display" "ACES 2.0 - HDR 1000 nits (P3 D65)" | The same display and view as the `ocio` filter above: a Rec.2100-PQ display at 1000 nits, with the gamut limited to P3. With an ACES 1.3 config, see [Setups for a P3 monitor](#ocio-setups). |
| \-d uint16 | Output as 16-bit file format. Typically you want at least 10-bit encodes, so to get the data to FFmpeg, this is a good start. |

<!---
name: test_pq10
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     matrix: bt2020nc
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 14
     - assert: less
       value: mean_error_10bit
       less: 2.0
     - assert: stringmatch
       value: color_primaries
       string: bt2020
     - assert: stringmatch
       value: color_transfer
       string: smpte2084
-->
```console
ffmpeg  \
    -r 30 -start_number 6700 -i sparks2_pq1000/sparks2_pq1000.%05d.png   \
    -c:v libx265   \
    -vf "zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
 -tag:v hvc1  \
    -color_range tv   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le \
    sparks2_pq1000_444.mov
```

| :---- | :---- |
| \-c:v libx265 | Use the h265 encoder |
| \-tag:v hvc1 | Tag the file to enable playback with QuickTime Player |
| \-vf "zscale=matrix=2020\_ncl:<br>range=limited:filter=lanczos,<br>setparams=color\_primaries=bt2020:<br>color\_trc=smpte2084" | Convert the full range RGB to limited range Y'CbCr with the BT.2020 non-constant luminance matrix, and tag the frames with the BT.2020 primaries and PQ transfer function. From FFmpeg 7.1 the `-color_primaries` and `-color_trc` flags are ignored, so `setparams` is what tags the file; see [FFmpeg zscale Filter](../EncodeZscale.html). |
| \-color\_range tv | Set the output range to be tv (limited) range. |
| \-color\_trc smpte2084 | smpte2084 is the PQ reference EOTF |
| \-color\_primaries bt2020 | Use the bt2020 color primaries |
| \-colorspace bt2020nc | Tagging the Y'CbCr as being encoded using the BT-2020 non-constant luminance. |
| \-pix\_fmt yuv444p10le | Y'CbCr 444, although 422 in many cases is also fine. |

### PQ 422 FFmpeg H265 encoding

Here we are going to add the additional Mastering Display metadata, in addition to the parameters used by PQ10.

```console
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
ffmpeg -framerate 24 -start_number 6700 -i sparks2/SPARKS_ACES_%05d.exr \
    -c:v libx265 \
    -vf "ocio=input=ACES2065-1:display=Rec.2100-PQ - Display:view=ACES 2.0 - HDR 1000 nits (P3 D65):format=rgb48,format=rgb48le,zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
    -color_range tv -color_trc smpte2084 -color_primaries bt2020 -colorspace bt2020nc \
    -pix_fmt yuv422p10le -tag:v hvc1 \
    -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400" \
    sparks2_pq1000_422.mov
```

x265's `hdr-opt=1` (HDR10 optimization) is left out: x265 only applies it to 10-bit 4:2:0 with BT.2020
primaries and matrix and PQ transfer, and otherwise disables it with a "Recommended Settings for HDR10-opt"
error. Add it for 10-bit 4:2:0 HDR10 deliveries.

The HDR metadata parameters really is what separates HDR10 from PQ10. The parameters below are:

* [Master Display](#master-display)  
* [Max-CLL/Max-FALL](#max-cllmaxfall)

It's worth noting that the definition below is for H264/H265, and may not be transferable to other codecs. We will attempt to document other appropriate settings. For H264/H265 the Master-display metadata is stored in the Supplemental Enhancement Information (SEI) block within the H264/H265 stream for the gory details see: [T-REC-H.265-202407-S](https://www.itu.int/rec/T-REC-H.265-202407-S/en)

#### Master Display {#master-display}

It is possible to create encoded media without additional metadata (essentially the PQ10 standard), but [T-REC-H.265-202407-S](https://www.itu.int/rec/T-REC-H.265-202407-S/en) defines some additional metadata fields which describe how the media was mastered, establishing the creative intent of the original media.

It's extremely rare to be doing the final color-correct on a monitor that fully supports rec2020, much more typical is one that has a P3 Gamut. The master-display parameter defines the colorimetry of the master display and the luminance range.

The display volume can be controlled with the [master-display](https://x265.readthedocs.io/en/stable/cli.html#cmdoption-master-display) x265 parameter, that can be passed through FFmpeg. We commonly see P3 values defined in a SEI info block (Supplemental Enhancement Information):

```console
master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)
```

This maps to:

```console
master-display=G( Gx, Gy )B( Bx, By )R( Rx, Ry )WP( Wx, Wy )L( max_nits, min_nits )
```

Where (Gx, Gy), (Bx, By) and r(Rx, Ry) define the primaries of the color volume, so [P3](https://en.wikipedia.org/wiki/DCI-P3) has a color primaries:

| | Rx | Ry | Gx | Gy | Bx | By |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Primary Colors | 0.680 | 0.320 | 0.265 | 0.690 | 0.150 | 0.060 |
| x 50000 | 34000 | 16000 | 13250 | 34500 | 7500 | 3000 |

This defines the x, y primaries, but you need to multiply the fractional value with "50000" to get the integer value.

The whitepoint is also defined with the same multiplication, which typically would be a D65 whitepoint (0.3127 , 0.3290 ) \= WP(15635,16450).

Lastly, the Luminance is defined as L(MAX\_NITS\*10000, MIN\_NITS\*10000) so for a typical 1000 nit display would be L(10000000,1). For Max luminance values are expected to be in the 50000 to 100000000 range, otherwise the value is considered unknown. 0 is also considered unknown. Similarly for the min luminance the range is considered to be in the 1-50000 range other values (including 0\) are considered unknown.

For reference the full rec2020 display values would be:

```console
master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1)
```

Reminder, this does NOT need to match the colorspace/primaries of the overall encoding container, you should not use this unless you actually Master the content on a rec2020 display. Using the P3 monitor values (or whatever display you are using) gives a clue to the display that it should not be using values outside of that gamut, this ensures that you get the colors that the creators expect. The problem is that this does assume quite a bit of the hardware interpreting these values, so in many cases it may be best to limit the source content as much as possible to a P3 gamut (or less).

#### Max-cll/MaxFALL

The [max-cll](https://x265.readthedocs.io/en/stable/cli.html#cmdoption-max-cll) parameter in h265 is actually two parameters:

* Maximum content light level (MaxCLL) \- this is the luminance of the brightest pixel (in Nits) of the entire video stream.  
* Maximum frame average light level (MaxFALL) \- this is the highest frame-average luminance in the video stream (in Nits): the average is taken over each frame, and the value is that of the brightest frame.

These are defined by the [Consumer Electronics Association 861.3 spec](https://manuals.plus/m/daba89fd26a25086fa5fbb4855bca4cf77e76cfecbf8bd748a139fcbdc220332.pdf).

Tools such as Resolve, provide ways to calculate these values see [here](https://www.youtube.com/watch?v=1HJi_ZP079w), but its not uncommon to use "typical" values, e.g. "1000,400". i.e. 1000 nit max brightness, 400 nit for the brightest frame's average. Although if you really don't know, you can use 0,0 to mean unknown.

#### What players do with the metadata {#player-behaviour}

The metadata is a description, not an instruction: what a player or display does with it varies, and it can
change a picture that is already within a known standard. In our tests on a Mac, metadata that matched the
content changed nothing, metadata that overstated the peak compressed the whole picture, and in the HDR Video
display preset no metadata had any effect. Recommended setup, so that the metadata changes the result as little
as possible:

1. Limit the content to what you can review, e.g. with an OCIO view to 1000 cd/m<sup>2</sup> and P3, in a
   BT.2020/PQ file (see [Choosing the OCIO display transform](#ocio-display-transform)).
2. Write metadata that matches it: the mastering display you limited to (P3-D65, `L(10000000,1)`), and the
   content's real MaxCLL/MaxFALL (or `0,0`). Do not overstate the peak: a player that uses it compresses the
   whole range to make room for highlights that are not there. Players disagree about what to assume with no
   metadata (1000 on the Mac, 10000 in libplacebo), so honest metadata is safer than none.
3. Review on a Mac in the HDR Video (P3-ST 2084) preset. On other players and on HDR TVs (with dynamic tone
   mapping off, e.g. HGIG), repeat the tests (below): a display that cannot reach the mastering peak has to compress
   something.

The test pages are on [HDR Display Tests](../tests/hdr-metadata-display/hdr-display-tests.html): start with
the [HDR display tests](https://encode.taurich.org/tests/hdr-metadata-display/simple/index.html) page, eight tests with one question
each.

<details markdown="block">
  <summary>Measurements: test charts, and what a Mac and libplacebo did</summary>

Two sets of test charts check what a player does with the metadata ([simple page](https://encode.taurich.org/tests/hdr-metadata-display/simple/index.html),
[full set](https://encode.taurich.org/tests/hdr-metadata-display/index.html)):

* [`tests/hdr_metadata_simple.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/hdr_metadata_simple.py)
  makes a page of eight tests, one question each (does the player use the mastering peak, MaxCLL, the mastering
  primaries; where is SDR white; does honest metadata change anything; are colors inside P3 changed), with a
  reference rendered by libplacebo for comparison.
* [`tests/hdr_metadata_display_chart.py`](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/blob/main/tests/hdr_metadata_display_chart.py)
  is the full set, including whether the player reads the HEVC SEI or the MP4 `mdcv`/`clli` boxes.

Both need FFmpeg 9.0 or later (`-mastering_display`, `-content_light`); the references also need libplacebo.
Serve the output folder over HTTP (e.g. `python3 -m http.server`) and open its `index.html`, and look at the
screen itself: tone mapping is often done after a screenshot is taken.

Results on a MacBook Pro (M2 Max, XDR screen), macOS 26.6, in Safari (the color tests also in Chrome):

| Display preset | SDR white | No metadata, or mastering 1000 | Mastering 4000 | Metadata used |
| :--- | :--- | :--- | :--- | :--- |
| Apple XDR Display (default), below full brightness | | steps visible to about 1500 cd/m<sup>2</sup> | | |
| Apple XDR Display (default), full brightness | PQ 160 | clips at 1000 | whole range compressed (steps visible to 3000) | mastering peak; MaxCLL and primaries ignored |
| HDR Video (P3-ST 2084) | PQ 100 | clips at 1000 | clips at 1000 | none |

* In the default preset the result depends on the brightness slider and on which window is active (it changed
  when the browser lost focus). Metadata only made a difference when it claimed more than the content holds:
  with honest metadata the picture was the same as with none.
* In the HDR Video preset (System Settings &rarr; Displays &rarr; Preset, on MacBook Pros with an XDR screen and
  the Pro Display XDR) PQ is shown at its true level up to 1000 cd/m<sup>2</sup>, and no metadata (mastering
  peak, MaxCLL, primaries, or none at all) changed the picture.
* Colors outside the screen's gamut are compressed, not clipped, in the video path, whatever the mastering
  primaries say; a PNG with the same colors is clipped.
* Colors at the very edge of P3 are not reproduced consistently. On the XDR screen (HDR Video preset), a 6%
  step in saturation at the P3 primaries was gone in a file tagged BT.2020 in Safari, Chrome and QuickTime. In
  the same colors tagged P3-D65 it was visible at the edge in Safari and Chrome, but in QuickTime only 5% in from
  the edge. On two SDR monitors, where macOS has to fit P3 into a smaller gamut anyway, the step was visible in
  both files. How far inside P3 the XDR effect reaches has not been measured; colors a little inside P3 looked
  the same in every case. A P3-D65 PQ file helps in some players, but HDR10 specifies BT.2020 primaries, so keep
  BT.2020 for deliverables.
* libplacebo (FFmpeg's `libplacebo` filter, mpv) uses all of it: with no metadata it assumes 10000 cd/m<sup>2</sup>,
  it clips at the mastering peak, it prefers the mastering peak to MaxCLL, and it uses the mastering primaries to
  decide how much to compress color (with BT.2020 primaries it shifts colors inside P3). Its peak detection
  (`peak_detect`, on by default) replaces the metadata with a measured peak.

</details>

### PQ 422 without the OCIO filter

The same encode from the PNG files made with `oiiotool` in [PQ10 without the OCIO filter](#pq10-without-the-ocio-filter):

<!---
name: test_pq1000
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     matrix: bt2020nc
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 9
     - assert: less
       value: mean_error_10bit
       less: 2.0
     - assert: stringmatch
       value: color_primaries
       string: bt2020
     - assert: stringmatch
       value: color_transfer
       string: smpte2084
-->
```console
ffmpeg  \
    -r 30 -start_number 6700 -i sparks2_pq1000/sparks2_pq1000.%05d.png   \
    -c:v libx265   \
    -vf "zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=smpte2084" \
    -color_range tv   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv422p10le  -tag:v hvc1  \
    -x265-params "colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400" \
    sparks2_pq1000_422.mov
```

### SVT-AV1

SVT-AV1 encoder also has command line parameters that need to be passed in:  

```console
ffmpeg \
    -i input.mp4 \
    -c:v libsvtav1 -pix_fmt yuv420p10le \
    -svtav1-params "preset=6:crf=28:enable-hdr=1:color-primaries=9:transfer-characteristics=16:matrix-coefficients=9:mastering-display=G(0.265,0.69)B(0.15,0.06)R(0.68,0.32)WP(0.3127,0.329)L(1000,0.0001):content-light=1000,400" \
    output.mov
 ```

The parameters are similar but the units are quite different. The mastering-display are in the original 0-1 primary values, with the Luminance in nits. It's also worth noting that SVT-AV1 only supports 4:2:0.

See:

* [svt-av1 parameters](https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Docs/Parameters.md#2-av1-metadata)

### VP9

To specify the display-master parameters with VP9, you need to use the  [mkvmerge](https://mkvtoolnix.download/doc/mkvmerge.html) tool, which is part of [mkvtoolnix](https://mkvtoolnix.download/) to apply the metadata once the file has been created. For more information, please see: [https://developers.google.com/media/vp9/hdr-encoding](https://developers.google.com/media/vp9/hdr-encoding)

It is currently not possible to add this metadata with FFmpeg, but this hopefully will be addressed.

### ProRes

ProRes does have the ability to add the Mastering Display Metadata, and while it seems ffmpeg can convert a file with it to another, preserving the metadata, there does not appear a way to add it to a newly created ProRes file (if you know how to, do please let us know).

An example of this file is the [NAS Sole Mates ASWF DPEL HDR Production Sample](https://dpel-assets.aswf.io/solemates/quicktime_media-sdr_hdr-v1.0.0.zip), and if you look at the file with ffprobe, you will see:

```console
    Side data:
      Mastering Display Metadata, has_primaries:1 has_luminance:1 r(0.6800,0.3200) g(0.2650,0.6900) b(0.1500 0.0600) wp(0.3127, 0.3290) min_luminance=0.000100, max_luminance=1000.000000
```

## HLG

[HLG](https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma) encoding, developed by NHK and the BBC. It's designed to be backwards compatible with the EOTF to SDR but with an extension for higher intensities. It has a more limited maximum peak brightness of 5000 nits rather than 10000 nits for PQ (although 1000 is more common).

It is also designed to adapt to the surrounding room light levels, unlike PQ which is fixed. The downside is that this adaptation could affect the media in unexpected ways. For this reason (and others) we do recommend using PQ10 instead.

### HLG OCIO display transform

As for PQ (see [Choosing the OCIO display transform](#ocio-display-transform)), the `ocio` filter converts the EXRs to the HLG display space inside `ffmpeg`, using the same 1000 nit P3 limited view on the `Rec.2100-HLG - Display`; the `oiiotool` version is at the end of this section.

### HLG 444 FFmpeg encoding

```console
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
ffmpeg -framerate 24 -start_number 6700 -i sparks2/SPARKS_ACES_%05d.exr \
    -c:v libx265 -tag:v hvc1 \
    -vf "ocio=input=ACES2065-1:display=Rec.2100-HLG - Display:view=ACES 2.0 - HDR 1000 nits (P3 D65):format=rgb48,format=rgb48le,zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=arib-std-b67" \
    -color_range tv -color_trc arib-std-b67 -color_primaries bt2020 -colorspace bt2020nc \
    -pix_fmt yuv444p10le \
    -x265-params "atc-sei=18:pic-struct=0" \
    sparks2_hlg_444.mov
```

#### Overall encode params

| --- | --- |
| -c:v libx265 | Use the h265 encoder |
| -tag:v hvc1 | Tag the file for playback on mac |

#### Encode media definition

| --- | --- |
| -color_range tv | Set the output range to be tv (limited) range. |
| -color_trc arib-std-b67 | ARIB STD-B67 is the HLG reference EOTF |
| -color_primaries bt2020 | Use the bt2020 color primaries |
| -colorspace bt2020nc | Tagging the Y'CbCr as being encoded using the BT-2020 non-constant luminance. |
| -pix_fmt yuv444p10le | Y'CbCr 4:4:4 10-bit output |

#### X265 parameters

The color tags come from the filter chain (`zscale` and `setparams`), which FFmpeg passes to libx265, so they are
not repeated in `-x265-params` (see [x265](https://x265.readthedocs.io/en/2.5/cli.html)). Setting them there as
well can disagree with the filter chain: with `transfer=bt2020-10`, FFmpeg 6.0 wrote `bt2020-10` into the stream
and 9.0 wrote `arib-std-b67`. See [HDR and -x265-params](../FFmpegChanges.html#hdr-and--x265-params).

| --- | --- |
| atc-sei=18 | Adds an alternative transfer characteristics SEI saying the transfer is HLG (ARIB STD-B67). |
| pic-struct=0 | Picture structure SEI: progressive frames. |

### HLG without the OCIO filter

Without the `ocio` filter, write 16-bit PNG files with `oiiotool` and encode those:

```console
# Assuming we are using OCIO 2.5 or higher
export OCIO=ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --resize 1920x1014 \
      --ociodisplay "Rec.2100-HLG - Display" "ACES 2.0 - HDR 1000 nits (P3 D65)" -d uint16 -o sparks2_hlg/sparks2_hlg.#.png
```

| --- | --- |
| \--ociodisplay "Rec.2100-HLG \- Display" "ACES 2.0 - HDR 1000 nits (P3 D65)" | The core colorspace conversion: a Rec.2100-HLG display at 1000 nits, with the gamut limited to P3. |
| -d uint16 | Output as 16-bit file format |

<!---
name: test_hlg
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     matrix: bt2020nc
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 14
     - assert: less
       value: mean_error_10bit
       less: 2.0
     - assert: stringmatch
       value: color_primaries
       string: bt2020
     - assert: stringmatch
       value: color_transfer
       string: arib-std-b67
-->
```console
ffmpeg -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
    -c:v libx265  -tag:v hvc1  \
    -vf "zscale=matrix=2020_ncl:range=limited:filter=lanczos,setparams=color_primaries=bt2020:color_trc=arib-std-b67" \
    -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le   \
    -x265-params "atc-sei=18:pic-struct=0" \
    sparks2_hlg_444.mov
```

### cICP/mDCV/cLLI in PNG

PNG files have transferable parameters for video encoding in two formats:  
[cICP](https://w3c.github.io/png/#cICP-chunk) which has the color primaries, transfer function and matrix coefficients based on the [ITU-T-H.273](https://w3c.github.io/png/#bib-itu-t-h.273) spec. FFmpeg 9.0 reads the `cICP` chunk as the frame's color tags (6.0 does not); see [Sources without tags](../EncodeZscale.html#sources-without-tags).

Similarly for HDR, the Mastering display color volume can be defined with the [mDCV](https://w3c.github.io/png/#mDCV-chunk) and [cLLI](https://w3c.github.io/png/#cLLI-chunk) metadata chunks in PNG.

Further Reading:

* [H.273 Specification.](https://www.itu.int/rec/T-REC-H.273-202107-I/en)  
* [St2084](https://pub.smpte.org/doc/st2084/20140816-pub/) \- SMPTE standard for PQ.  
* [What is HDR](https://www.lightillusion.com/what_is_hdr.html)  
* [Ultra HD Forum \- UHD Guidelines](https://ultrahdforum.org/wp-content/uploads/UHD-Guidelines-V2.4-Fall2020-1.pdf)  
* [High Dynamic Range Metadata for Apple Devices](https://developer.apple.com/av-foundation/High-Dynamic-Range-Metadata-for-Apple-Devices.pdf)  
* [BT.2100-3](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2100-3-202502-I!!PDF-E.pdf)  
* [https://pub.smpte.org/pub/st2086/st2086-2018.pdf](https://pub.smpte.org/pub/st2086/st2086-2018.pdf) \- Specification of Mastering Display Color Volume  
* [HDR Color Bars \- BT.2111](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2111-3-202505-I!!PDF-E.pdf)  
* [YouTube HDR Creators Guide](https://docs.google.com/document/u/1/d/1OHGOE4Ihv6SKazfiub_DP1lJbR9PdMMPOQYxPJQAES4/pub#h.3v06o2et6qxw)  
* [MovieLabs \- HDR/WCG Metadata encoding best practice](https://movielabs.com/md/practices/color/ManifestPractices_HDR_v1.0.pdf)  
* [Recommendations for Verifying HDR Subjective Testing Workflows](https://arxiv.org/pdf/2305.11858)
* [ITU-T Rec.H Sup.19 \- Usage of video signal code points](https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-H.Sup19-201910-S!!PDF-E&type=items)

I would like to thank Zach Lewis, Doug Walker, Michael De Caria and Vibhoothi for their help in creating this document.  
