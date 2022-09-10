---
layout: default
nav_order: 6
title: HDR Encoding
parent: Encoding Overview
---

# HDR Encoding.

*This is under development*


## Frame prep

There are a two main encoding formats (https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma)[HLG] and (https://en.wikipedia.org/wiki/Perceptual_quantizer)[PQ] encoding. We are choosing HLG since its a slightly simpler format, and requires less additional metadata.

We take advantage of ACES to do the initial conversion to an intermediate format, which we are using png as the container.

```
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --resize 1920x1014 \
      --colorconvert acescg out_rec2020hlg1000nits -d uint16 -o sparks2_hlg/sparks2_hlg.#.png
```

| --- | --- |
|--colorconvert acescg out_rec2020hlg1000nits | This is the core colorspace conversion, out_rec2020hlg1000nits is an output colorspace conversion for rec2020 HLG at 1000 nit display |
| -d uint16 | Output as 16-bit file format |



## HLG 444 FFMPEG encoding

```
ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   \
    -color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
    -pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
    -c:v libx265   \
	-tag:v hvc1  \
    -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le   -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int  \
    -x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400'   \
    sparks2_hlg_444.mov
```

NOTE, this is a little different to other conversions (is this better?). We are defining up front what the source media is defined (e.g. `-color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc` ). 

### Source media definition.

| --- | --- |
| -color_range pc | Set the source range to be full-range |
| -color_trc arib-std-b67 | ARIB STD-B67 is the HLG reference EOTF |
| -color_primaries bt2020 | Use the bt2020 color primaries |
| -colorspace bt2020nc | NOT SURE ??? |
| -pix_fmt rgb48be | We are assuming 16-bit RGB imagery as input |


### Overall encode params

| --- | --- |
| -c:v libx265 | Use the h265 encoder |
| -tag:v hvc1 | Tag the file for playback on mac | 

### Encode media definition

| --- | --- |
| -color_range tv | Set the source range to be tv range. |
| -color_trc arib-std-b67 | ARIB STD-B67 is the HLG reference EOTF |
| -color_primaries bt2020 | Use the bt2020 color primaries |
| -colorspace bt2020nc | NOT SURE ??? |
| -pix_fmt yuv444p10le | YUV 444 10-bit output

### X265 parameters

We explicitly define the X265 parameters (see https://x265.readthedocs.io/en/2.5/cli.html )

| --- | --- |
| colorprim=bt2020 | Set the colorprimaries to bt2020 |
| transfer=arib-std-b67 | Set the ETOF to HLG (aka. arib-std-bt67 ) |
| colormatrix=bt2020nc | Use the bt2020 color primaries |
| range=limited | Set the source range to be tv range. |
| master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\) | SMPTE ST 2086 mastering display color volume SEI info, specified as a string which is parsed when the stream header Essentially setting the X,Y display primaries for rec2020 along with the Whitepoint, and the Max,min luminance values in units of 0.00001 NITs. See the above docs for more info. |
| max-cll=1000,400 | Set the Maximum content light level |


## HLG 420 FFMPEG encoding



```
ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   \
	-color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
	-c:v libx265   \
	-tag:v hvc1  \
	-color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt yuv420p10le   \
	-sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   \
	-x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400' \
	   sparks2_hlg_420.mov

```


## HLG 422 FFMPEG Encoding

```
ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   \
	-color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
	-c:v libx265   -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt yuv420p10le  \
	-tag:v hvc1  \
	-sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   \
	-x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400' \
	   sparks2_hlg_420_v2.mov
```


