---
layout: default
nav_order: 4.3
title: ProRes Encoding
parent: Codec Comparisons
---

# ProRes <a name="prores"></a>

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

There are four ProRes encoders, Prores, Prores_ks, Prores_aw and prores_videotoolbox, which is a hardware based MacOS M1 encoder/decoder (ffmpeg version 5 or higher).

If you are doing lighting or compositing reviews the recommendation is to use Prores_ks with -profile:v 3. If you are able we would recommend using [OpenAPV](https://academysoftwarefoundation.github.io/EncodingGuidelines/EncodeOpenAPV.html) or prores_videotoolbox over prores_ks, and look at a 444 10-bit or 12-bit encode, since they both give a superior result.

The two encoders we are reviewing are:

* [Prores_ks](#prores_ks)
* [videotoolbox_prores](#videotoolbox_prores) - only available on MacOS.

## Prores_ks

While ProRes does support up to 12 bits of resolution, prores_ks can only encode to 10-bits. It is able to decode to > 10 bits (see [https://github.com/ColorlabMD/Prores-BitDepth](https://github.com/ColorlabMD/Prores-BitDepth) )

Supported pixel formats: yuv422p10le yuv444p10le yuva444p10le

Example encode would look like:

<!---
name: test_proresks
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 3
     - assert: less
       value: mean_error_10bit
       less: 0.1
     - assert: less
       value: max_error_10bit
       less: 20
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: iec61966-2-1
-->
```console
ffmpeg -r 24 -start_number 100 -i inputfile.%04d.png \
         -pix_fmt yuv422p10le -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=iec61966-2-1" \
        -frames:v 100 -c:v prores_ks -profile:v 3 -vendor apl0 \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 \
        -y outputfile.mov
```

{: .note }
> These examples convert with `zscale`, which needs FFmpeg built with zimg; see [zscale Conversion](EncodeZscale.html). The `scale` filter (libswscale) puts white at 943 instead of 940 when converting a 10-bit or higher source to limited range. ProRes takes its colour tags from the frames, so `setparams` sets the primaries and transfer function; the `-color_*` flags are harmless but not needed. The automated comparison results further down this page were made with `scale`.

Options that can be used include:

| --- | --- |
| -profile:v 4444xq | Which prores encoding profile to use, see below |
| -qscale:v 3 | between values of 1-4, 0 being the same as specifying no qscale |
| -vendor apl0 | tricks the codec into believing its from an Apple codec. |
| -alpha_bits 16 | Allows you to specify how many bits to use for the alpha channel (default 16) |

Using this with the usual color space flags, seems to work well with the exception of ffmpeg itself is unable to read a ProRes file, and convert it to a still frame. It needs the flags:`-vf scale=in_color_matrix=bt709:out_color_matrix=bt709` added to the command to ensure the right input colorspace is recognized, e.g.:

```console
ffmpeg -i INPUTFILE.mov -compression_level 10 -pred mixed -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -frames:v 1 \
   -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 OUTPUTFILE.png
```

However, other encoders seem to be recognized correctly, so there is clearly some metadata missing. I did try using the prores_metadata filter to try adding some additional parameters, but it didn't seem to help.

```console
ffmpeg -i ./chip-chart-yuvconvert/basicnclc.mov -c copy \
   -bsf:v prores_metadata=color_primaries=bt709:color_trc=bt709:colorspace=bt709 \
   chip-chart-yuvconvert/basicnclcmetadata.mov
```

### Prores_ks profile

Profile values can be one of:

| Profile | Number | Chroma | Data Rate HD @ 29.97 | Description |
|:----------|:-----------|:-----------|:-----------|:-----------|
| proxy | 0 | 4:2:2 | 45Mbps | Proxy |
| lt | 1 | 4:2:2 | 102Mbps | Light |
| standard | 2 | 4:2:2 | 147Mbps | Standard |
| hq | 3 | 4:2:2 | 220Mbps | High Quality 10-bit |
| 4444 | 4 | 4:4:4:4 | 300Mbps | High quality mastering format, can support both RGB and Y'CrCb. Also supports a 16-bit mathematically lossless alpha. |
| 4444xq | 5 | 4:4:4:4 | 500MBps | High quality mastering format, supports up to 12 bit, and 16-bit alpha. ffmpeg will only generate up to 10-bit. |

See [https://support.apple.com/en-us/HT202410](https://support.apple.com/en-us/HT202410)

To compare them:

| ![](enctests/reference-results/prores-test-encode_time.png)  This is showing profile values against encoding time. | ![](enctests/reference-results/prores-test-filesize.png) This is showing profile values against file size. |
| ![](enctests/reference-results/prores-test-vmaf_harmonic_mean.png) This is showing profile values against VMAF harmonic mean (quality)|

### Prores_ks -qscale:v comparison

To help pick appropriate values with the -qscale:v , we have run the [Test Framework](enctests/README.html) through some of the [reference media](enctests/sources/enc_sources/README.html).

| ![](enctests/reference-results/prores-qscale-tests-encode_time.png)  This is showing qscale values against encoding time. |
| ![](enctests/reference-results/prores-qscale-tests-filesize.png) This is showing qscale values against file size. |
| ![](enctests/reference-results/prores-qscale-tests-vmaf_harmonic_mean.png) This is showing qscale values against VMAF harmonic mean (quality)|

## videotoolbox_prores

If you are on a MacOS M1 machine and are using ffmpeg 5.0 or higher, you can use the built in libraries to encode to ProRes using:

<!---
name: test_prores_videotoolbox
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the zscale result for this command on both test charts, FFmpeg 6.0 and 9.0, 2026-10-26. The same command with scale, or with no filter, fails white_error.
   - testtype: assertresults
     tests:
     - assert: between
       value: white_error_10bit
       between: [-1.5, 1.5]
     - assert: less
       value: p99_error_10bit
       less: 2
     - assert: less
       value: mean_error_10bit
       less: 0.1
     - assert: less
       value: max_error_10bit
       less: 5
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png  \
         -pix_fmt yuv422p10le \
        -vf "zscale=matrix=709:range=limited:filter=lanczos,format=yuv422p10le,setparams=color_primaries=bt709:color_trc=bt709" \
        -frames:v 100 -c:v prores_videotoolbox -profile:v 3  \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 outputfile.mov

```

NOTE, it does not appear to allow `-color_trc iec61966-2-1` (sRGB) -- so this needs more testing.

The `format=yuv422p10le` after `zscale` matters: `prores_videotoolbox` takes a semi-planar format (`p210le`) that
`zscale` cannot output, so without it FFmpeg leaves `zscale`'s output as RGB and converts with libswscale instead
(white at 943). With it, libswscale only repacks the planes. Tested on FFmpeg 6.0 and 9.0.

### Prores_videotoolbox profile

Similar to prores_ks, with the exception of xq. Profile values can be one of:

| Profile | Number | Chroma | Data Rate HD @ 29.97 | Description |
| :---------- | :----------- | :----------- | :----------- | :----------- |
| proxy | 0 | 4:2:2 | 45Mbps | Proxy |
| lt | 1 | 4:2:2 | 102Mbps | Light |
| standard | 2 | 4:2:2 | 147Mbps | Standard |
| hq | 3 | 4:2:2 | 220Mbps | High Quality 10-bit |
| 4444 | 4 | 4:4:4:4 | 300Mbps | High quality mastering format, can support both RGB and Y'CrCb. Also supports a 16-bit mathematically lossless alpha. |
| xq | 5 | 4:4:4:4 | 500MBps | High quality mastering format, supports up to 12 bit, and 16-bit alpha. ffmpeg will only generate up to 10-bit. |
