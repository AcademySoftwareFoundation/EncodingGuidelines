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

There are four ProRes encoders, `prores`, `prores_ks`, `prores_aw` and `prores_videotoolbox`, which is a hardware based MacOS M1 encoder/decoder (ffmpeg version 5 or higher).

If you are doing lighting or compositing reviews the recommendation is to use Prores_ks with -profile:v 3. If you are able we would recommend using [OpenAPV](EncodeOpenAPV.html) or prores_videotoolbox over prores_ks, and look at a 444 10-bit or 12-bit encode, since they both give a superior result.

The two encoders we are reviewing are:

* [Prores_ks](#prores_ks)
* [prores_videotoolbox](#prores_videotoolbox) - only available on MacOS.

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
| -qscale:v 3 | A fixed quantiser for the whole frame, 1 (highest quality) to 64; above 64 the encoder stops with "too large quantiser, maximum is 64". 0, or leaving it out, uses the profile's rate control instead (see below). |
| -vendor apl0 | tricks the codec into believing its from an Apple codec. |
| -alpha_bits 16 | Allows you to specify how many bits to use for the alpha channel (default 16) |

To extract a still from a ProRes file, convert it with `zscale`:

```console
ffmpeg -i INPUTFILE.mov -frames:v 1 -vf "zscale,format=gbrp16le" -pix_fmt rgb48be OUTPUTFILE.png
```

Decoding ProRes to 16-bit PNG and comparing with the RGB it was made from (errors in 10-bit code values, away from
edges; `prores_ks` at `-qscale:v 1`, tagged BT.709):

| Conversion | 422 HQ | 4444 |
| :--- | :--- | :--- |
| No filter | 12.3 max, 1.26 mean | 7.8 max, 1.27 mean |
| `scale=in_color_matrix=bt709:out_color_matrix=bt709`, with `-sws_flags spline+accurate_rnd+full_chroma_int` | 19.6 max, 1.27 mean | 7.8 max, 1.27 mean |
| `zscale,format=gbrp16le` | 5.5 max, 0.35 mean | 4.1 max, 0.35 mean |

The results were identical on 6.1.6, 7.0, 7.1.5, 8.1, 9.0.2 and a 9.1 development build. Telling `scale` the matrix gains nothing for a tagged file, and libswscale also
puts the chroma of 4:2:2 ProRes in the wrong place ([Chroma Siting](ChromaSiting.html#reading-back-to-rgb)).

`zscale` needs the file to say what its matrix is, and gives no output for a file with no tags. You can add them to
an existing ProRes file without re-encoding:

```console
ffmpeg -i INPUTFILE.mov -c copy \
   -bsf:v prores_metadata=color_primaries=bt709:color_trc=bt709:colorspace=bt709 \
   OUTPUTFILE.mov
```

`zscale` then accepts the file (tested on 6.1.6, 7.1.5 and 9.0.2; of those, only 9.0.2's `ffprobe` shows the new
tags). This only changes the label, so use it only if the pixels really are BT.709: an encode with no colour settings
and no conversion filter is converted as BT.601.

### Prores_ks profile

Profile values can be one of:

| Profile | Number | Chroma | Data Rate HD @ 29.97 | Description |
|:----------|:-----------|:-----------|:-----------|:-----------|
| proxy | 0 | 4:2:2 | 45Mbps | Proxy |
| lt | 1 | 4:2:2 | 102Mbps | Light |
| standard | 2 | 4:2:2 | 147Mbps | Standard |
| hq | 3 | 4:2:2 | 220Mbps | High Quality 10-bit |
| 4444 | 4 | 4:4:4:4 | 330Mbps | High quality mastering format, can support both RGB and Y'CbCr. Also supports a 16-bit mathematically lossless alpha. |
| 4444xq | 5 | 4:4:4:4 | 500Mbps | High quality mastering format, supports up to 12 bit, and 16-bit alpha. ffmpeg will only generate up to 10-bit. |

See [https://support.apple.com/en-us/HT202410](https://support.apple.com/en-us/HT202410)

To compare them:

| ![](enctests/reference-results/prores-test-encode_time.png)  This is showing profile values against encoding time. | ![](enctests/reference-results/prores-test-filesize.png) This is showing profile values against file size. |
| ![](enctests/reference-results/prores-test-vmaf_harmonic_mean.png) This is showing profile values against VMAF harmonic mean (quality)|

### Prores_ks -qscale:v comparison

Without `-qscale:v`, `prores_ks` aims at a data rate set by the profile, and picks a quantiser for each slice (for
422 HQ and above it starts in the range 1-6, and goes higher only where a slice would not otherwise fit). With
`-qscale:v N` it uses quantiser N everywhere and ignores the profile's data rate, so the profile then only chooses
the quantisation matrix and what the file says it is. N is 1 to 64, and higher values are coarser.

Single 1920x1080 frames from two of the Chimera clips, with the data rate as it would be at 24 fps and the PSNR of
Y' (FFmpeg 9.0.2; 6.1.6 gave the same):

| `-qscale:v` | 422 HQ, data rate | 422 HQ, PSNR Y' | 4444, data rate | 4444, PSNR Y' |
| :--- | ---: | ---: | ---: | ---: |
| not set | 186 Mb/s | 54.0 - 54.2 dB | 278 Mb/s | 57.2 dB |
| 1 | 368 - 398 Mb/s | 64.8 dB | 431 - 464 Mb/s | 64.5 dB |
| 2 | 237 - 266 Mb/s | 59.4 - 59.6 dB | 272 - 301 Mb/s | 59.3 - 59.4 dB |
| 4 | 132 - 164 Mb/s | 54.5 - 54.8 dB | 154 - 183 Mb/s | 54.4 - 54.7 dB |
| 9 | 65 - 90 Mb/s | 49.9 - 50.2 dB | 75 - 98 Mb/s | 49.8 - 50.1 dB |
| 13 | 48 - 71 Mb/s | 47.9 - 48.1 dB | 54 - 77 Mb/s | 47.9 - 48.1 dB |

So for 422 HQ, leaving `-qscale:v` out is roughly equivalent to `-qscale:v 4`, but with a steady data rate.
`-qscale:v 9` is well below the HQ data rate, closer to ProRes 422 LT.

To help pick appropriate values with the -qscale:v , we have run the [Test Framework](enctests/README.html) through some of the [reference media](enctests/sources/enc_sources/README.html).

| ![](enctests/reference-results/prores-qscale-tests-encode_time.png)  This is showing qscale values against encoding time. |
| ![](enctests/reference-results/prores-qscale-tests-filesize.png) This is showing qscale values against file size. |
| ![](enctests/reference-results/prores-qscale-tests-vmaf_harmonic_mean.png) This is showing qscale values against VMAF harmonic mean (quality)|

## prores_videotoolbox {#prores_videotoolbox}

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

Similar to prores_ks, except that the XQ profile is called `xq` rather than `4444xq`. Profile values can be one of:

| Profile | Number | Chroma | Data Rate HD @ 29.97 | Description |
| :---------- | :----------- | :----------- | :----------- | :----------- |
| proxy | 0 | 4:2:2 | 45Mbps | Proxy |
| lt | 1 | 4:2:2 | 102Mbps | Light |
| standard | 2 | 4:2:2 | 147Mbps | Standard |
| hq | 3 | 4:2:2 | 220Mbps | High Quality 10-bit |
| 4444 | 4 | 4:4:4:4 | 330Mbps | High quality mastering format, can support both RGB and Y'CbCr. Also supports a 16-bit mathematically lossless alpha. |
| xq | 5 | 4:4:4:4 | 500Mbps | High quality mastering format, supports up to 12 bit, and 16-bit alpha. |
