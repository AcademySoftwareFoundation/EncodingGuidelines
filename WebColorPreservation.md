---
layout: default
title: Web Color Preservation
nav_order: 5
parent: Encoding Overview
---

<style>
.compare th, .compare td {
    padding: 2px 2px !important;
    border: 0px solid #e9ebec !important;
}
</style>

# Color Metadata and Web Color Preservation <a name="nclc"></a>
There are a number of metadata flags designed to help the player know what colorspace the media is in, so it can correctly interpret it for playback. We do recommend adding the metadata tags to media, particularly if you are reviewing it on a web browser, however there are a lot of gotchas here, please see the section on [Web Review](#review).

The NCLC/NCLX is defined as a ISO spec here (see https://www.iso.org/standard/73412.html). The numbers below are part of the definition. NCLC stands for Non-Consistent Luminance Coding, a brief overview of its history is here. For MP4 files, its also known as NCLX. Additionally this metadata can also be represented in the h264 metadata stream in the video usability Information (VUI) block.

You can read the metadata using [mp4box.js](https://gpac.github.io/mp4box.js/test/filereader.html) which is a visual browser of the mp4 metadata, and look at moov/trak/mdia/minf/stbl/stsd/avc1/colr property.

NOTE: None of the flags below affect the encoding of the source imagery, they are meant to be used to guide how the mp4 file is decoded.

The docs are pretty sparse for this, some of the better info is [FFmpeg/pixfmt.h at master](https://github.com/FFmpeg/FFmpeg/blob/master/libavutil/pixfmt.h)

There are four possible tags that you can apply to movies:
  * <a href='#transfer-function-tests-color_trc-flag'>color_trc</a> - The transfer function (e.g. gamma)
  * <a href='#colorprimaries'>color_primaries</a> - e.g. rec709, rec2020, display-p3
  * <a href="#color_range">color_range</a> - Is it tv vs. full range
  * <a href="#color_space">color_space</a> - Is it YUV vs. RGB


For a detailed breakdown of what browsers support what flags see: [here](https://wiki.aswf.io/display/PRWG/Color+fidelity+for+Web+Browsers)


# Transfer function tests (color_trc flag)
This is setting the transfer function, which is typically going to be related to the gamma of the display. There are a number of existing gamma profiles, e.g. rec709 or sRGB, as well as gamma 2.2, and 2.8. Having said that, rec709 is frankly rather useless, consequently we recommend using sRGB as a default.

For more details see: [here](tests/greramp-osx/ycrcbcompare.md)

## sRGB
Using the `-color_trc iec61966-2-1` flag. This appears to be the most reliable one, working across all machines and browsers that support it. It's a shame that the flag has to be so cryptic. 

<table class='compare'>
<TR><TD><img width=400 src="tests/greyramp-osx/greyscale-srgb.png"/></TD><TD>Source SRGB PNG</TD></TR>
<TR><TD><video width=400><source src="tests/greyramp-osx/greyscale-srgb.mp4"></video></TD><TD>Mp4 Video should match PNG</TD></TR>
</table>

## rec709
Using the `-color_trc rec709` flag. This is often the default tag, however producers the most confusing results. On Chrome this will actually match sRGB, but on safari it will match the camera rec709 parameters, which roughly match gamma 1.95. NOTE, there is no support at all for BT1886, which is what we would conventionally use for the TV gamma of 2.4, the closest you can get is using quicktime on OSX.

<table  class='compare'>
<TR><TD><video width=400><source src="tests/greyramp-osx/greyscale-rec709.mp4"></video></TD><TD>This is the rec709 mp4.</TD></TR>
<TR x-show="/^((?!chrome|android).)*safari/i.test(navigator.userAgent)"><TD><video width=400><source src="tests/greyramp-osx/greyscale-gamma195.mov"></video></TD><TD>This is a quicktime with a gamma of 1.95. This should be nearly identical to the above rec709 mp4, which implies OSX is correctly interpreting camera rec709.</TD></TR>
<TR><TD><video width=400><source src="tests/greyramp-osx/greyscale-srgb.mp4"></video></TD><TD>This is the srgb.mp4 which may match the rec709 result. For chrome on windows, this should match rec709, which implies its treating it as sRGB.</TD></TR>
</table>

Screenshots
<table class='compare'>
<TR><TD><img width=400 src="browsercompare/chrome-rec709-windows-color_trc1.png"/></TD><TD>Screenshot of mp4 of chrome on windows</TD></TR>
<TR><TD><img width=400 src="browsercompare/safari-rec709-osx-color_trc1.png"/></TD><TD>Screenshot of mp4 of safari on OSX</TD></TR>
</table>

## Gamma 2.2
Using the `-color_trc gamma22` flag. This does not work correctly on safari.

<table class='compare'>
<TR><TD><img width=400 src="tests/greyramp-osx/greyscale-g22.png"/></TD><TD>Source gamma 2.2 PNG</TD></TR>
<TR><TD><video width=400><source src="tests/greyramp-osx/greyscale-gamma22.mp4"></video></TD><TD>Mp4 Video should match PNG</TD></TR>
</table>

## Gamma linear
Using the `-color_trc linear` flag. This is unlikely to ever be used for video, however it does make for a good test that something is working.

<table class='compare'>
<TR><TD><img width=400 src="tests/greyramp-osx/greyscale-lin.png"/></TD><TD>Source linear PNG</TD></TR>
<TR><TD><video width=400><source src="tests/greyramp-osx/greyscale-lin.mp4"></video></TD><TD>Mp4 Video should match PNG</TD></TR>
</table>

## Summary
We recommend the use of `-color_trc iec61966-2-1` to use sRGB. There is no support for a gamma 2.4, if you still need it, we recommend that you use -color_trc unknown and ensure that your monitor is set correctly


# Gamut colorprimaries

Normally web browsers use the bt709 color gamut (which is different to the bt709 gamma), but in theory you could define your media as having a wider gamut, e.g. DCI-P3 or rec2020. The files below show a PNG and MP4 file defined using the rec2020 gamut, so depending on which monitor you are using it will show different text. This is similar to the excellent [WIDE>Gamut](https://www.wide-gamut.com/) test page.

<table class='compare' width='100%'>
<TR><TH>PNG file</TH><TH>Mp4 file (which should match PNG file)</TH></TR>
<TR><TD><img width='316' src="gamuttests/iccgamut/ps-combined-rec2020-g2.2.png"/></td><td><video   width='316'   ><source src='gamuttests/iccgamut/greyscale-rec2020.mp4' type='video/mp4'/></video></td></TR>
</table>


<table class='compare' width='100%'>
<TR><TD><img width='316' src="browsercompare/gamut-all.png"/></TD><TD>What the image should look like if nothing is working, or you have a rec2020 monitor.</TD></TR>
<TR><TD><img width='316' src="browsercompare/gamut-displayp3-raw.png"/></TD><TD>What the image should look like if you have a display-p3 monitor.</TD></TR>
</table>

Chrome on windows, and Safari and Chrome on IOS will always assume the display is sRGB. In theory [chrome://flags/#force-color-profile](chrome://flags/#force-color-profile) should give you some settings for this, but it seems to be ignored.



# Web Review <a name="webreview"></a>
See:
* [NCLC Testing Overview](https://richardssam.github.io/ffmpeg-tests/compare.html) This is an overview of the NCLC Tag tests for web review.
* [Comparing different outputs for -color_trc](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-osx/compare.html) - Showing what the -color_trc flag is doing, compared to embedding in mov and png.
* [Comparing different outputs for the -colorprimaries](https://richardssam.github.io/ffmpeg-tests/gamuttests/iccgamut/compare.html)
