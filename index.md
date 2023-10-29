---
layout: default
nav_order: 1
title: Introduction
---

# ORI Video Encoding Guidelines.

A project from within the [ASWF Open Review Initiative](https://openreviewinitiative.org/), attempts to establish best practices for encoding Video media for VFX/Animation media review. We aim to explain what various parameters do, and in what situations you might want to choose to modify them.

This is not the site for general encoding, although you may find answers here, we will likely opt for a simple one-size fits all solution over file-size efficiency.
We welcome suggestions and improvements.

The main confluence page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

## Why is this needed.

There are a lot of excellent guides out there. But few addressing the needs of the VFX community. 

An example of why this is important is to compare:

<table>
<TR><TD style='padding-top:0px; padding-bottom: 0px' >Original PNG Image</TD><TD style='padding-top:0px; padding-bottom: 0px'><IMG src="sourceimages/original-png.png" style='height:70px'/></TD><TD style='padding-top:0px; padding-bottom: 0px'></td></TR>
<TR><TD style='padding-top:0px; padding-bottom: 0px'>Default ffmpeg conversion</TD><TD style='padding-top:0px; padding-bottom: 0px'><img src="sourceimages/default-ffmpeg.png" style='height:70px'/> </td><td style='padding-top:0px; padding-bottom: 0px'> NOTE color shift compared to original</TD></TR>
<TR><TD style='padding-top:0px; padding-bottom: 0px'>Using the libavscale library</TD><TD style='padding-top:0px; padding-bottom: 0px'><img src="sourceimages/libswscale-example.png" style='height:70px'/> </td><td style='padding-top:0px; padding-bottom: 0px'> Should match original</TD></TR>
</table>

You can see the default ffmpeg conversion introduces a dramatic colorshift that if you use the right flags, you can match the original. See [Color space conversion](ColorPreservation.html#Color-space-conversion) for more details on this.

1. [Acknowledgements](#Acknowledgements)
2. [Encoding Cheat Sheet](Quickstart.html)
3. [Encoding Overview](Encoding.html#Encoding-Overview)
4. [Color space conversion](ColorPreservation.html#Color-space-conversion)
5. [Media Encoding with ffmpeg](ColorPreservation.html#encodestart)
	1. [RGB to YCrCb Conversion](ColorPreservation.html#yuv)
	2. [TV vs. Full range.](ColorPreservation.html#tvfull)
	3. [RGB encode](ColorPreservation.html#rgbencode)
6. [Codec Comparsions](Encoding.html#encode)
	1. [h264](Encodeh264.html)
	2. [Prores](EncodeProres.html)
	3. [AV1](EncodeAv1.html)
	4. [HEVC/H.265](EncodeHevc.html)
	5. [MJPEG](EncodeMJPEG.html)
	6. [VP9](EncodeVP9.html)
	7. [DNxHD](EncodeDNXHD.html)
7. [Metadata NCLC/NCLX](ColorPreservation.html#nclc)
	1. [Gamut - colorprimaries](ColorPreservation.html#gamut)
	2. [Color Range](ColorPreservation.html#range)
8. [Web Review](ColorPreservation.html#webreview)

### Acknowledgements  <a name="Acknowledgements"></a>

This document is a result of feedback from many people, in particular I would like to thank Kevin Wheatley, Gates Roberg Clark, Rick Sayre, Wendy Heffner and J Schulte for their time and patience.  

### Status

This document and project is still a work in progress. We are working on building a more complete testing framework, so that it is easy to confirm that changes to ffmpeg are not breaking existing functionality.

### Authors

This document is primarily the work of Sam Richards. The test suite was developed by Daniel Flehner Heen.

### Feedback and error reporting.

We welcome feedback on this document, please report any errors or suggestions to the [github issues](https://github.com/AcademySoftwareFoundation/EncodingGuidelines/issues) page. 
