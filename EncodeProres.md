---
layout: default
nav_order: 4.2
title: Prores Encoding
parent: Encoding Overview
---

# ProRes <a name="prores"></a>
There are four Prores encoders, Prores, Prores_ks, Prores_aw and now with ffmpeg 5 VideoToolBox Prores, which is a hardware based OSX M1 encoder/decoder.

From [https://trac.ffmpeg.org/wiki/Encode/VFX](https://trac.ffmpeg.org/wiki/Encode/VFX) the recommendation is to use Prores_ks with -profile:v 3 and the qscale of 11

Options that can be used include:

-profile:v values can be one of.
* proxy (0)
* lt (1)
* standard (2)
* hq (3)
* 4444 (4)
* 4444xq (5)

-qscale:v between values of 9 - 13 give a good result, 0 being best, see below for some wedge tests.

-vendor apl0 - tricks the codec into believing its from an Apple codec.

Example encode would look like:

<!---
name: test_proresks
sources: 
- sourceimages/chip-chart-1080-noicc.png.yml
-->
```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
        -vframes 100 -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 outputfile.mov
```

Using this with the usual color space flags, seems to work well with the exception of ffmpeg itself is unable to read a prores file, and convert it to a still frame. It needs the flags:`-vf scale=in_color_matrix=bt709:out_color_matrix=bt709` added to the command to ensure the right input colorspace is recognised, e.g.:


<!---
name: test_proresks2
sources: 
- sourceimages/chip-chart-1080-noicc.png.yml
-->
```console
ffmpeg -i INPUTFILE.mov -compression_level 10 -pred mixed -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
   -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 OUTPUTFILE.png
```

However, other encoders seem to be recognised correctly, so there is clearly some metadata missing. I did try using the prores_metadata filter to try adding some additional parameters, but it didn't seem to help.

```console
ffmpeg -i ./chip-chart-yuvconvert/basicnclc.mov -c copy \
   -bsf:v prores_metadata=color_primaries=bt709:color_trc=bt709:colorspace=bt709 \
   chip-chart-yuvconvert/basicnclcmetadata.mov
```

If you are on a OSX M1 machine and are using ffmpeg 5.0 or higher, you can use the built in libraries to encode to prores using:

```console
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
        -vframes 100 -c:v prores_videotoolbox -profile:v 3 -pix_fmt yuv422p \
        -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 outputfile.mp4

```

NOTE, it does not appear to allow `-color_trc iec61966-2-1` (sRGB) -- so this needs more testing.

#### Prores_ks -qscale:v comparison.

To help pick appropriate values with the -qscale:v , we have run the [Test Framework](enctests/README.html) through some of the [reference media](enctests/sources/enc_sources/README.html).

| ![](enctests/reference-results/prores-test-encode_time.png)  This is showing qscale values against encoding time. |
| ![](enctests/reference-results/prores-test-filesize.png) This is showing qscale values against file size. |
| ![](enctests/reference-results/prores-test-vmaf_harmonic_mean.png) This is showing qscale values against VMAF harmonic mean |