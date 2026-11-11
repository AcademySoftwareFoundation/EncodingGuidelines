---
layout: default
nav_order: 1
title: Introduction
---

# ORI Video Encoding Guidelines

This project is from the [ASWF Open Review Initiative](https://openreviewinitiative.org/). It attempts to establish best practices for encoding Video media for VFX/Animation media review. We aim to explain what various parameters do, and in what situations you might want to choose to modify them.

This is not the site for general encoding, although you may find answers here, we will likely opt for a simple one-size fits all solution over file-size efficiency.
We welcome suggestions and improvements.

The original Confluence page for this work is [Movie Compression with ffmpeg for media review](https://lf-aswf.atlassian.net/wiki/spaces/PRWG/pages/11274685/Movie+Compression+with+ffmpeg+for+media+review).

{: .highlight }
We recommend usage of [VP9](EncodeVP9.html) and [AV1](EncodeAv1.html) over h264 and h265 where possible to encourage the usage of patent-free codecs, for more information on this see the white-paper [Next-gen codecs for VFX Community](https://docs.google.com/document/d/1EJ7Q_HhjL0ELNdjz5AgnPrraUvy7XCo52LL08WxgjtA/edit#heading=h.9rkn78tjmq48).  

## Why is this needed

There are a lot of excellent guides out there. But few addressing the needs of the VFX community.

An example of why this is important is to compare:

<table>
<TR><TD style='padding-top:0px; padding-bottom: 0px' >Original PNG Image</TD><TD style='padding-top:0px; padding-bottom: 0px'><IMG src="sourceimages/original-png.png" style='height:70px'/></TD><TD style='padding-top:0px; padding-bottom: 0px'></td></TR>
<TR><TD style='padding-top:0px; padding-bottom: 0px'>Default ffmpeg conversion</TD><TD style='padding-top:0px; padding-bottom: 0px'><img src="sourceimages/default-ffmpeg.png" style='height:70px'/> </td><td style='padding-top:0px; padding-bottom: 0px'> NOTE color shift compared to original</TD></TR>
<TR><TD style='padding-top:0px; padding-bottom: 0px'>Converting explicitly to BT.709</TD><TD style='padding-top:0px; padding-bottom: 0px'><img src="sourceimages/libswscale-example.png" style='height:70px'/> </td><td style='padding-top:0px; padding-bottom: 0px'> Should match original</TD></TR>
</table>

You can see the default ffmpeg conversion introduces a dramatic color shift that if you use the right flags, you can match the original. See [RGB to YCbCr Conversion](ColorPreservation.html) for more details on this.

1. [Acknowledgements](#Acknowledgements)
2. [Encoding Cheat Sheet](Quickstart.html)
3. [Encoding Overview](EncodingOverview.html)
    1. [Color space conversion](EncodingOverview.html#Color-space-conversion)
    2. [Frame sequence specification](FfmpegInputs.html)
    3. [RGB to YCbCr Conversion](ColorPreservation.html)
    4. [TV vs. Full range](ColorPreservation.html#tvfull)
    5. [Adding Timecode and Editorial Workflow](EditorialWorkflow.html)
    6. [Web Color Preservation](WebColorPreservation.html)
    7. [FFmpeg OCIO Filter](FfmpegOcio.html)
    8. [Useful FFmpeg Filters](OtherFfmpegArgs.html)
    9. [FFmpeg Scaling Options](EncodeSwsScale.html)
    10. [zscale Conversion](EncodeZscale.html)
    11. [Chroma Siting](ChromaSiting.html)
    12. [RGB Encoding](RGBEncoding.html)
    13. [HDR Encoding](enctests/HDR_Encoding.html)
    14. [Adding Metadata](EncodingMetadata.html)
4. [Codec Comparisons](Encoding.html)
    1. [H.264](Encodeh264.html)
    2. [HEVC/H.265](EncodeHevc.html)
    3. [ProRes](EncodeProres.html)
    4. [DNxHD](EncodeDNXHD.html)
    5. [AV1](EncodeAv1.html)
    6. [VP9](EncodeVP9.html)
    7. [JPEG2000 - HTJ2K](EncodeHTJ2K.html)
    8. [MJPEG](EncodeMJPEG.html)
    9. [OpenAPV](EncodeOpenAPV.html)
    10. [VP8](EncodeVP8.html)
5. [Test Output](Testresults.html)
6. [Test Framework](enctests/README.html)
7. [FFmpeg Version Changes](FFmpegChanges.html)

### Acknowledgements  <a name="Acknowledgements"></a>

This document is a result of feedback from many people, in particular I would like to thank Kevin Wheatley, Trevor Aylward, Mark Reid, Gates Roberg Clark, Rick Sayre, Wendy Heffner and J Schulte for their time and patience.  

### Status

This document and project is still a work in progress. We are working on building a more complete testing framework, so that it is easy to confirm that changes to ffmpeg are not breaking existing functionality.

### Authors

This document is primarily the work of Sam Richards with input from the ASWF community. The test suite was developed by Daniel Flehner Heen.

### Feedback and error reporting

We welcome feedback on this document, please report any errors or suggestions to the [github issues](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/issues) page.
