---
layout: default
nav_order: 4.6
title: DNxHD Encoding
parent: Codec Comparisons
---


# DNxHD/DNxHR

Avid [DNxHD](https://en.wikipedia.org/wiki/Avid_DNxHD) ("Digital Nonlinear Extensible High Definition") is a lossy post-production codec that is intended for use for editing as well as a presentation format.

There are a number of pre-defined resolutions, frame-rates and bit-rates that are supported, see [AVID Resolutions](https://en.wikipedia.org/wiki/List_of_Avid_DNxHD_resolutions) for a list. However, we are going to focus on the DNxHR version of the codec, since it allows quite a bit more flexibility for larger image sizes than HD, more flexible frame rates and bit-rates of up toe 3730Mbit/s (See  [DNxHR-Codec-Bandwidth-Specifications](https://avid.secure.force.com/pkb/articles/en_US/White_Paper/DNxHR-Codec-Bandwidth-Specifications) ).


Supported pixel formats: yuv422p yuv422p10le yuv444p10le gbrp10le

Example encoding:

<!---
name: test_dnxhd_mov
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/chip-chart-1080-16bit-noicc-yuv422p10le.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -frames:v 200 -c:v dnxhd \
    -pix_fmt yuv422p10le -profile:v dnxhr_hqx -sws_flags spline+accurate_rnd+full_chroma_int \
    -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" \
    -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2 -y  outputfile.mov
```


## ffmpeg DNxHR Profiles

| Profile name | Profile description | Profile # | Pix Fmt | Bit Depth | Compression Ratio |
|:----------|:-----------|:-----------|:-----------|:-----------|:-----------|
| dnxhr_lb | Low Bandwidth | 1 | YUV 4:2:2 | 8 | 22:1 |
| dnxhr_sq | Standard Quality | 2 | YUV 4:2:2 | 8 | 7:1 |
| dnxhr_hq | High Quality | 3 | YUV 4:2:2 | 8 | 4.5:1 |
| dnxhr_hqx | High Quality | 4 | YUV 4:2:2 | 12 | 5.5: 1 |
| dnxhr_444 | DNxHR 4:4:4 | 5 | YUV 4:4:4 or RGB | 12 | 4.5:1 |

There really are not any significant flags to be used, changing bit-rate has no effect.

Note, the 12-bit depth does not appear to be supported by ffmpeg, since the encoding only allows 10-bit image data to be encoded.

## ffmpeg RGB support

<!---
name: test_prores444_rgb
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -y -r 24 -i inputfile.%04d.png -vframes 100 \
     -c:v dnxhd -profile:v dnxhr_444 \
     -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
     -color_primaries bt709 -color_range tv -color_trc bt709 -colorspace rgb \
     -pix_fmt gbrp10le outputfile.mov
```

## AVID friendly MXF

AVID prefer deliveries in MXF using the Avid Op-Atom format. Generating the Op-Atom format used to be a separate application, but its now integrated into ffmpeg.

<!---
name: test_prores444_mxf
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -y -r 24 -i inputfile.%04d.png -vframes 100 \
      -c:v dnxhd -profile:v dnxhr_444 \
      -metadata project="MY PROJECT" \
      -metadata material_package_name="MY CLIP" \
      -b:v 36M -f mxf_opatom outputfile.mxf
 ```

 See [https://johnwarburton.net/blog/?p=50731](https://johnwarburton.net/blog/?p=50731)

## DNxHD Profiles

For example below is an example of DNxHD at 175Mbps at yuv422p10 at resolution 1920x1080.

<!---
name: test_prores422_profile
sources: 
- sourceimages/chip-chart-1080-16bit-noicc.png.yml
comparisontest:
   - testtype: idiff
     compare_image: ../sourceimages/chip-chart-1080-16bit-noicc-yuv422p10le.png
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```
ffmpeg -y -r 24 -i inputfile.%04d.png -vframes 100 \
     -c:v dnxhd -b:v 175M \
     -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
     -color_primaries bt709 -color_range tv -color_trc bt709 -colorspace rgb \
     -pix_fmt yuv422p10 outputfile.mov
```

Other combinations of resolution, bitrate and format are:

| Resolution | Bit Rate | Pix Format |
|:----------|:-----------|:-----------|
| 1920x1080p|  175M  |  yuv422p10 |
| 1920x1080p|  185M  |  yuv422p10 |
| 1920x1080p|  365M  |  yuv422p10 |
| 1920x1080p|  440M  |  yuv422p10 |
| 1920x1080p|  115M  |  yuv422p |
| 1920x1080p|  120M  |  yuv422p |
| 1920x1080p|  145M  |  yuv422p |
| 1920x1080p|  240M  |  yuv422p |
| 1920x1080p|  290M  |  yuv422p |
| 1920x1080p|  175M  |  yuv422p |
| 1920x1080p|  185M  |  yuv422p |
| 1920x1080p|  220M  |  yuv422p |
| 1920x1080p|  365M  |  yuv422p |
| 1920x1080p|  440M  |  yuv422p |
| 1920x1080i|  185M  |  yuv422p10 |
| 1920x1080i|  220M  |  yuv422p10 |
| 1920x1080i|  120M  |  yuv422p |
| 1920x1080i|  145M  |  yuv422p |
| 1920x1080i|  185M  |  yuv422p |
| 1920x1080i|  220M  |  yuv422p |
| 1440x1080i|  120M  |  yuv422p |
| 1440x1080i|  145M  |  yuv422p |
| 1280x720p|  90M  |  yuv422p10 |
| 1280x720p|  180M  |  yuv422p10 |
| 1280x720p|  220M  |  yuv422p10 |
| 1280x720p|  90M  |  yuv422p |
| 1280x720p|  110M  |  yuv422p |
| 1280x720p|  180M  |  yuv422p |
| 1280x720p|  220M  |  yuv422p |
| 1280x720p|  60M  |  yuv422p |
| 1280x720p|  75M  |  yuv422p |
| 1280x720p|  120M  |  yuv422p |
| 1280x720p|  145M  |  yuv422p |
| 1920x1080p|  36M  |  yuv422p |
| 1920x1080p|  45M  |  yuv422p |
| 1920x1080p|  75M  |  yuv422p |
| 1920x1080p|  90M  |  yuv422p |
| 1920x1080p|  350M  |  yuv444p10, gbrp10 |
| 1920x1080p|  390M  |  yuv444p10, gbrp10 |
| 1920x1080p|  440M  |  yuv444p10, gbrp10 |
| 1920x1080p|  730M  |  yuv444p10, gbrp10 |
| 1920x1080p|  880M  |  yuv444p10, gbrp10 |
| 960x720p|  42M  |  yuv422p |
| 960x720p|  60M  |  yuv422p |
| 960x720p|  75M  |  yuv422p |
| 960x720p|  115M  |  yuv422p |
| 1440x1080p|  63M  |  yuv422p |
| 1440x1080p|  84M  |  yuv422p |
| 1440x1080p|  100M  |  yuv422p |
| 1440x1080p|  110M  |  yuv422p |
| 1440x1080i|  80M  |  yuv422p |
| 1440x1080i|  90M  |  yuv422p |
| 1440x1080i|  100M  |  yuv422p |
| 1440x1080i|  110M  |  yuv422p |

## TODO

   * The output sizes dont vary with different profiles, which seems wildly wrong.