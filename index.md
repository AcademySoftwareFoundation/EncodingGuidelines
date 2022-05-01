---
layout: default
nav_order: 1
title: Introduction
---

# ASWF Encoding recommendations.

This contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.
We are trying to develop best practices, so we will suggest a good starting point, but there isnt a right answer for all cases, so we do also try to explain what the parameters do, and in what situations you might want to choose different parameters.
This is not the site for general encoding, although you may find answers here, we will likely opt for a simple one-size fits all solution over file-size efficiency.
We welcome suggestions and improvements.

This is being done as part of the [ASWF Media Review working-group](https://wiki.aswf.io/display/PRWG/Playback+And+Review+Working+Group).

The main confluence page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

1. [Acknowledgements](#Acknowledgements)
2. [Encoding Cheat Sheet](Quickstart.html)
3. [Encoding Overview](Encoding.html#Encoding-Overview)
4. [Color space conversion](ColorPreservation.html#Color-space-conversion)
5. [Media Encoding with ffmpeg](ColorPreservation.html#encodestart)
	1. [RGB to YCrCb Conversion](ColorPreservation.html#yuv)
	2. [TV vs. Full range.](ColorPreservation.html#tvfull)
	3. [RGB encode](ColorPreservation.html#rgbencode)
6. [Encoding](Encoding.html#encode)
	1. [h264](Encoding.html#h264)
	2. [Prores](Encoding.html#prores)
7. [Metadata NCLC/NCLX](ColorPreservation.html#nclc)
	1. [Gamut - colorprimaries](ColorPreservation.html#gamut)
	2. [Color Range](ColorPreservation.html#range)
8. [Web Review](ColorPreservation.html#webreview)


### Acknowledgements  <a name="Acknowledgements"></a>

This document is a result of feedback from many people, in particular I would like to thank Kevin Wheatley, Gates Roberg Clark, Rick Sayre, Wendy Heffner and J Schulte for their time and patience.  

### Status

This document and project is still a work in progress. We are working on building a more complete testing framework, so that it is easy to confirm that changes to ffmpeg are not breaking existing functionality.


### Authors

This document is primarily the work of Sam Richards, with support from Daniel Flehner Heen.
