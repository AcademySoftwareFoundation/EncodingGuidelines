---
layout: default
nav_order: 6
title: HDR Encoding
parent: Encoding Overview
---

# HDR Encoding.

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

{: .warning }
This is currently under development, use at your own risk.

There are a lot of competing standards for [HDR](https://www.lightillusion.com/what_is_hdr.html), we are going to focus only on two due to their relative simplicity (not requiring dynamic metadata), and lack of licensing fees. 
1. [HLG](https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma) encoding, developed by NHK and the BBC.
2. [PQ10](https://en.wikipedia.org/wiki/HDR10) which uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer). 

## PQ10

Is the HDR format which is the HDR10 without the metadata. It uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer) aka SMPTE ST 2084 otherwise is somewhat similar to create as HLG, but there may be different reasons for choosing each.

### Frame prep

We take advantage of ACES to do the initial conversion to an intermediate format, which we are using png as the container.

Converting to PQ-1000 Nits.

```console
# Assuming we are using OCIO 2.1 or higher
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --iscolorspace "ACEScg" --resize 1920x1014 \
       --ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" \
       -d uint16 -o sparks2_pq2000/sparks2_pq2000.#.png
```

| --- | --- |
|--iscolorspace "ACEScg" | Set the input colorspace to ACEScg (or whatever your source imagery is using) |
|--ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" | This is the core colorspace conversion, This is using a 2100-PQ display, at 100 nits and rec2020 |
| -d uint16 | Output as 16-bit file format |

The other option built in for PQ is a config with 2000 nits -
``--ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (2000 nits & Rec.2020 lim)" `|`
| HLG |  |


### PQ 444 FFMPEG encoding

<!---
name: test_pq2000
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
     extracttemplate: "ffmpeg -y -i {newfile} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt2020:out_color_matrix=bt2020  -frames:v 1 {newpngfile}"
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg  \
    -r 30 -start_number 6700 -i sparks2_pq2000/sparks2_pq2000.%05d.png   \
    -c:v libx265   \
    -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020" \
	-tag:v hvc1  \
    -color_range tv   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le 
    -x265-params 'colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=2000,400'   \
    sparks2_pq2000_444.mov
```

#### Overall encode params

| --- | --- |
| -c:v libx265 | Use the h265 encoder |
| -tag:v hvc1 | Tag the file for playback on mac | 
| -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020"  | Make sure we treat the input and output color primaries to be bt2020. Without this, ffmpeg can assume the source is different, and apply a primary that shouldnt be there. |

#### Encode media definition

| --- | --- |
| -color_range tv | Set the source range to be tv range. |
| -color_trc smpte2084 | smpte2084 is the PQ reference EOTF |
| -color_primaries bt2020 | Use the bt2020 color primaries |
| -colorspace bt2020nc | Tagging the YcBCr as being encoded using the BT-2020 non-constant luminance. |
| -pix_fmt yuv444p10le | YUV 444 10-bit output

#### X265 parameters

We explicitly define the X265 parameters (see [x265](https://x265.readthedocs.io/en/2.5/cli.html) )

| --- | --- |
| colorprim=bt2020 | Set the colorprimaries to bt2020 |
| transfer=smpte2084 | Set the ETOF to PQ (aka. smpte2084 ) |
| colormatrix=bt2020nc | UTagging the YcBCr as being encoded using the BT-2020 non-constant luminance. |
| range=limited | Set the source range to be tv range. |
| master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\) | SMPTE ST 2086 mastering display color volume SEI info, specified as a string which is parsed when the stream header Essentially setting the X,Y display primaries for rec2020 along with the Whitepoint, and the Max,min luminance values in units of 0.00001 NITs. See the above docs for more info. |
| max-cll=2000,400 | Set the Maximum content light level (in this case 2000 nits = max content light level and 400 = the MaxFall - the maxiumum frame-average light level) |

## HLG

[HLG](https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma) encoding, developed by NHK and the BBC. Its designed to be backwards compatible with the EOTF to SDR but with an extension for higher intensities. It has a more limited maximum peak brightness of 5000 nits rather than 10000 nits for PQ. 

It is also designed to adapt to the surrounding room light levels, unlike PQ which is fixed. The downside is that this adaption could affect the media in unexpected ways.


### Frame prep



We take advantage of ACES to do the initial conversion to an intermediate format, which we are using png as the container.

```console
# Assuming we are using OCIO 2.1 or higher
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --resize 1920x1014 \
      ---ociodisplay "Rec.2100-HLG - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" -d uint16 -o sparks2_hlg/sparks2_hlg.#.png
```

| --- | --- |
|--ociodisplay "Rec.2100-HLG - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" | This is the core colorspace conversion, out_rec2020hlg1000nits is an output colorspace conversion for rec2020 HLG at 1000 nit display |
| -d uint16 | Output as 16-bit file format |



### HLG 444 FFMPEG encoding

<!---
name: test_hlg
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
     extracttemplate: "ffmpeg -y -i {newfile} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt2020:out_color_matrix=bt2020  -frames:v 1 {newpngfile}"
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
    -c:v libx265  -tag:v hvc1  \
    -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020" \
    -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le   \
    -x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400'   \
    sparks2_hlg_444.mov
```

#### Overall encode params

| --- | --- |
| -c:v libx265 | Use the h265 encoder |
| -tag:v hvc1 | Tag the file for playback on mac | 

#### Encode media definition

| --- | --- |
| -color_range tv | Set the source range to be tv range. |
| -color_trc arib-std-b67 | ARIB STD-B67 is the HLG reference EOTF |
| -color_primaries bt2020 | Use the bt2020 color primaries |
| -colorspace bt2020nc | Tagging the YcBCr as being encoded using the BT-2020 non-constant luminance. |
| -pix_fmt yuv444p10le | YUV 444 10-bit output

#### X265 parameters

We explicitly define the X265 parameters (see [x265](https://x265.readthedocs.io/en/2.5/cli.html) )

| --- | --- |
| colorprim=bt2020 | Set the colorprimaries to bt2020 |
| transfer=arib-std-b67 | Set the ETOF to HLG (aka. arib-std-bt67 ) |
| colormatrix=bt2020nc | UTagging the YcBCr as being encoded using the BT-2020 non-constant luminance. |
| range=limited | Set the source range to be tv range. |
| master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\) | SMPTE ST 2086 mastering display color volume SEI info, specified as a string which is parsed when the stream header Essentially setting the X,Y display primaries for rec2020 along with the White-point, and the Max,min luminance values in units of 0.00001 NITs. See the above docs for more info. |
| max-cll=1000,400 | Set the Maximum content light level (in this case 2000 nits = max content light level and 400 = the MaxFall - the maximum frame-average light level) |

TODO - We do need to understand if the max-cll and master-display parameters are even used for HLG display.


### HLG 420 FFMPEG encoding

<!---
name: test_hlg420
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
     extracttemplate: "ffmpeg -y -i {newfile} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt2020:out_color_matrix=bt2020  -frames:v 1 {newpngfile}"
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
	-c:v libx265   -tag:v hvc1  \
  -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020" \
	-color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt yuv420p10le   \
	-x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400' \
	   sparks2_hlg_420.mov

```


### HLG 422 FFMPEG Encoding

<!---
name: test_hlg422
sources: 
- sourceimages/smptehdbars_10.dpx.yml
comparisontest:
   - testtype: idiff
     extracttemplate: "ffmpeg -y -i {newfile} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt2020:out_color_matrix=bt2020  -frames:v 1 {newpngfile}"
   - testtype: assertresults
     tests:
     - assert: less
       value: max_error
       less: 0.00195
-->
```console
ffmpeg  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   \
	-c:v libx265   -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   \
	-pix_fmt yuv420p10le  -tag:v hvc1  \
    -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020" \
	-x265-params 'colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400' \
	   sparks2_hlg_420_v2.mov
```


Further Reading:
   * [H.273 Specification.](https://www.itu.int/rec/T-REC-H.273-202107-I/en)
   * [What is HDR](https://www.lightillusion.com/what_is_hdr.html)
   * [HDR Color Bars - BT.2111](https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.2111-2-202012-I!!PDF-E.pdf)
