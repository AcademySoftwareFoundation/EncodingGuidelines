---
layout: default
nav_order: 4.5
title: VP9 Encoding
parent: Codec Comparisons
---

# VP9

VP9 is an open-source and royalty free codec developed by the [Alliance for Open Media](https://trac.ffmpeg.org/wiki/Encode/VP9) (AOMedia), a non-profit industry consortium. It can be 20-50% higher efficiency than h264. 

General ffmpeg info on VP9 is [here](https://trac.ffmpeg.org/wiki/Encode/VP9), and on the encoder in general [https://developers.google.com/media/vp9/hdr-encoding](https://developers.google.com/media/vp9/hdr-encoding).

VP9 has browser support in:
   * Chrome - works on all configurations.
   * Edge - works on all configurations.
   * Firefox - works for 8-bit and 10-bit but fails with 12-bit.
   * Opera - works on all configurations.
   * Safari - works for 8-bit and 10-bit but fails on 10-bit 444 and 12-bit RGB.

VP9 is supported by mp4 and webm containers, no support exists for mov.

Outside of the web browser, VP9 support is pretty much limited to Davinci Resolve, Blender, ffmpeg and VLC.

The two codecs we will cover are:
* [libvpx-vp9](#libvpx-vp9)
* vp9-nvenc

## libvpx-vp9

libvpx-vp9 has a wide range of pixel formats:
yuv420p yuva420p yuv422p yuv440p yuv444p yuv420p10le yuv422p10le yuv440p10le yuv444p10le yuv420p12le yuv422p12le yuv440p12le yuv444p12le gbrp gbrp10le gbrp12le


Example encoding:

<!---
name: test_vp9
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/chip-chart-1080-16bit-noicc-yuv420p10le.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 -c:v libvpx-vp9 \
   -pix_fmt yuv420p10le -crf 22 -speed 2 -row-mt 1 -sws_flags spline+accurate_rnd+full_chroma_int \
   -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" \
   -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2 -quality good -b:v 0 \
     -y outputfile.mp4
```



## Recomended Flags

```
-crf 22 -quality good -b:v 0  -speed 2 -row-mt 1 
```

| --- | --- |
| **-crf 23** | This is the constant quality rate factor, controlling the default quality, similar to h264. The range is a little different to h264, so you may need to test. |
| *-quality good* | May require additional testing, but so far switching to *-quality best* increased the duration, but didn't increase the VMAF score (which is already pretty high with these values of crf). |
| -b:v 0 | Unlike with h264, you can set a constant quality rate factor unless it exceeds a specified bit-rate, if the bit-rate is set to 0, it ignores the bit-rate as a factor. |
| -speed 2 | This is also accessible as -cpu_used, it sets how efficient the compression will be. The default is 0, changing this will increase encoding speed at the expense of having some impact on quality and rate control accuracy. (See below). |
| -row-mt 1 | This enables row based multi-threading (see [here](https://trac.ffmpeg.org/wiki/Encode/VP9#rowmt)) which is not enabled by default. |


### CRF Comparison

Below is a comparison of different CRF rates, with -b:v 0 and -quality good

| ![](enctests/reference-results/vp9-crf-test-encode_time.png)  This is showing CRF values against encoding time. |
| ![](enctests/reference-results/vp9-crf-test-filesize.png) This is showing CRF values against file size. |
| ![](enctests/reference-results/vp9-crf-test-vmaf_harmonic_mean.png) This is showing CRF values against VMAF harmonic mean |
| ![](enctests/reference-results/vp9-crf-test-psnr_y_harmonic_mean.png) This is showing CRF values against psnr y harmonic mean |

### Speed Comparison

Below is a comparison of different speed rates, with and without the -row-mt 1 flag, with -crf 22, -b:v 0 and -quality good.

This shows that the -row-mt flag creates an almost identical result, but can be up to twice as quick (for -speed 0).
Also at least with this crf value, even with speed 4, the quality is still pretty good.

| ![](enctests/reference-results/vp9-speed-tests-encode_time.png)  This is showing speed against encoding time. |
| ![](enctests/reference-results/vp9-speed-tests-filesize.png) This is showing speed values against file size. |
| ![](enctests/reference-results/vp9-speed-tests-vmaf_harmonic_mean.png) This is showing speed values against VMAF harmonic mean |
| ![](enctests/reference-results/vp9-speed-tests-psnr_y_harmonic_mean.png) This is showing speed values against psnr y harmonic mean |
