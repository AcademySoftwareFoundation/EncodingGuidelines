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
2. [HDR10](https://en.wikipedia.org/wiki/HDR10)/PQ10 which uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer).

{:.note }  
For VFX/Animation review we are recommending using the PQ10 standard (essentially HDR10 without the master-display/max-cll parameters). We would recommend mastering to a known max luminance such as 1000 nit, and configuring OCIO to match that value, rather than relying on the monitor to apply a tonemap, at least for internal review. This also gives you a fair degree of flexibility in terms of which codecs you can use (essentially most 10+bit codecs should work), since you can use the [PQ10 Encoding](#pq10-ffmpeg-encoding) approach.

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

In practice most HDR monitors are more likely to be in the 1000-2000 range, and even there they often try to limit the percentage of the overall screen that is full brightness This is done to manage power consumption and prevent overheating from thermal throttling.

### Frame prep

We take advantage of ACES to do the initial conversion to an intermediate format, which we are using png as the container.

Converting to PQ-1000 Nits.

```console
# Assuming we are using OCIO 2.1 or higher
export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1
oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr\
     --iscolorspace "ACES2065-1" --resize 1920x1014 \
       --ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (1000 nits & P3 lim)" \
       -d uint16 -o sparks2_pq2000/sparks2_pq1000.#.png
```

| --- | --- |
| \--iscolorspace "ACES2065-1" | Set the input colorspace to ACES2065-1 (or whatever your source imagery is using such as ACEScg) |
| \--ociodisplay "Rec.2100-PQ \- Display" "ACES 1.1 \- HDR Video (1000 nits & P3 lim)" | This is the core colorspace conversion, This is using a 2100-PQ display, at 1000 nits and while it is a full rec2020 gamut (as defined by the rec.2100 spec) the gamut is limited to P3. Since few displays are currently above P3 gamut, this is a fairly typical. Its also worth noting, P3 does not exist as a "Video Gamut" hence why the larger rec2020 is used. |
| \-d uint16 | Output as 16-bit file format. Typically you want at least 10-bit encodes, so to get the data to ffmpeg, this is a good start. |

The other option built in for PQ is a config with 2000 nits \-  
\--ociodisplay "Rec.2100-PQ \- Display" "ACES 1.1 \- HDR Video (2000 nits & Rec.2020 lim)"  
There is also a 4000 nit max and P3 target gamuts available in the OCIO config mentioned above. And if you are willing to use OCIO 2.5, there are improved HDR view transforms based on ACES 2.0. This has 500, 1000, 2000, 4000 nit max luminance and P3 and Rec.2020 target gamuts.

### PQ10 FFMPEG encoding

PQ10 is a simplified HDR format essentially HDR10 without the metadata. It uses the [PQ EOTF](https://en.wikipedia.org/wiki/Perceptual_quantizer) aka SMPTE ST 2084 otherwise is somewhat similar to create as HLG, but there may be different reasons for choosing each.


<!---
name: test_pq10
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
    -r 30 -start_number 6700 -i sparks2_pq1000/sparks2_pq1000.%05d.png   \
    -c:v libx265   \
    -vf "scale=in_range=full:in_color_matrix=bt2020:out_range=tv:out_color_matrix=bt2020" \
	-tag:v hvc1  \
    -color_range tv   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc  \
    -pix_fmt yuv444p10le  -tag:v hvc1 \
    sparks2_pq1000_444.mov
```



| :---- | :---- |
| \-c:v libx265 | Use the h265 encoder |
| \-tag:v hvc1 | Tag the file to enable playback with QuickTime Player |
| \-vf "scale=in\_range=full:in\_color\_matrix=bt2020:out\_range=tv:out\_color\_matrix=bt2020" | Make sure we treat the input and output color primaries to be bt2020. Without this, ffmpeg can assume the source is different, and apply a primary that shouldn't be there. |
| \-color\_range tv | Set the source range to be tv range. |
| \-color\_trc smpte2084 | smpte2084 is the PQ reference EOTF |
| \-color\_primaries bt2020 | Use the bt2020 color primaries |
| \-colorspace bt2020nc | Tagging the YcBCr as being encoded using the BT-2020 non-constant luminance. |
| \-pix\_fmt yuv444p10le | YCrCb 444, although 422 in many cases is also fine. |


In many cases this may be sufficient, particularly if you are using the ACES transforms that closely map to the maximum luminance of the review monitor (e.g. the 1000 nit view-transforms). It depends on how much the monitor can take advantage of the master-display parameters (see below).

### PQ 444 FFMPEG encoding

Here we are going to add the additional Mastering Display metadata, in addition to the parameters used by PQ10.

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
    -x265-params "hdr-opt=1:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):max-cll=1000,400"  -tag:v hvc1 \
    sparks2_pq2000_444.mov
```

The HDR metadata parameters really is what separates HDR10 from PQ10. The parameters below are:

* [Master Display](#master-display)  
* [Max-CLL/Max-FALL](#max-cllmaxfall)

It's worth noting that the definition below is for H264/H265, and may not be transferable to other codecs. We will attempt to document other appropriate settings. For H264/H265 the Master-display metadata is stored in the Supplemental Enhancement Information (SEI) block within the H264/H265 stream for the gory details see: [T-REC-H.265-202407-I](https://www.itu.int/rec/T-REC-H.265-202407-I) 

##### Master Display {#master-display}

It is possible to create encoded media without additional metadata (essentially the PQ10 standard), but [T-REC-H.265-202407-I](https://www.itu.int/rec/T-REC-H.265-202407-I)  defines some additional metadata fields which describe how the media was mastered, establishing the creative intent of the original media.

It's extremely rare to be doing the final color-correct on a monitor that fully supports rec2020, much more typical is one that has a P3 Gamut. The master-display parameter defines the colorimetry of the master display and the luminance range.

The display volume can be controlled with the [master-display](https://x265.readthedocs.io/en/stable/cli.html#cmdoption-master-display) x265 parameter, that can be passed through ffmpeg. We commonly see P3 values defined in a SEI info block (Supplemental Enhancement Information):

```
master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1)
```

This maps to:

```
master-display=G( Gx, Gy )B( Bx, By )R( Rx, Ry )WP( Wx, Wy )L( max_nits, min_nits )
```

Where (Gx, Gy), (Bx, By) and r(Rx, Ry) define the primaries of the color volume, so [P3](https://en.wikipedia.org/wiki/DCI-P3) has a color primaries:

|  | Rx | Ry | Gx | Gy | Bx | By |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Primary Colors | 0.680 | 0.320 | 0.265 | 0.690 | 0.150 | 0.060 |
| x 50000  | 34000 | 16000 | 13250 | 34500 | 7500 | 3000 |

This defines the x, y primaries, but you need to multiply the fractional value with "50000" to get the integer value.

The whitepoint is also defined with the same multiplication, which typically would be a D65 whitepoint (0.3127 ,	0.3290	) \= WP(15635,16450).

Lastly, the Luminance is defined as L(MAX\_NITS\*10000, MIN\_NITS\*10000) so for a typical 1000 nit display would be L(10000000,1). For Max luminance values are expected to be in the 50000 to 100000000 range, otherwise the value is considered unknown. 0 is also considered unknown. Similarly for the min luminance the range is considered to be in the 1-50000 range other values (including 0\) are considered unknown.

For reference the full rec2020 display values would be:

```
master-display=G(8500,39850)B(6550,2300)R(35400,14600)WP(15635,16450)L(10000000,1)
```

Reminder, this does NOT need to match the colorspace/primaries of the overall encoding container, you should not use this unless you actually Master the content on a rec2020 display. Using the P3 monitor values (or whatever display you are using) gives a clue to the display that it should not be using values outside of that gamut, this ensures that you get the colors that the creators expect. The problem is that this does assume quite a bit of the hardware interpreting these values, so in many cases it may be best to limit the source content as much as possible to a P3 gamut (or less).

##### Max-cll/MaxFALL

The [max-cll](https://x265.readthedocs.io/en/stable/cli.html#cmdoption-max-cll) parameter in h265 is actually two parameters:

* Maximum content light level (MaxCLL) \- this is the luminance of the brightest pixel (in Nits) of the entire video stream.  
* Maximum frame average light level (MaxFALL) \- this is the average luminance of the entire video stream (in Nits).

These are defined by the [Consumer Electronics Association 861.3 spec](https://manuals.plus/m/daba89fd26a25086fa5fbb4855bca4cf77e76cfecbf8bd748a139fcbdc220332.pdf).

Tools such as Resolve, provide ways to calculate these values see [here](https://www.youtube.com/watch?v=1HJi_ZP079w), but its not uncommon to use "typical" values, e.g. "1000,400". i.e. 1000 nit max brightness, 400 average brightness. Although if you really don't know, you can use 0,0 to mean unknown.

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

It is currently not possible to add this metadata with ffmpeg, but this hopefully will be addressed.

## HLG

[HLG](https://en.wikipedia.org/wiki/Hybrid_log%E2%80%93gamma) encoding, developed by NHK and the BBC. It's designed to be backwards compatible with the EOTF to SDR but with an extension for higher intensities. It has a more limited maximum peak brightness of 5000 nits rather than 10000 nits for PQ (although 1000 is more common).

It is also designed to adapt to the surrounding room light levels, unlike PQ which is fixed. The downside is that this adaptation could affect the media in unexpected ways. For this reason (and others) we do recommend using PQ10 instead.

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
    -x265-params "colorprim=bt2020:colormatrix=bt2020nc:transfer=bt2020-10:atc-sei=18:pic-struct=0" \
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


### cICP/mDCV/cLLI in PNG

PNG files have transferable parameters for video encoding in two formats:  
[cICP](https://w3c.github.io/png/#cICP-chunk) which has the color primaries, transfer function and matrix coefficients based on the [ITU-T-H.273](https://w3c.github.io/png/#bib-itu-t-h.273)\] spec. Further exploration is needed to see if these parameters are correctly read into ffmpeg, which potentially may reduce some of the crazy flags needed.

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
* [Recommendations for Verifying HDR Subjective Testing WorkflowsRecommendations for Verifying HDR Subjective Testing Workflows](https://arxiv.org/pdf/2305.11858)
* [ITU-T Rec.H Sup.19 \- Usage of video signal code points](https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-H.Sup19-201910-S!!PDF-E&type=items)

I would like to thank Zach Lewis, Doug Walker, Michael De Caria and Vibhoothi for their help in creating this document.  
