---
layout: default
nav_order: 4.4
title: DNxHD Encoding
parent: Codec Comparisons
---


# DNxHD/DNxHR

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

Avid [DNxHD](https://en.wikipedia.org/wiki/Avid_DNxHD) ("Digital Nonlinear Extensible High Definition") is a lossy post-production codec that is intended for use for editing as well as a presentation format.

There are a number of pre-defined resolutions, frame-rates and bit-rates that are supported, see [AVID Resolutions](#dnxhd-profiles) for a list, and these are commonly requested by Editorial. However, we recommend using the DNxHR version of the codec, since it allows quite a bit more flexibility for larger image sizes than HD, more flexible frame rates and bit-rates of up to 3730Mbit/s (See  [DNxHR-Codec-Bandwidth-Specifications](https://avid.secure.force.com/pkb/articles/en_US/White_Paper/DNxHR-Codec-Bandwidth-Specifications) ).

Supported pixel formats: yuv422p yuv422p10le yuv444p10le gbrp10le

{: .note }
> The Y'CbCr examples on this page use `zscale` for the RGB to Y'CbCr conversion. Earlier versions used
> `scale` (libswscale), which on every FFmpeg version centres the 4:2:2 chroma while the formats here assume it is
> co-sited (half a pixel off, and in MXF labelled co-sited), and puts white at 943 instead of 940 from 10-bit
> sources. See [Chroma Siting](ChromaSiting.html) and [zscale Conversion](EncodeZscale.html). If your FFmpeg has no
> `zscale`, see the fallback in [FFmpeg Version Changes](FFmpegChanges.html#recommended-commands).

Example encoding:

<!---
name: test_dnxhd_mov
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
       less: 6
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 -c:v dnxhd \
    -pix_fmt yuv422p10le -profile:v dnxhr_hqx \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=bt709" \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 -y  outputfile.mov
```

## ffmpeg DNxHR Profiles

| Profile name | Profile description | Profile # | Pix Fmt | Bit Depth | Compression Ratio |
| :---------- | :----------- | :----------- | :----------- | :----------- | :----------- |
| dnxhr_lb | Low Bandwidth | 1 | YUV 4:2:2 (yuv422p) | 8 | 22:1 |
| dnxhr_sq | Standard Quality | 2 | YUV 4:2:2  (yuv422p) | 8 | 7:1 |
| dnxhr_hq | High Quality | 3 | YUV 4:2:2  (yuv422p) | 8 | 4.5:1 |
| dnxhr_hqx | High Quality, 10-bit | 4 | YUV 4:2:2  (yuv422p10) | 12 (*) | 5.5:1 |
| dnxhr_444 | DNxHR 4:4:4 | 5 | YUV 4:4:4 or RGB  (yuv444p10, gbrp10) | 12 (*) | 4.5:1 |

There really are not any significant flags to be used, since the quality is adjusted automatically to fit the compression ratio. Similarly the bit-rate flag has no impact on this. For more Bit-rate control, see the [DNxHD settings](#dnxhd-profiles) below.

(*) The 12-bit depth is what the codec can support, but does not appear to be supported by ffmpeg, since the encoding only allows 10-bit image data to be encoded.

### DNxHR resolutions

The DNxHR profiles accept any frame size from 256x120 upwards, and the bit-rate scales with the frame size. Tested
on FFmpeg 9.0.2:

* Sizes from 256x120 to 8192x4320 encoded with `dnxhr_hq`, including non-standard sizes such as 2048x858 and
  1998x1080; the other four profiles were checked at 4096x2160.
* Anything narrower than 256 or shorter than 120 is rejected: "Input dimensions too small, input must be at least
  256x120".
* We did not find an upper limit in the encoder: 16384x8640 ran out of memory rather than being refused.
* The width and height do not have to be even: 1921x1081 encoded and decoded at that size in FFmpeg, in 4:2:2 and
  4:4:4. We have not checked whether other applications (Avid, Resolve) accept odd sizes, so even dimensions are the
  safer choice for delivery.

This is the difference from DNxHD, which only accepts four frame sizes; see [DNxHD Profiles](#dnxhd-profiles).

NOTE, we have sometimes seen incompatibility issues with DNxHD Quicktimes not being read by Black Magic devices (e.g. the HyperDeck Studio), so there may be cases where you will need to use Resolve or Adobe Media Encoder to create compatible media.

## ffmpeg RGB support

The `dnxhr_444` profile can also store RGB directly (`gbrp10le`), with no Y'CbCr conversion:

<!---
name: test_dnxhd_rgb
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: ycbcr
     # Limits (10-bit code values): just above the result of this command, FFmpeg 6.0 and 9.0, 2026-10-26.
   - testtype: assertresults
     tests:
     - assert: less
       value: p99_error_10bit
       less: 1
     - assert: less
       value: mean_error_10bit
       less: 0.1
     - assert: less
       value: max_error_10bit
       less: 4
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -y -r 24 -i inputfile.%04d.png -frames:v 100 \
     -c:v dnxhd -profile:v dnxhr_444 \
     -vf "setparams=color_primaries=bt709:color_trc=bt709" \
     -color_primaries bt709 -color_range pc -color_trc bt709 -colorspace rgb \
     -pix_fmt gbrp10le outputfile.mov
```

## AVID friendly MXF

There are two types of MXF files, Op-atom and OP1a. Op-atom is designed for a single piece of media, whether it's audio or video, so a clip with both would be split into two sections. OP1a is a streaming format, where the audio and video streams are interleaved (see [MXF](https://web.archive.org/web/20121119151859/http://www.avid.com/static/resources/common/documents/mxf.pdf)).

### OP1a MXF

This is appropriate for deliveries where there is only a video component, not a mixed format.

<!---
name: test_dnxhd_op1a_mxf
sources: 
- sourceimages/smptehdbars_8.png.yml
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
       less: 6
     - assert: less
       value: mean_error_10bit
       less: 0.1
     - assert: less
       value: max_error_10bit
       less: 16
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -y -r 24 -start_number 2500 -i inputfile.%04d.png  -frames:v 100 \
    -pix_fmt yuv422p \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=bt709" \
    -c:v dnxhd -profile:v dnxhr_sq \
      -metadata project="MY PROJECT" \
      -metadata material_package_name="MY CLIP"  -timecode 01:00:20:00 \
    -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709  \
    outputfile.mxf
```

These can be imported directly into the AVID, although it will need to do some unpacking. For the fastest import you probably want to use OpAtom (see below). If you want to import with a reel-name, wrapping the file in an AAF (see [AAF Creation](EditorialWorkflow.html#aaf-creation)) is the recommended approach.

### Op-Atom MXF

AVID prefer deliveries in MXF using the Avid Op-Atom format. Generating the Op-Atom format used to be a separate application, but it's now integrated into ffmpeg. This works for a single piece of media (i.e. just video, or audio, not both).

<!---
name: test_dnxhd_opatom_mxf
sources: 
- sourceimages/smptehdbars_8.png.yml
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
       less: 6
     - assert: less
       value: mean_error_10bit
       less: 0.1
     - assert: less
       value: max_error_10bit
       less: 16
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -y -r 24 -i inputfile.%04d.png -frames:v 100 \
    -pix_fmt yuv422p \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=bt709" \
    -c:v dnxhd -profile:v dnxhr_sq \
      -metadata project="MY PROJECT" \
      -metadata material_package_name="MY CLIP"  -timecode 01:00:20:00 \
      -f mxf_opatom \
      -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
       outputfile.mxf
 ```

Typically you will want "MY CLIP" to match the outputfile, but it's not necessary. Also note, that if you want a reel-name to also be on the clip that you will need to wrap the MXF file in an AAF (see [AAF Creation](EditorialWorkflow.html#aaf-creation)) to get the extra metadata imported.

 See [https://johnwarburton.net/blog/?p=50731](https://johnwarburton.net/blog/?p=50731)

 Also see [Avid Media Composer Workflow](EditorialWorkflow.html#avid-media-composer-workflows) for other workflows such as AAF creation.

## DNxHD Profiles

Without a `dnxhr_*` profile, the encoder writes DNxHD, which is chosen by bit-rate (`-b:v`) and only exists for four
frame sizes: 1920x1080, 1440x1080, 1280x720 and 960x720. The frame size, bit-rate and pixel format have to match one
of the rows in the table below exactly. Anything else, including a missing `-b:v`, stops with "video parameters
incompatible with DNxHD" followed by the list of combinations your build accepts (FFmpeg 9.0.2: 2048x1080 and
3840x2160 at 175M were rejected, as was 1920x1080 at 100M). For any other frame size use DNxHR; see
[DNxHR resolutions](#dnxhr-resolutions).

Below is an example of DNxHD at 175Mbps at yuv422p10 at resolution 1920x1080.

<!---
name: test_dnxhd_profile
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
       less: 0.3
     - assert: less
       value: max_error_10bit
       less: 14
     - assert: stringmatch
       value: color_primaries
       string: bt709
     - assert: stringmatch
       value: color_transfer
       string: bt709
-->
```console
ffmpeg -y -r 24 -i inputfile.%04d.png -frames:v 100 \
    -vf "zscale=matrix=709:range=limited:filter=lanczos,setparams=color_primaries=bt709:color_trc=bt709" \
    -pix_fmt yuv422p10 -c:v dnxhd -b:v 175M \
     -color_primaries bt709 -color_range tv -color_trc bt709 -colorspace bt709 \
      outputfile.mov
```

Other combinations of resolution, bitrate and format are below. They are the list FFmpeg prints (9.0.2), grouped
by Avid compression ID (CID), with the bytes per frame from `libavcodec/dnxhddata.c`.

Each variant writes a fixed number of bytes per frame, and `-b:v` only chooses the variant: FFmpeg does not check the
frame rate. The real data rate is the frame size times your frame rate, so `-b:v 185M` at 24 fps gives 176 Mb/s,
and `-b:v 145M` at 50 fps gives 242 Mb/s (measured, 9.0.2). The frame rates are the ones each `-b:v` value is named
after (bytes per frame times frame rate). The 960x720 and 1440x1080 values do not line up with standard frame rates,
so they are left blank.

| Resolution | CID | Pix Format | Bytes per frame | `-b:v` (frame rate) |
| :--- | :--- | :--- | ---: | :--- |
| 1920x1080p | 1235 | yuv422p10 | 917504 | 175M (23.98, 24), 185M (25), 365M (50), 440M (59.94, 60) |
| 1920x1080p | 1238 | yuv422p | 917504 | 175M (23.98, 24), 185M (25), 220M (29.97), 365M (50), 440M (59.94, 60) |
| 1920x1080p | 1237 | yuv422p | 606208 | 115M (23.98, 24), 120M (25), 145M (29.97), 240M (50), 290M (59.94, 60) |
| 1920x1080p | 1253 | yuv422p | 188416 | 36M (23.98, 24, 25), 45M (29.97), 75M (50), 90M (59.94, 60) |
| 1920x1080p | 1256 | yuv444p10, gbrp10 | 1835008 | 350M (23.98, 24), 390M (25), 440M (29.97), 730M (50), 880M (59.94, 60) |
| 1920x1080i | 1241 | yuv422p10 | 917504 | 185M (25), 220M (29.97) |
| 1920x1080i | 1243 | yuv422p | 917504 | 185M (25), 220M (29.97) |
| 1920x1080i | 1242 | yuv422p | 606208 | 120M (25), 145M (29.97) |
| 1440x1080i | 1244 | yuv422p | 606208 | 120M (25), 145M (29.97) |
| 1280x720p | 1250 | yuv422p10 | 458752 | 90M (23.98, 24, 25), 180M (50), 220M (59.94, 60) |
| 1280x720p | 1251 | yuv422p | 458752 | 90M (23.98, 24, 25), 110M (29.97), 180M (50), 220M (59.94, 60) |
| 1280x720p | 1252 | yuv422p | 303104 | 60M (23.98, 24, 25), 75M (29.97), 120M (50), 145M (59.94, 60) |
| 960x720p | 1258 | yuv422p | 212992 | 42M, 60M, 75M, 115M |
| 1440x1080p | 1259 | yuv422p | 417792 | 63M, 84M, 100M, 110M |
| 1440x1080i | 1260 | yuv422p | 835584 | 80M, 90M, 100M, 110M (FFmpeg marks this one experimental: add `-strict experimental`) |

FFmpeg has no 10-bit 1920x1080p variant at 29.97 (`-b:v 220M` with `yuv422p10` is rejected); use 8-bit or DNxHR.
The interlaced (`i`) variants are only chosen with `-flags +ildct`.

## See Also

* <https://dovidenko.com/2019/999/ffmpeg-dnxhd-dnxhr-mxf-proxies-and-optimized-media.html>
* <https://askubuntu.com/questions/907398/how-to-convert-a-video-with-ffmpeg-into-the-dnxhd-dnxhr-format>
