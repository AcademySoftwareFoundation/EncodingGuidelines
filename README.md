# ORI Video Encoding recommendations.

This repository contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.
We are trying to develop best practices, so we will suggest a good starting point, but there isn't a right answer for all cases. We also try to explain what the encoding parameters do, and in what situations you might want to choose different parameters.
This is not the site for general encoding, although you may find answers here, we will likely opt for a simple one-size fits all solution over file-size efficiency.
We welcome suggestions and improvements.

This work is being done as part of the [ASWF Open Review Initiative](https://openreviewinitiative.org/). We are grateful for the ASWF for creating the collaborative cross company environment that allows such projects to exist.

The main wiki page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

1. [Acknowledgements](#Acknowledgements)
2. [Encoding Cheat Sheet](Quickstart.html)
3. [Encoding Overview](Encoding.html#Encoding-Overview)
4. [Color space conversion](ColorPreservation.html#Color-space-conversion)
5. [Media Encoding with ffmpeg](ColorPreservation.html#encodestart)
    1. [Frame sequence specification](FfmpegInputs.html)
	2. [RGB to YCrCb Conversion](ColorPreservation.html#yuv)
	3. [TV vs. Full range.](ColorPreservation.html#tvfull)
	4. [RGB encode](RGBEncoding.html)
	5. [Useful Ffmpeg Filters.](OtherFfmpegArgs.html)
	6. [HDR Encoding](HDR_Encoding.html)
	7. [Adding Timecode and Editorial Workflow](EditorialWorkflow.html)
6. [Codec Comparsions](Encoding.html#encode)
	1. [h264](Encodeh264.html)
	2. [Prores](EncodeProres.html)
	3. [AV1](EncodeAv1.html)
	4. [HEVC/H.265](EncodeHevc.html)
	5. [MJPEG](EncodeMJPEG.html)
	6. [VP8](EncodeVP8.html)
	6. [VP9](EncodeVP9.html)
	7. [DNxHD](EncodeDNXHD.html)
7. [Metadata NCLC/NCLX](ColorPreservation.html#nclc)
	1. [Gamut - colorprimaries](ColorPreservation.html#gamut)
	2. [Color Range](ColorPreservation.html#range)
8. [Web Review](ColorPreservation.html#webreview)