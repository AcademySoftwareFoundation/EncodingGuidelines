---
layout: default
nav_order: 4.5
title: MJPEG Encoding
parent: Codec Comparisons
---

# MJPEG - Motion JPEG

[Motion JPEG](https://en.wikipedia.org/wiki/Motion_JPEG) has historically been quite common in the VFX industry, and is part of the default quicktime codecs, so is well supported everywhere.

While it does compress quickly, and maintains its quality fairly well, we would recommend other codecs at higher bit-depths such as vp9, h264 or h265 (or even Prores or DNxHD), which will also compress better than mjpeg.



## MJPEG

mjpeg has a limited range of pixel formats:
yuvj420p yuvj422p yuvj444p yuv420p yuv422p yuv444p


Example encoding:

<!---
name: test_mjpeg
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/chip-chart-1080-16bit-noicc-yuv444p10le.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 \
   -c:v mjpeg -crf 18 -pix_fmt rgb24 -vf "scale=in_range=full:out_range=full" -color_primaries bt709 -color_range pc -color_trc bt709 -colorspace rgb -qscale:v 3 -y "/Users/sam/git/EncodingGuidelines/enctests/rgb-encode/chimera_cars_srgb.-test_rgb-8bit_mjpeg.mp4"
   ffmpeg command: ffmpeg -start_number 2500 -i inputfile.%04d.png -vframes 200 \
   -c:v mjpeg -qscale:v 4 -pix_fmt yuv444p \
   -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 outputfile.mov

```


## Recomended Flags

| --- | --- |
| **-qscale:v 3** | This is the compression factor, which goes from 2 to 31 where 2 is the best quality. |


### qscale:v Comparison

Below is a comparison of different Qscale rates

| ![](enctests/reference-results/mjpeg-qscale-tests-encode_time.png)  This is showing qscale:v values against encoding time. |
| ![](enctests/reference-results/mjpeg-qscale-tests-filesize.png) This is showing qscale:v values against file size. |
| ![](enctests/reference-results/mjpeg-qscale-tests-vmaf_harmonic_mean.png) This is showing qscale:v values against VMAF harmonic mean |
| ![](enctests/reference-results/mjpeg-qscale-tests-psnr_y_harmonic_mean.png) This is showing qscale:v values against PSNR-Y harmonic mean |
